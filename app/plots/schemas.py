from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def nonempty_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")
    return normalized


class PlotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=50)
    area_m2: float = Field(gt=0, allow_inf_nan=False)
    soil_type: str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return nonempty_text(value, "Plot name")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return nonempty_text(value, "Plot code") if value is not None else None


class PlotUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=150)
    code: str | None = Field(default=None, max_length=50)
    area_m2: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    soil_type: str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Plot name cannot be null.")
        return nonempty_text(value, "Plot name")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return nonempty_text(value, "Plot code") if value is not None else None

    @field_validator("area_m2")
    @classmethod
    def reject_null_area(cls, value: float | None) -> float:
        if value is None:
            raise ValueError("Plot area cannot be null.")
        return value


class PlotPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    farm_id: UUID
    name: str
    code: str | None
    area_m2: float
    soil_type: str | None
    description: str | None
    created_at: str
    updated_at: str
