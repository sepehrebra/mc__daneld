import re
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SeasonStatus = Literal["planned", "active", "completed", "cancelled"]
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")


def valid_date(value: str | None) -> str | None:
    if value is None:
        return None
    if not DATE_PATTERN.fullmatch(value):
        raise ValueError("Date must use YYYY-MM-DD format.")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Date is not valid.") from error
    return value


def valid_crop_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Crop name is required.")
    return value


def validate_date_order(
    start_date: str,
    expected_end_date: str | None,
    actual_start_date: str | None,
    actual_end_date: str | None,
) -> None:
    if expected_end_date is not None and expected_end_date < start_date:
        raise ValueError("Expected end date cannot precede start date.")
    if actual_end_date is not None:
        if actual_start_date is None:
            raise ValueError("Actual start date is required when actual end date is set.")
        if actual_end_date < actual_start_date:
            raise ValueError("Actual end date cannot precede actual start date.")


class CropSeasonCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop_name: str = Field(min_length=1, max_length=150)
    variety: str | None = None
    start_date: str
    actual_start_date: str | None = None
    expected_end_date: str | None = None
    actual_end_date: str | None = None
    status: SeasonStatus = "planned"
    notes: str | None = None

    @field_validator("crop_name")
    @classmethod
    def normalize_crop_name(cls, value: str) -> str:
        return valid_crop_name(value)

    @field_validator("start_date", "actual_start_date", "expected_end_date", "actual_end_date")
    @classmethod
    def check_date(cls, value: str | None) -> str | None:
        return valid_date(value)

    @model_validator(mode="after")
    def check_date_order(self) -> "CropSeasonCreate":
        validate_date_order(
            self.start_date,
            self.expected_end_date,
            self.actual_start_date,
            self.actual_end_date,
        )
        return self


class CropSeasonUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop_name: str | None = Field(default=None, max_length=150)
    variety: str | None = None
    start_date: str | None = None
    actual_start_date: str | None = None
    expected_end_date: str | None = None
    actual_end_date: str | None = None
    status: SeasonStatus | None = None
    notes: str | None = None

    @field_validator("crop_name")
    @classmethod
    def normalize_crop_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Crop name cannot be null.")
        return valid_crop_name(value)

    @field_validator("start_date", "actual_start_date", "expected_end_date", "actual_end_date")
    @classmethod
    def check_date(cls, value: str | None) -> str | None:
        return valid_date(value)

    @field_validator("start_date", "status")
    @classmethod
    def reject_required_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Required field cannot be null.")
        return value


class CropSeasonPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plot_id: UUID
    crop_name: str
    variety: str | None
    start_date: str
    actual_start_date: str | None
    expected_end_date: str | None
    actual_end_date: str | None
    status: SeasonStatus
    notes: str | None
    created_at: str
    updated_at: str
