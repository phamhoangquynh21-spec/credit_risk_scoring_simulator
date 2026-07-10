"""Authentication: verify a Supabase user JWT via the Supabase auth API
(no JWT secret needed) and expose the caller's id + role."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header

from .errors import AppError
from .settings import settings


@dataclass
class Principal:
    user_id: str
    role: str


def verify_token(token: str) -> tuple[str, str]:
    """Return (user_id, role) for a valid Supabase access token, else raise.

    Uses the anon client's auth.get_user(token); role is read from profiles
    via a service-role client. This is the seam tests monkeypatch.
    """
    from supabase import create_client

    anon = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        resp = anon.auth.get_user(token)
    except Exception as exc:  # network / invalid token
        raise AppError("unauthorized", "invalid or expired token", 401) from exc
    user = getattr(resp, "user", None)
    if user is None:
        raise AppError("unauthorized", "invalid or expired token", 401)

    try:
        svc = create_client(settings.supabase_url, settings.supabase_service_role_key)
        prof = (svc.table("profiles").select("role")
                .eq("user_id", user.id).limit(1).execute().data)
        role = prof[0]["role"] if prof else "analyst"
    except Exception:  # backend hiccup (DB down, RLS, network): fail closed
        role = "analyst"
    return user.id, role


def get_principal(authorization: str | None = Header(default=None)) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("unauthorized", "missing bearer token", 401)
    token = authorization.split(" ", 1)[1].strip()
    user_id, role = verify_token(token)
    return Principal(user_id=user_id, role=role)


def require_role(*roles: str):
    from fastapi import Depends

    def _checked(principal: Principal = Depends(get_principal)) -> Principal:
        if roles and principal.role not in roles and principal.role != "admin":
            raise AppError("forbidden", "insufficient role", 403)
        return principal

    return _checked
