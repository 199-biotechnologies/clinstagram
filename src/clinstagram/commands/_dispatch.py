"""Shared dispatch logic — routes a Feature to a backend, calls the action, outputs the result."""
from __future__ import annotations

import json
import sys
from typing import Any, Callable

import typer
from rich.console import Console

def make_subgroup(help_text: str) -> typer.Typer:
    """Create a sub-Typer with proper no-args help."""
    sub = typer.Typer(help=help_text, no_args_is_help=True)
    return sub

from clinstagram.auth.keychain import SecretsStore
from clinstagram.backends.base import Backend
from clinstagram.backends.capabilities import Feature
from clinstagram.backends.router import Router
from clinstagram.config import ComplianceMode
from clinstagram.media import cleanup_temp_files, resolve_media
from clinstagram.models import CLIError, CLIResponse, ExitCode

console = Console()


def _get_secrets(ctx: typer.Context) -> SecretsStore:
    if "secrets" in ctx.obj:
        return ctx.obj["secrets"]
    return SecretsStore(backend="keyring")


def _get_router(ctx: typer.Context) -> Router:
    config = ctx.obj["config"]
    return Router(
        account=ctx.obj["account"],
        compliance_mode=config.compliance_mode,
        secrets=_get_secrets(ctx),
    )


def _instantiate_backend(ctx: typer.Context, backend_name: str, feature: Feature) -> Backend:
    """Create the appropriate Backend instance from stored credentials."""
    import httpx

    secrets = _get_secrets(ctx)
    account = ctx.obj["account"]

    if backend_name == "graph_ig":
        from clinstagram.backends.graph import GraphBackend

        token = secrets.get(account, "graph_ig_token")
        return GraphBackend(token=token, login_type="ig", client=httpx.Client())

    if backend_name == "graph_fb":
        from clinstagram.backends.graph import GraphBackend

        token = secrets.get(account, "graph_fb_token")
        return GraphBackend(token=token, login_type="fb", client=httpx.Client())

    if backend_name == "private":
        from instagrapi import Client

        from clinstagram.backends.private import PrivateBackend

        session_json = secrets.get(account, "private_session")
        if not session_json:
            raise RuntimeError("No private session stored. Run: clinstagram auth login")
        cl = Client()
        session_data = json.loads(session_json)
        cl.set_settings(session_data)
        proxy = ctx.obj.get("proxy")
        if proxy:
            cl.set_proxy(proxy)
            
        from clinstagram.backends.capabilities import READ_ONLY_FEATURES
        config = ctx.obj["config"]
        rl = config.rate_limits
        if feature in READ_ONLY_FEATURES:
            cl.delay_range = [0, rl.request_delay_min]
        else:
            cl.delay_range = [rl.request_delay_min, rl.request_delay_max]
            
        return PrivateBackend(client=cl)

    raise ValueError(f"Unknown backend: {backend_name}")


def _output_response(ctx: typer.Context, response: CLIResponse) -> None:
    if ctx.obj["json"]:
        typer.echo(response.to_json())
    else:
        if isinstance(response.data, list):
            for item in response.data:
                if isinstance(item, dict):
                    for k, v in item.items():
                        typer.echo(f"  {k}: {v}")
                    typer.echo()
                else:
                    typer.echo(f"  {item}")
        elif isinstance(response.data, dict):
            for k, v in response.data.items():
                typer.echo(f"  {k}: {v}")
        else:
            typer.echo(str(response.data))


def _output_error(ctx: typer.Context, error: CLIError) -> None:
    if ctx.obj["json"]:
        typer.echo(error.to_json(), err=True)
    else:
        console.print(f"[red]Error:[/red] {error.error}")
        if error.remediation:
            console.print(f"[yellow]Fix:[/yellow] {error.remediation}")
    raise typer.Exit(code=error.exit_code)


def strip_at(username: str) -> str:
    """Remove leading @ from usernames."""
    return username.lstrip("@")


def stage(source: str, backend_name: str) -> str:
    """Resolve a media source (path or URL) for the given backend."""
    needs_url = backend_name.startswith("graph")
    return resolve_media(source, needs_url=needs_url)


def dispatch(
    ctx: typer.Context,
    feature: Feature,
    action: Callable[[Backend], Any],
) -> None:
    """Route feature → backend → call action → output result."""
    # Check dry-run
    if ctx.obj.get("dry_run"):
        router = _get_router(ctx)
        backend_name = router.route(feature)
        typer.echo(json.dumps({
            "dry_run": True,
            "feature": feature.value,
            "backend": backend_name,
        }))
        return

    # Force backend override
    forced = ctx.obj.get("backend")
    if forced and forced.value != "auto":
        backend_name = forced.value
    else:
        router = _get_router(ctx)
        backend_name = router.route(feature)

    if backend_name is None:
        # Determine whether it's a policy block or missing backend
        config = ctx.obj["config"]
        if config.compliance_mode == ComplianceMode.OFFICIAL_ONLY:
            _output_error(ctx, CLIError(
                exit_code=ExitCode.POLICY_BLOCKED,
                error=f"Feature '{feature.value}' is blocked by compliance mode '{config.compliance_mode.value}'",
                remediation="Run: clinstagram config mode hybrid-safe",
            ))
        else:
            _output_error(ctx, CLIError(
                exit_code=ExitCode.CAPABILITY_UNAVAILABLE,
                error=f"No backend available for '{feature.value}'",
                remediation="Run: clinstagram auth status  — then connect a backend",
            ))
        return

    try:
        backend = _instantiate_backend(ctx, backend_name, feature)
    except Exception as exc:
        _output_error(ctx, CLIError(
            exit_code=ExitCode.AUTH_ERROR,
            error=f"Failed to initialize {backend_name}: {exc}",
            remediation=f"Run: clinstagram auth {'login' if backend_name == 'private' else 'connect-' + backend_name.split('_')[1]}",
        ))
        return

    try:
        # Store backend_name in context for stage() calls in action lambdas
        ctx.obj["_backend_name"] = backend_name
        result = action(backend)
        _output_response(ctx, CLIResponse(
            data=result,
            backend_used=backend_name,
        ))
    except NotImplementedError as exc:
        _output_error(ctx, CLIError(
            exit_code=ExitCode.CAPABILITY_UNAVAILABLE,
            error=str(exc),
            remediation="Try a different backend: --backend private",
        ))
    except Exception as exc:
        error_str = str(exc)
        if "rate" in error_str.lower() or "throttl" in error_str.lower():
            _output_error(ctx, CLIError(
                exit_code=ExitCode.RATE_LIMITED,
                error=error_str,
                retry_after=60,
            ))
        elif "challenge" in error_str.lower():
            _output_error(ctx, CLIError(
                exit_code=ExitCode.CHALLENGE_REQUIRED,
                error=error_str,
                challenge_type="unknown",
            ))
        elif "login" in error_str.lower() or "auth" in error_str.lower() or "session" in error_str.lower():
            _output_error(ctx, CLIError(
                exit_code=ExitCode.AUTH_ERROR,
                error=error_str,
                remediation="Run: clinstagram auth login",
            ))
        else:
            _output_error(ctx, CLIError(
                exit_code=ExitCode.API_ERROR,
                error=error_str,
            ))
    finally:
        cleanup_temp_files()
