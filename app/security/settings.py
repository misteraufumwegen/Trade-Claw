"""
Startup-time validation of security-critical environment variables.

Imported (and called) from `app.main` at app boot. In non-development
environments it refuses to start when any required secret is missing or
still equals a well-known placeholder.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable

logger = logging.getLogger(__name__)

# Secrets that MUST be set in production.
_REQUIRED_SECRETS: tuple[str, ...] = (
    "TRADE_CLAW_API_KEY",
    "SECRET_KEY",
    "ENCRYPTION_KEY",
    "DB_PASSWORD",
)

# Obvious placeholders that should never be accepted.
_PLACEHOLDERS: frozenset[str] = frozenset(
    {
        "",
        "change-me",
        "change-me-in-production",
        "your-secret-key-here-change-in-production",
        "your-api-key-here",
        "your-fernet-key-here",
        "your-jwt-secret-key",
        "trading_password",
        "password",
        "admin",
    }
)


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in _PLACEHOLDERS


def _check(var_names: Iterable[str]) -> list[str]:
    """Return a list of problem descriptions (empty if fine)."""
    problems: list[str] = []
    for name in var_names:
        value = os.getenv(name)
        if value is None or value.strip() == "":
            problems.append(f"{name} is not set")
        elif _is_placeholder(value):
            problems.append(f"{name} still uses a placeholder value")
    return problems


def validate_environment(strict: bool | None = None) -> None:
    """
    Validate critical environment variables.

    When ``strict`` is True, any problem raises ``RuntimeError`` and the
    process aborts. When it is False, problems are only logged.

    If ``strict`` is None, we enable strict mode unless ``ENVIRONMENT``
    is set to ``development`` or ``test``.
    """
    env = (os.getenv("ENVIRONMENT") or "development").strip().lower()
    if strict is None:
        strict = env not in {"development", "dev", "test", "testing", "local"}

    problems = _check(_REQUIRED_SECRETS)

    if not problems:
        logger.info("Environment validation passed (env=%s).", env)
        return

    message = (
        "Refusing to start: "
        + "; ".join(problems)
        + ". Set these in your .env or deployment secrets."
    )

    if strict:
        logger.error(message)
        # Write to stderr as well so it is visible in container logs.
        raise RuntimeError(message)

    logger.warning("DEV-ONLY — %s", message)
