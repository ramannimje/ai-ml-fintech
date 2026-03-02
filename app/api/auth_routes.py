from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
import httpx
from starlette.responses import JSONResponse

from app.core.auth import create_app_jwt, get_current_user
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
oauth = OAuth()
_auth0_registered = False


def _register_auth0_client() -> None:
    global _auth0_registered
    if _auth0_registered:
        return

    settings = get_settings()
    oauth.register(
        name="auth0",
        client_id=settings.auth0_client_id,
        client_secret=settings.auth0_client_secret,
        server_metadata_url=f"https://{settings.auth0_domain}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile email"},
    )
    _auth0_registered = True


def _frontend_redirect(path: str = "", **params: str) -> str:
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    url = f"{base}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    return url


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    _register_auth0_client()
    settings = get_settings()
    redirect_uri = settings.auth0_callback_url
    try:
        return await oauth.auth0.authorize_redirect(request, redirect_uri)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth0 login is not configured correctly. Update AUTH0_* settings.",
        ) from exc


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    _register_auth0_client()
    try:
        token = await oauth.auth0.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth0 token exchange failed") from exc

    userinfo: dict[str, Any] | None = token.get("userinfo")
    if not userinfo:
        settings = get_settings()
        access_token = token.get("access_token")
        if access_token:
            async with httpx.AsyncClient(timeout=8.0) as client:
                profile = await client.get(
                    f"https://{settings.auth0_domain}/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if profile.status_code == 200:
                    userinfo = profile.json()
    if not userinfo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to retrieve user profile")

    app_jwt = create_app_jwt(dict(userinfo))
    request.session["user"] = dict(userinfo)
    request.session["app_token"] = app_jwt

    response = RedirectResponse(_frontend_redirect("/", auth="success"))
    response.set_cookie(
        key="app_token",
        value=app_jwt,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=3600,
    )
    return response


@router.post("/logout")
async def logout(request: Request) -> JSONResponse:
    request.session.clear()
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie("app_token")
    return response


@router.get("/me")
async def me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "sub": current_user.get("sub"),
        "email": current_user.get("email"),
        "name": current_user.get("name"),
        "picture": current_user.get("picture"),
    }
