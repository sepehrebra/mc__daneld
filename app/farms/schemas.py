from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def valid_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Farm name is required.")
    return value


def valid_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("Invalid IANA timezone.") from error
    return value


class FarmCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    province: str | None = None
    city: str | None = None
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str = "Asia/Tehran"
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return valid_name(value)

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, value: str) -> str:
        return valid_timezone(value)

    @model_validator(mode="after")
    def coordinates_must_be_paired(self) -> "FarmCreate":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together.")
        return self


class FarmUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=150)
    province: str | None = None
    city: str | None = None
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Farm name cannot be null.")
        return valid_name(value)

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Timezone cannot be null.")
        return valid_timezone(value)


class FarmPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    province: str | None
    city: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    timezone: str
    description: str | None
    created_at: str
    updated_at: str
