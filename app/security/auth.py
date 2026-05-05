"""
Single-user API-key authentication dependency.

Usage:
    from app.security.auth import require_api_key

    @app.post("/protected")
    async def protected(_: None = Depends(require_api_key)):
        ...

The API key is compared against `TRADE_CLAW_API_KEY` in the environment using
a constant-time comparison (hmac.compare_digest) to avoid timing attacks.

For a multi-user setup swap the dependency implementation — every protected
endpoint only imports the symbol `require_api_key`, so the surface stays stable.
"""

from __future__ import annotations

import hmac
import os
import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Placeholder marker used to detect unconfigured deployments.
_UNSET_MARKERS = {
    "",
    "change-me",
    "change-me-in-production",
    "your-api-key-here",
    "your-secret-key-here-change-in-production",
}


def _load_api_key() -> str | None:
    """Read the expected API key from the environment."""
    key = os.getenv("TRADE_CLAW_API_KEY")
    if key is None:
        return None
    key = key.strip()
    if not key or key.lower() in _UNSET_MARKERS:
        return None
    return key


async def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    api_key_header: str | None = Depends(_api_key_header),
) -> None:
    """
    FastAPI dependency that enforces an API key.

    Accepts either:
      - ``Authorization: Bearer <key>`` header, or
      - ``X-API-Key: <key>`` header (used by the bundled frontend).

    Raises 401 if no key is provided, 403 if the key is wrong, and 503 if
    ``TRADE_CLAW_API_KEY`` is not configured on the server.
    """
    expected = _load_api_key()
    if expected is None:
        # Fail closed — never allow unauthenticated calls in production.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server misconfigured: TRADE_CLAW_API_KEY is not set.",
        )

    provided: str | None = None
    if credentials is not None and credentials.scheme.lower() == "bearer":
        provided = credentials.credentials or ""
    elif api_key_header:
        provided = api_key_header.strip()

    if not provided:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key (use 'Authorization: Bearer <key>' or 'X-API-Key' header).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time comparison to defeat timing oracles.
    if not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )


def generate_api_key(num_bytes: int = 32) -> str:
    """Generate a strong URL-safe API key (for first-time setup)."""
    return secrets.token_urlsafe(num_bytes)
