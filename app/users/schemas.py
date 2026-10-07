from uuid import UUID

import phonenumbers
from phonenumbers import PhoneNumberFormat, PhoneNumberType
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    phone: str
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name is required.")
        return value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        try:
            parsed = phonenumbers.parse(value, "IR")
        except phonenumbers.NumberParseException as error:
            raise ValueError("Invalid mobile number.") from error

        if not phonenumbers.is_valid_number(parsed) or (
            phonenumbers.number_type(parsed) != PhoneNumberType.MOBILE
        ):
            raise ValueError("Invalid mobile number.")
        return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.lower() if value else None


class UserPublic(BaseModel):
    id: UUID
    full_name: str
    phone: str
    email: EmailStr | None
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
