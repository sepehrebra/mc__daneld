"""تنظیمات، اتصال و مدل‌های دیتابیس SQLite."""

from collections.abc import Iterator
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import (
    CheckConstraint,
    Engine,
    ForeignKey,
    Index,
    Integer,
    Float,
    REAL,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Settings(BaseSettings):
    """تنظیمات محیط اجرا."""

    database_url: str = "sqlite:///./data/farm.db"
    session_ttl_hours: int = Field(default=24, gt=0, le=720)

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


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
        Index("ix_auth_sessions_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False)
    revoked_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now, onupdate=utc_now)


class Farm(Base):
    __tablename__ = "farms"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_farms_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_farms_longitude"),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="ck_farms_coordinates_pair",
        ),
        Index("ix_farms_owner_id", "owner_id"),
    )

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    owner_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    province: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    timezone: Mapped[str] = mapped_column(
        Text, nullable=False, default="Asia/Tehran", server_default="Asia/Tehran"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now, onupdate=utc_now)


class Plot(Base):
    __tablename__ = "plots"
    __table_args__ = (
        UniqueConstraint("farm_id", "name", name="uq_plots_farm_name"),
        UniqueConstraint("farm_id", "code", name="uq_plots_farm_code"),
        CheckConstraint("area_m2 > 0", name="ck_plots_area_positive"),
        Index("ix_plots_farm_id", "farm_id"),
    )

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    farm_id: Mapped[str] = mapped_column(
        Text, ForeignKey("farms.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_m2: Mapped[float] = mapped_column(REAL, nullable=False)
    soil_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now, onupdate=utc_now)


class CropSeason(Base):
    __tablename__ = "crop_seasons"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'cancelled')",
            name="ck_crop_seasons_status",
        ),
        Index("ix_crop_seasons_plot_id", "plot_id"),
    )

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    plot_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plots.id", ondelete="RESTRICT"), nullable=False
    )
    crop_name: Mapped[str] = mapped_column(Text, nullable=False)
    variety: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[str] = mapped_column(Text, nullable=False)
    actual_start_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_end_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_end_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="planned", server_default="planned"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now, onupdate=utc_now)


class Operation(Base):
    __tablename__ = "operations"
    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('planting', 'irrigation', 'fertilizing', "
            "'spraying', 'harvesting', 'other')",
            name="ck_operations_type",
        ),
        CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed', 'cancelled')",
            name="ck_operations_status",
        ),
        CheckConstraint(
            "(status = 'completed' AND completed_at IS NOT NULL) OR "
            "(status != 'completed' AND completed_at IS NULL)",
            name="ck_operations_completion_time",
        ),
        Index("ix_operations_plot_date", "plot_id", "scheduled_date"),
        Index("ix_operations_crop_season_id", "crop_season_id"),
        Index("ix_operations_created_by", "created_by"),
    )

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    plot_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plots.id", ondelete="RESTRICT"), nullable=False
    )
    crop_season_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("crop_seasons.id", ondelete="RESTRICT"), nullable=True
    )
    created_by: Mapped[str] = mapped_column(
        Text, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    operation_type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_date: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_time: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="planned", server_default="planned"
    )
    result_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now, onupdate=utc_now)


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        CheckConstraint("channel = 'in_app'", name="ck_reminders_channel"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed', 'cancelled')",
            name="ck_reminders_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_reminders_attempt_count"),
        Index("ix_reminders_operation_id", "operation_id"),
        Index("ix_reminders_recipient_status_due", "recipient_id", "status", "remind_at"),
    )

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    operation_id: Mapped[str] = mapped_column(
        Text, ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False
    )
    recipient_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    remind_at: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(
        Text, nullable=False, default="in_app", server_default="in_app"
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending", server_default="pending"
    )
    sent_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    read_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now, onupdate=utc_now)


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
