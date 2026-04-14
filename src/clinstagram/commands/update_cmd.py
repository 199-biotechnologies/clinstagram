"""`clinstagram update` — agent-safe self-update helper.

Invariants for agent use:
  - default behaviour is --check-only (no mutation, no prompt)
  - applying an upgrade requires explicit --apply AND --yes (or a TTY with confirm)
  - in --json mode, we never prompt; if --apply without --yes, emit error envelope
  - progress noise goes to stderr, envelope to stdout
  - refuse to mutate for anything except a clean pip install (use importlib.metadata
    + direct_url.json + INSTALLER to detect); return the right command otherwise
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, distribution
from typing import Any

import typer

from clinstagram import __version__
from clinstagram.commands._dispatch import output_error, output_success
from clinstagram.models import CLIError, ExitCode

PYPI_URL = "https://pypi.org/pypi/clinstagram/json"


# ---------- install-method detection ------------------------------------------------

def _detect_install_method() -> dict[str, Any]:
    """Inspect installed metadata to decide whether self-upgrade is safe.

    Returns {method, safe_to_auto_upgrade, upgrade_command, reason}.
    """
    try:
        dist = distribution("clinstagram")
    except PackageNotFoundError:
        return {
            "method": "unknown",
            "safe_to_auto_upgrade": False,
            "upgrade_command": "pip install --upgrade clinstagram",
            "reason": "clinstagram not found via importlib.metadata",
        }

    # PEP 660 editable install → refuse
    try:
        direct_url_raw = dist.read_text("direct_url.json")
        if direct_url_raw:
            direct_url = json.loads(direct_url_raw)
            if direct_url.get("dir_info", {}).get("editable"):
                return {
                    "method": "editable",
                    "safe_to_auto_upgrade": False,
                    "upgrade_command": "git pull",
                    "reason": "editable install — update would overwrite local changes",
                }
            if "vcs_info" in direct_url:
                return {
                    "method": "vcs",
                    "safe_to_auto_upgrade": False,
                    "upgrade_command": direct_url.get("url", "git pull"),
                    "reason": "installed from VCS — not from PyPI",
                }
    except Exception:
        pass

    # INSTALLER file tells us which tool put the package here
    installer = ""
    try:
        installer = (dist.read_text("INSTALLER") or "").strip().lower()
    except Exception:
        pass

    # pipx — has its own canonical upgrade command
    if installer == "pipx" or "/pipx/venvs/clinstagram/" in sys.executable:
        return {
            "method": "pipx",
            "safe_to_auto_upgrade": False,
            "upgrade_command": "pipx upgrade clinstagram",
            "reason": "installed via pipx — use pipx to keep the managed venv intact",
        }

    # uv — prefer uv's cli so its lockfile stays in sync
    if installer == "uv" or os.environ.get("UV_PROJECT_ENVIRONMENT"):
        return {
            "method": "uv",
            "safe_to_auto_upgrade": False,
            "upgrade_command": "uv pip install --upgrade clinstagram",
            "reason": "detected uv-managed environment",
        }

    # Homebrew / system Python managed → never auto-modify
    if sys.executable.startswith("/opt/homebrew/") or sys.executable.startswith("/usr/local/Cellar/"):
        return {
            "method": "homebrew",
            "safe_to_auto_upgrade": False,
            "upgrade_command": "brew upgrade clinstagram",
            "reason": "installed via Homebrew — auto-upgrade disabled",
        }
    if sys.executable.startswith("/usr/") or sys.executable.startswith("/System/"):
        return {
            "method": "system",
            "safe_to_auto_upgrade": False,
            "upgrade_command": "sudo pip install --upgrade clinstagram",
            "reason": "system Python — auto-upgrade disabled",
        }

    # conda → suggest pip-in-env but don't run automatically
    if os.environ.get("CONDA_PREFIX") and "conda" in sys.executable:
        return {
            "method": "conda",
            "safe_to_auto_upgrade": False,
            "upgrade_command": f"{sys.executable} -m pip install --upgrade clinstagram",
            "reason": "detected conda environment — run inside the active env",
        }

    # Plain pip install → safe to auto-upgrade
    return {
        "method": installer or "pip",
        "safe_to_auto_upgrade": True,
        "upgrade_command": f"{sys.executable} -m pip install --upgrade clinstagram",
        "reason": "plain pip install — safe to auto-upgrade",
    }


# ---------- PyPI lookup -------------------------------------------------------------

def _fetch_latest_from_pypi(include_prereleases: bool) -> str:
    """Return the highest valid version string from PyPI.

    - Ignores yanked releases
    - Filters out pre-releases unless include_prereleases=True
    - Requires at least one file per version
    """
    import httpx  # lazy
    from packaging.version import InvalidVersion, Version

    response = httpx.get(PYPI_URL, timeout=10.0)
    response.raise_for_status()
    payload = response.json()

    releases: dict[str, list[dict]] = payload.get("releases") or {}
    candidates: list[Version] = []
    for version_str, files in releases.items():
        if not files:
            continue
        # skip a release where every file is yanked
        if all(f.get("yanked") for f in files):
            continue
        try:
            v = Version(version_str)
        except InvalidVersion:
            continue
        if v.is_prerelease and not include_prereleases:
            continue
        candidates.append(v)

    if not candidates:
        # Fall back to info.version (may be a prerelease)
        fallback = payload.get("info", {}).get("version")
        if fallback:
            return fallback
        raise RuntimeError("no valid release found on PyPI")

    return str(max(candidates))


# ---------- command entrypoint ------------------------------------------------------

def run_update(
    ctx: typer.Context,
    check: bool = False,  # retained for backward-compat with the existing CLI flag
    apply: bool = False,
    yes: bool = False,
    pre: bool = False,
) -> None:
    from packaging.version import Version

    try:
        latest_str = _fetch_latest_from_pypi(include_prereleases=pre)
    except Exception as exc:
        output_error(ctx, CLIError(
            exit_code=ExitCode.API_ERROR,
            error=f"PyPI lookup failed: {exc}",
            remediation="Retry shortly or set a working proxy",
        ))
        return

    current = Version(__version__)
    latest = Version(latest_str)

    if latest > current:
        status = "update_available"
    elif latest < current:
        status = "ahead_of_pypi"  # local dev version newer than released
    else:
        status = "up_to_date"

    install_info = _detect_install_method()

    base_data: dict[str, Any] = {
        "current_version": __version__,
        "latest_version": latest_str,
        "status": status,
        "install_method": install_info["method"],
        "safe_to_auto_upgrade": install_info["safe_to_auto_upgrade"],
        "upgrade_command": install_info["upgrade_command"],
    }

    # --check or default (not --apply): report and stop
    if check or not apply:
        output_success(ctx, base_data)
        return

    # --apply path
    if status != "update_available":
        output_success(ctx, {**base_data, "message": f"No upgrade needed (status={status})"})
        return

    if not install_info["safe_to_auto_upgrade"]:
        output_error(ctx, CLIError(
            exit_code=ExitCode.POLICY_BLOCKED,
            error=f"Auto-upgrade disabled for {install_info['method']} install: {install_info['reason']}",
            remediation=install_info["upgrade_command"],
        ))
        return

    # JSON mode is non-interactive — require --yes
    if not yes:
        if ctx.obj.get("json"):
            output_error(ctx, CLIError(
                exit_code=ExitCode.USER_ERROR,
                error="--apply requires --yes in JSON/non-interactive mode",
                remediation=f"Run: clinstagram update --apply --yes  (or: {install_info['upgrade_command']})",
            ))
            return
        # Human TTY: confirm
        typer.echo(
            f"Update available: {__version__} → {latest_str} ({install_info['method']} install)",
            err=True,
        )
        if not typer.confirm(f"Run `{install_info['upgrade_command']}` now?"):
            output_success(ctx, {**base_data, "message": "aborted by user"})
            return

    # Execute upgrade. Progress → stderr; envelope → stdout.
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "clinstagram"]
    if pre:
        cmd.insert(-1, "--pre")

    typer.echo(f"Upgrading: {' '.join(cmd)}", err=True)
    result = subprocess.run(cmd, stdout=sys.stderr, stderr=sys.stderr)

    if result.returncode != 0:
        output_error(ctx, CLIError(
            exit_code=ExitCode.API_ERROR,
            error=f"pip exited with code {result.returncode}",
            remediation=install_info["upgrade_command"],
        ))
        return

    output_success(ctx, {
        **base_data,
        "status": "updated",
        "old_version": __version__,
        "new_version": latest_str,
    })
