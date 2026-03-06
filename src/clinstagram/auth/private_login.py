"""Resilient private API login via instagrapi.

Handles session persistence, device UUID preservation, challenge resolution,
TOTP 2FA, proxy enforcement, and delay configuration.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Default action delays (seconds) — reduces detection risk
DEFAULT_DELAY_RANGE = [1, 3]


@dataclass
class LoginResult:
    success: bool
    username: str = ""
    session_json: str = ""
    error: str = ""
    challenge_required: bool = False
    relogin: bool = False


@dataclass
class LoginConfig:
    username: str
    password: str
    totp_seed: str = ""
    proxy: str = ""
    delay_range: list[int] = field(default_factory=lambda: list(DEFAULT_DELAY_RANGE))
    challenge_handler: Optional[Callable[[str], str]] = None
    locale: str = ""
    timezone: str = ""


def _challenge_code_handler(username: str, choice: str) -> str:
    """Default interactive challenge handler — prompts user for verification code."""
    import typer

    method = "SMS" if choice == "sms" else "email"
    code = typer.prompt(f"Enter the {method} verification code sent to your device")
    return code


def _configure_client(client: Any, config: LoginConfig) -> None:
    """Apply proxy, delays, locale, and TOTP to an instagrapi Client."""
    if config.proxy:
        client.set_proxy(config.proxy)

    client.delay_range = config.delay_range

    if config.locale:
        client.set_locale(config.locale)
    if config.timezone:
        client.set_timezone_offset(int(config.timezone))

    if config.totp_seed:
        client.totp_seed = config.totp_seed

    # Set challenge handler
    handler = config.challenge_handler or _challenge_code_handler
    client.challenge_code_handler = handler


def _validate_session(client: Any) -> bool:
    """Check if the current session is still valid by hitting a lightweight endpoint."""
    try:
        client.get_timeline_feed()
        return True
    except Exception:
        return False


def _extract_uuids(settings: dict) -> dict:
    """Pull device UUIDs from settings for fingerprint preservation."""
    uuids = {}
    for key in ("uuid", "phone_id", "device_id", "advertising_id"):
        if key in settings:
            uuids[key] = settings[key]
    # Also preserve device settings (model, android version, etc.)
    if "device_settings" in settings:
        uuids["device_settings"] = settings["device_settings"]
    return uuids


def login_private(config: LoginConfig, existing_session: str = "") -> LoginResult:
    """
    Perform a resilient private API login.

    Flow:
    1. If existing session exists, try to restore it
    2. Validate with get_timeline_feed()
    3. If validation fails, re-login with preserved device UUIDs
    4. If fresh login, perform full login with challenge handling
    5. Return session JSON for storage in keychain

    Parameters
    ----------
    config : LoginConfig
        Username, password, TOTP seed, proxy, etc.
    existing_session : str
        Previously stored session JSON from keychain (empty for first login).

    Returns
    -------
    LoginResult
        Contains success flag, session JSON for storage, and error details.
    """
    from instagrapi import Client
    from instagrapi.exceptions import (
        ChallengeRequired,
        LoginRequired,
        TwoFactorRequired,
    )

    cl = Client()
    _configure_client(cl, config)

    # ── Try restoring existing session ──────────────────────────────
    if existing_session:
        try:
            session_data = json.loads(existing_session)
            cl.set_settings(session_data)
            cl.login(config.username, config.password)

            if _validate_session(cl):
                logger.info("Session restored successfully for %s", config.username)
                new_session = json.dumps(cl.get_settings())
                return LoginResult(
                    success=True,
                    username=config.username,
                    session_json=new_session,
                )

            # Session invalid — re-login with preserved device fingerprint
            logger.info("Session expired for %s, re-authenticating with preserved UUIDs", config.username)
            old_settings = cl.get_settings()
            uuids = _extract_uuids(old_settings)

            cl = Client()
            _configure_client(cl, config)
            cl.set_settings({})
            if uuids:
                cl.set_uuids(uuids)

            cl.login(config.username, config.password)

            if _validate_session(cl):
                new_session = json.dumps(cl.get_settings())
                return LoginResult(
                    success=True,
                    username=config.username,
                    session_json=new_session,
                    relogin=True,
                )

            return LoginResult(success=False, username=config.username, error="Re-login succeeded but session validation failed")

        except ChallengeRequired:
            return LoginResult(
                success=False,
                username=config.username,
                error="Challenge required during session restore. Try logging in again.",
                challenge_required=True,
            )
        except TwoFactorRequired:
            # Handle 2FA during session restore
            if config.totp_seed:
                try:
                    from instagrapi.mixins.totp import TOTPMixin

                    code = TOTPMixin.totp_generate_code(config.totp_seed)
                    cl.two_factor_login(code)
                    if _validate_session(cl):
                        new_session = json.dumps(cl.get_settings())
                        return LoginResult(success=True, username=config.username, session_json=new_session)
                except Exception as exc:
                    return LoginResult(success=False, username=config.username, error=f"2FA during session restore failed: {exc}")
            return LoginResult(
                success=False,
                username=config.username,
                error="2FA required but no TOTP seed provided",
            )
        except LoginRequired:
            # Session completely dead — fall through to fresh login
            logger.info("Session completely expired for %s, performing fresh login", config.username)
            old_settings = cl.get_settings()
            uuids = _extract_uuids(old_settings)
            # Fall through to fresh login below, preserving UUIDs
            cl = Client()
            _configure_client(cl, config)
            if uuids:
                cl.set_uuids(uuids)
        except Exception as exc:
            logger.warning("Session restore failed for %s: %s", config.username, exc)
            # Fall through to fresh login
            cl = Client()
            _configure_client(cl, config)

    # ── Fresh login ─────────────────────────────────────────────────
    try:
        cl.login(config.username, config.password)
    except TwoFactorRequired:
        if config.totp_seed:
            try:
                from instagrapi.mixins.totp import TOTPMixin

                code = TOTPMixin.totp_generate_code(config.totp_seed)
                cl.two_factor_login(code)
            except Exception as exc:
                return LoginResult(success=False, username=config.username, error=f"2FA login failed: {exc}")
        else:
            return LoginResult(
                success=False,
                username=config.username,
                error="2FA required. Provide --totp-seed or set up TOTP in Instagram settings.",
            )
    except ChallengeRequired:
        return LoginResult(
            success=False,
            username=config.username,
            error="Instagram challenge required. Try again — the challenge handler will prompt you.",
            challenge_required=True,
        )
    except Exception as exc:
        return LoginResult(success=False, username=config.username, error=f"Login failed: {exc}")

    # ── Validate ────────────────────────────────────────────────────
    if not _validate_session(cl):
        return LoginResult(success=False, username=config.username, error="Login succeeded but session validation failed")

    new_session = json.dumps(cl.get_settings())
    return LoginResult(
        success=True,
        username=config.username,
        session_json=new_session,
    )
