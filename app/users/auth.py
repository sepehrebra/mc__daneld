from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import AuthSession, User, get_db, utc_now

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession


def token_digest(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db_session: Annotated[Session, Depends(get_db)],
) -> AuthContext:
    if credentials is None:
        raise authentication_error()

    auth_session = db_session.scalar(
        select(AuthSession).where(AuthSession.token_hash == token_digest(credentials.credentials))
    )
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= utc_now()
    ):
        raise authentication_error()

    user = db_session.get(User, auth_session.user_id)
    if user is None or user.is_active != 1:
        raise authentication_error()

    return AuthContext(user=user, session=auth_session)
