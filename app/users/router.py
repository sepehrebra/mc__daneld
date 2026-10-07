from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.users.models import User, utc_now
from app.users.schemas import UserPublic, UserRegister
from db import get_db

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
