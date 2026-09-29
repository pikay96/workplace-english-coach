import hashlib
import hmac
import re
import secrets

from fastapi import HTTPException, Request, Response


def signature(guest: str, secret: str) -> str:
    return hmac.new(secret.encode(), guest.encode(), hashlib.sha256).hexdigest()


def guest(request: Request) -> str:
    token = request.cookies.get("workplace_guest", "")
    parts = token.split(".")
    if len(parts) != 2 or not re.fullmatch(r"[a-f0-9]{32}", parts[0]):
        raise HTTPException(401, "guest_required")
    expected = signature(parts[0], request.app.state.config.guest_cookie_secret.get_secret_value())
    if not hmac.compare_digest(expected, parts[1]):
        raise HTTPException(401, "guest_required")
    return parts[0]


def establish(request: Request, response: Response):
    try:
        identity = guest(request)
    except HTTPException:
        identity = secrets.token_hex(16)
    config = request.app.state.config
    value = f"{identity}.{signature(identity, config.guest_cookie_secret.get_secret_value())}"
    response.set_cookie(
        "workplace_guest",
        value,
        max_age=30 * 86400,
        httponly=True,
        secure=config.cookie_secure,
        samesite="lax",
        path="/",
    )
