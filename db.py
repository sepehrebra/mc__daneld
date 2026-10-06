"""تنظیمات و اتصال مشترک SQLite برای بک‌اند."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine, event


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
