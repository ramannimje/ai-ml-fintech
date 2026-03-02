from __future__ import annotations

import base64
import json
import time
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

try:
    from jose import JWTError, jwt  # type: ignore

    JOSE_AVAILABLE = True
except ImportError:  # pragma: no cover - env-dependent fallback
    JWTError = Exception  # type: ignore
    jwt = None  # type: ignore
    JOSE_AVAILABLE = False

bearer_scheme = HTTPBearer(auto_error=False)
_JWKS_CACHE: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 60 * 60


def _settings():
    return get_settings()


def _issuer() -> str:
    settings = _settings()
    return f"https://{settings.auth0_domain}/"


def _jwks_url() -> str:
    settings = _settings()
    return f"https://{settings.auth0_domain}/.well-known/jwks.json"


async def _get_jwks() -> dict[str, Any]:
    now = time.monotonic()
    if _JWKS_CACHE["keys"] and (now - _JWKS_CACHE["fetched_at"]) < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE["keys"]

    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(_jwks_url())
        response.raise_for_status()
        keys = response.json()

    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["fetched_at"] = now
    return keys


def _audience() -> str:
    settings = _settings()
    return settings.auth0_audience or settings.auth0_client_id


def create_app_jwt(user_claims: dict[str, Any]) -> str:
    settings = _settings()
    now = int(time.time())
    payload = {
        "sub": user_claims.get("sub"),
        "email": user_claims.get("email"),
        "name": user_claims.get("name"),
        "picture": user_claims.get("picture"),
        "iat": now,
        "exp": now + 3600,
        "iss": "ai-ml-fintech",
        "aud": "ai-ml-fintech-frontend",
    }
    if JOSE_AVAILABLE:
        return jwt.encode(payload, settings.secret_key, algorithm="HS256")

    # Development fallback when python-jose isn't installed.
    header = {"alg": "none", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header_b64}.{payload_b64}."


def _decode_app_jwt(token: str) -> dict[str, Any]:
    settings = _settings()
    if not JOSE_AVAILABLE:
        return _decode_unverified_payload(token)
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            audience="ai-ml-fintech-frontend",
            issuer="ai-ml-fintech",
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid application token",
        ) from exc


async def _decode_auth0_jwt(token: str) -> dict[str, Any]:
    if not JOSE_AVAILABLE:
        return _decode_unverified_payload(token)
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed JWT token",
        ) from exc

    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing JWT kid header")

    jwks = await _get_jwks()
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No matching JWKS key found")

    audiences = [_audience(), f"https://{_settings().auth0_domain}/userinfo"]
    for aud in audiences:
        try:
            return jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=aud,
                issuer=_issuer(),
            )
        except JWTError:
            continue

    # Fallback for providers returning access tokens without direct aud match.
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=_issuer(),
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Auth0 token") from exc

    client_id = _settings().auth0_client_id
    token_aud = claims.get("aud")
    aud_ok = False
    if isinstance(token_aud, str):
        aud_ok = token_aud in {client_id, f"https://{_settings().auth0_domain}/userinfo"}
    elif isinstance(token_aud, list):
        aud_ok = client_id in token_aud or f"https://{_settings().auth0_domain}/userinfo" in token_aud

    if not aud_ok and claims.get("azp") != client_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Auth0 token audience")
    return claims


async def decode_access_token(token: str) -> dict[str, Any]:
    # Support both Auth0 tokens (RS256) and locally issued app tokens (HS256).
    if token.count(".") != 2:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")

    if not JOSE_AVAILABLE:
        return _decode_unverified_payload(token)

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed JWT token") from exc
    alg = header.get("alg")
    if alg == "HS256":
        return _decode_app_jwt(token)
    return await _decode_auth0_jwt(token)


def _decode_unverified_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")

    payload = parts[1]
    payload += "=" * ((4 - len(payload) % 4) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode()).decode()
        claims = json.loads(decoded)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed JWT payload") from exc

    exp = claims.get("exp")
    if isinstance(exp, (int, float)) and exp < time.time():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return claims


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user

    if credentials and credentials.scheme.lower() == "bearer":
        claims = await decode_access_token(credentials.credentials)
        request.state.user = claims
        return claims

    app_cookie = request.cookies.get("app_token")
    if app_cookie:
        claims = await decode_access_token(app_cookie)
        request.state.user = claims
        return claims

    session_user = request.session.get("user")
    if session_user:
        request.state.user = session_user
        return session_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication token",
    )


class TokenVerificationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user = None

        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            if token:
                try:
                    request.state.user = await decode_access_token(token)
                except HTTPException:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Invalid bearer token"},
                    )

        response = await call_next(request)
        return response
