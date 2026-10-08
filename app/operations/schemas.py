import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.crop_seasons.schemas import valid_date

OperationType = Literal[
    "planting", "irrigation", "fertilizing", "spraying", "harvesting", "other"
]
OperationStatus = Literal["planned", "in_progress", "completed", "cancelled"]
LOCAL_TIME_PATTERN = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\Z")


class OperationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop_season_id: UUID | None = None
    title: str = Field(min_length=1, max_length=150)
    operation_type: OperationType
    description: str | None = None
    scheduled_date: str
    scheduled_time: str | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Operation title is required.")
        return value

    @field_validator("scheduled_date")
    @classmethod
    def check_date(cls, value: str) -> str:
        return valid_date(value)

    @field_validator("scheduled_time")
    @classmethod
    def check_time(cls, value: str | None) -> str | None:
        if value is not None and not LOCAL_TIME_PATTERN.fullmatch(value):
            raise ValueError("Time must use HH:MM:SS format.")
        return value


class OperationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheduled_date: str | None = None
    scheduled_time: str | None = None
    status: OperationStatus | None = None
    result_notes: str | None = None

    @field_validator("scheduled_date")
    @classmethod
    def check_date(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Scheduled date cannot be null.")
        return valid_date(value)

    @field_validator("scheduled_time")
    @classmethod
    def check_time(cls, value: str | None) -> str | None:
        if value is not None and not LOCAL_TIME_PATTERN.fullmatch(value):
            raise ValueError("Time must use HH:MM:SS format.")
        return value

    @field_validator("status")
    @classmethod
    def check_status(cls, value: OperationStatus | None) -> OperationStatus:
        if value is None:
            raise ValueError("Status cannot be null.")
        return value


class OperationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plot_id: UUID
    crop_season_id: UUID | None
    created_by: UUID
    title: str
    operation_type: OperationType
    description: str | None
    scheduled_date: str
    scheduled_time: str | None
    completed_at: str | None
    status: OperationStatus
    result_notes: str | None
    created_at: str
    updated_at: str
