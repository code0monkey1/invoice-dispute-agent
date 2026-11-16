"""Google authentication and sender-profile HTTP routes."""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src.usecases.auth import AuthUseCases
from src.usecases.sender_profile import InvalidSenderProfile, SenderProfileUseCases
from web.identity import Caller, GUEST_COOKIE_NAME, Identity
from web.schemas import GoogleCallbackRequest, SenderProfilePayload

logger = logging.getLogger("invoicechaser")


def _parse_google_http_error(exc: urllib.error.HTTPError) -> tuple[str, str]:
    raw_body = exc.read().decode("utf-8", errors="replace")
    error_code = f"http_{exc.code}"
    message = raw_body or str(exc)
    try:
        payload = json.loads(raw_body) if raw_body else {}
        error_code = payload.get("error") or error_code
        message = payload.get("error_description") or payload.get("error") or message
    except Exception:
        pass
    logger.error("Google OAuth HTTP error %s: %s", error_code, raw_body or str(exc))
    return error_code, message


def create_accounts_router(
    *,
    auth: AuthUseCases,
    sender_profiles: SenderProfileUseCases,
    identity: Identity,
    caller_dependency,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    sign_in_scopes: list[str],
    gmail_scopes: list[str],
    gmail_send_scope: str,
) -> APIRouter:
    router = APIRouter()

    def _auth_url(scopes: list[str], **extra: str) -> str:
        if not client_id or not redirect_uri:
            raise HTTPException(status_code=500, detail="Google OAuth is not configured on the server.")
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "include_granted_scopes": "true",
            **extra,
        }
        return f"https://accounts.google.com/o/oauth2/auth?{urllib.parse.urlencode(params)}"

    @router.get("/api/auth/google/url")
    def google_auth_url():
        """Sign-in link: basic profile access only, so Google shows no warning."""
        return {"url": _auth_url(sign_in_scopes, access_type="online", prompt="select_account")}

    @router.get("/api/auth/gmail/connect-url")
    def gmail_connect_url(caller: Caller = Depends(caller_dependency)):
        """Connect Gmail link: adds send-only access for a signed-in user.

        Offline access with consent so Google returns a refresh token we can keep.
        """
        user = caller.user()
        if not user:
            raise HTTPException(status_code=401, detail="Sign in before connecting Gmail.")
        return {"url": _auth_url(
            gmail_scopes,
            access_type="offline",
            prompt="consent",
            login_hint=user.get("email") or "",
            state="connect_gmail",
        )}

    @router.post("/api/auth/google/callback")
    def google_callback(req: GoogleCallbackRequest, request: Request, response: Response):
        if not client_id or not client_secret or not redirect_uri:
            raise HTTPException(status_code=500, detail="Google OAuth is not fully configured on the server.")

        token_data = urllib.parse.urlencode({
            "code": req.code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }).encode()
        token_request = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(token_request) as provider_response:
                token_response = json.loads(provider_response.read())
        except urllib.error.HTTPError as exc:
            error_code, message = _parse_google_http_error(exc)
            raise HTTPException(
                status_code=400,
                detail=f"Google sign-in failed ({error_code}): {message}",
            ) from exc

        access_token = token_response["access_token"]
        profile_request = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            with urllib.request.urlopen(profile_request) as provider_response:
                profile = json.loads(provider_response.read())
        except urllib.error.HTTPError as exc:
            error_code, message = _parse_google_http_error(exc)
            raise HTTPException(
                status_code=400,
                detail=f"Google profile lookup failed ({error_code}): {message}",
            ) from exc

        refresh_token = token_response.get("refresh_token", "")
        send_granted = gmail_send_scope in (token_response.get("scope") or "").split()
        try:
            user = auth.persist_google_user(
                profile,
                access_token=access_token,
                refresh_token=refresh_token,
                send_granted=send_granted,
            )
        except Exception as exc:
            logger.exception("Failed to persist Google user %s", profile.get("email"))
            raise HTTPException(
                status_code=500,
                detail="Google sign-in succeeded, but saving the user failed.",
            ) from exc

        guest_id = identity.guest_id_from_cookie(request.cookies.get(GUEST_COOKIE_NAME))
        if guest_id and guest_id != user["id"]:
            try:
                auth.migrate_guest(guest_id, user["id"])
            except Exception:
                logger.exception("Failed to migrate guest %s -> %s", guest_id, user["id"])
            response.delete_cookie(GUEST_COOKIE_NAME, path="/")

        return {
            "token": identity.create_jwt(user["id"], user["email"]),
            "user": user,
        }

    @router.get("/api/auth/me")
    def get_me_route(caller: Caller = Depends(caller_dependency)):
        user = caller.user()
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {"user": auth.present_user(user)}

    @router.get("/api/users/me/sender-profile")
    def get_sender_profile_route(caller: Caller = Depends(caller_dependency)):
        _user, user_id = caller.resolve()
        return sender_profiles.get(user_id)

    @router.patch("/api/users/me/sender-profile")
    def patch_sender_profile_route(
        payload: SenderProfilePayload,
        caller: Caller = Depends(caller_dependency),
    ):
        _user, user_id = caller.resolve()
        try:
            return sender_profiles.update(user_id, payload.model_dump(exclude_unset=True))
        except InvalidSenderProfile as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
