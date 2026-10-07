from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_users_phone"),
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("is_active IN (0, 1)", name="ck_users_is_active"),
    )

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now, onupdate=utc_now)
