from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.users.auth import AuthContext, authentication_error, require_auth, token_digest
from app.users.schemas import LoginResult, UserLogin, UserPublic, UserRegister
from db import AuthSession, User, get_db, get_settings, utc_now

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
password_hasher = PasswordHash.recommended()


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, session: Annotated[Session, Depends(get_db)]) -> User:
    now = utc_now()
    user = User(
        full_name=payload.full_name,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        password_hash=password_hasher.hash(payload.password),
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone or email is already registered.",
        ) from error
    session.refresh(user)
    return user


@router.post("/login", response_model=LoginResult)
def login(payload: UserLogin, session: Annotated[Session, Depends(get_db)]) -> LoginResult:
    user = session.scalar(select(User).where(User.phone == payload.phone))
    if user is None or user.is_active != 1 or not password_hasher.verify(
        payload.password, user.password_hash
    ):
        raise authentication_error()

    raw_token = token_urlsafe(32)
    now = utc_now()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=get_settings().session_ttl_hours)
    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    session.add(
        AuthSession(
            user_id=user.id,
            token_hash=token_digest(raw_token),
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
    return LoginResult(access_token=raw_token, expires_at=expires_at)


@router.get("/me", response_model=UserPublic)
def current_user(context: Annotated[AuthContext, Depends(require_auth)]) -> User:
    return context.user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    context: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> None:
    now = utc_now()
    context.session.revoked_at = now
    context.session.updated_at = now
    session.commit()
