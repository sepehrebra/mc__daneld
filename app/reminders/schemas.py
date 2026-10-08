import re
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

ReminderStatus = Literal["pending", "processing", "sent", "failed", "cancelled"]
REMIND_AT_PATTERN = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})\Z"
)


class ReminderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remind_at: str

    @field_validator("remind_at")
    @classmethod
    def normalize_remind_at(cls, value: str) -> str:
        if not REMIND_AT_PATTERN.fullmatch(value):
            raise ValueError("remind_at must be an ISO 8601 timestamp with timezone.")
        try:
            instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("remind_at is not a valid timestamp.") from error
        if instant.utcoffset() is None:
            raise ValueError("remind_at must include a timezone.")
        return instant.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class ReminderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    operation_id: UUID
    recipient_id: UUID
    remind_at: str
    channel: Literal["in_app"]
    status: ReminderStatus
    sent_at: str | None
    read_at: str | None
    attempt_count: int
    created_at: str
    updated_at: str
