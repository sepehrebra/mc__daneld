"""تنظیمات، اتصال و مدل‌های دیتابیس SQLite."""

from collections.abc import Iterator
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import CheckConstraint, Engine, Integer, Text, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Settings(BaseSettings):
    """تنظیمات محیط اجرا."""

    database_url: str = "sqlite:///./data/farm.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _ensure_sqlite_directory(database_url: str) -> None:
    """پوشهٔ فایل دیتابیس SQLite را، در صورت نیاز، می‌سازد."""
    if not database_url.startswith("sqlite:///") or database_url == "sqlite:///:memory:":
        return

    database_path = database_url.removeprefix("sqlite:///")
    Path(database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def create_database_engine(database_url: str | None = None) -> Engine:
    """Engine دیتابیس را با فعال‌بودن کلیدهای خارجی SQLite ایجاد می‌کند."""
    url = database_url or get_settings().database_url
    _ensure_sqlite_directory(url)
    database_engine = create_engine(url, future=True)

    if url.startswith("sqlite"):

        @event.listens_for(database_engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            dbapi_connection.execute("PRAGMA foreign_keys = ON")

    return database_engine


engine = create_database_engine()


class Base(DeclarativeBase):
    pass


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


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
