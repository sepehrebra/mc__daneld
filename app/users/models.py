"""Import path for the user module; the table definition lives in db.py."""

from db import User, utc_now

__all__ = ["User", "utc_now"]
