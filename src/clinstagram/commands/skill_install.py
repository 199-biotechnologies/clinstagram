"""Install clinstagram skills for AI coding agents (Claude Code, Gemini CLI, Cursor, etc.)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import typer

from clinstagram.commands._dispatch import make_subgroup, output_success

skill_app = make_subgroup("Install AI agent skills")

# Agent → skills directory mapping
_AGENT_DIRS = {
    "claude": Path.home() / ".claude" / "skills",
    "gemini": Path.home() / ".gemini" / "skills",
    "cursor": Path.cwd() / ".cursor" / "skills",
}


def _find_skill_source() -> Path | None:
    """Find the SKILL.md or clinstagram.md bundled with this package."""
    # Try package data first (installed via pip)
    import importlib.resources
    try:
        ref = importlib.resources.files("clinstagram") / ".." / ".." / ".claude" / "skills" / "clinstagram.md"
        if ref.is_file():  # type: ignore[union-attr]
            return Path(str(ref))
    except Exception:
        pass
    # Try relative to this file (development mode)
    project_skill = Path(__file__).resolve().parents[3] / ".claude" / "skills" / "clinstagram.md"
    if project_skill.exists():
        return project_skill
    # Try SKILL.md at project root
    skill_md = Path(__file__).resolve().parents[3] / "SKILL.md"
    if skill_md.exists():
        return skill_md
    return None


def _detect_agents() -> list[str]:
    """Detect which AI coding agents are installed by checking for their config directories."""
    found = []
    for name, path in _AGENT_DIRS.items():
        # Check parent directory exists (e.g., ~/.claude/ exists)
        if path.parent.exists():
            found.append(name)
    return found


def _install_for_agent(agent: str, source: Path, force: bool = False) -> dict:
    """Install the skill file for a specific agent."""
    target_dir = _AGENT_DIRS[agent]
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "clinstagram.md"

    if target_file.exists() and not force:
        return {"agent": agent, "status": "already_installed", "path": str(target_file)}

    shutil.copy2(source, target_file)
    return {"agent": agent, "status": "installed", "path": str(target_file)}


@skill_app.command("install-skill")
def install_skill(
    ctx: typer.Context,
    agent: Optional[str] = typer.Option(
        None, "--agent", "-a",
        help="Target agent: claude, gemini, cursor, or 'all' (auto-detect if omitted)",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing skill files"),
):
    """Install clinstagram skill for AI coding agents.

    Auto-detects installed agents (Claude Code, Gemini CLI, Cursor) and copies
    the skill definition so agents can use clinstagram commands natively.
    """
    source = _find_skill_source()
    if not source:
        typer.echo("Error: Could not find skill file (clinstagram.md or SKILL.md)", err=True)
        raise typer.Exit(1)

    if agent and agent != "all":
        if agent not in _AGENT_DIRS:
            typer.echo(f"Error: Unknown agent '{agent}'. Choose: {', '.join(_AGENT_DIRS)}", err=True)
            raise typer.Exit(1)
        agents = [agent]
    elif agent == "all":
        agents = list(_AGENT_DIRS.keys())
    else:
        agents = _detect_agents()
        if not agents:
            typer.echo("No AI coding agents detected. Use --agent to specify one.", err=True)
            raise typer.Exit(1)

    results = []
    for a in agents:
        result = _install_for_agent(a, source, force=force)
        results.append(result)
        if not ctx.obj.get("json"):
            status = result["status"]
            icon = "+" if status == "installed" else "="
            typer.echo(f"  [{icon}] {a}: {result['path']} ({status})")

    if ctx.obj.get("json"):
        output_success(ctx, {"skills_installed": results, "source": str(source)})
