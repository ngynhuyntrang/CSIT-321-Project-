from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

ALLOWED_EMAIL_DOMAINS = ("@uow.edu.au", "@uowmail.edu.au")


class SignupRequest(BaseModel):
    email: str
    full_name: str
    student_number: str | None = None
    role: Literal["student", "staff"] = "student"
    password: str

    @field_validator("email")
    @classmethod
    def uow_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not value.endswith(ALLOWED_EMAIL_DOMAINS):
            raise ValueError("Use your @uowmail.edu.au or @uow.edu.au address.")
        return value

    @field_validator("full_name")
    @classmethod
    def non_empty_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name is required.")
        return value

    @field_validator("password")
    @classmethod
    def strong_enough(cls, value: str) -> str:
        if len(value) < 10 or not any(ch.isdigit() for ch in value):
            raise ValueError("Password needs at least 10 characters, including a number.")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    student_number: str | None
    role: str
    status: str
    created_at: datetime


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    user: UserOut


class UserUpdate(BaseModel):
    role: Literal["student", "staff", "admin"] | None = None
    status: Literal["active", "pending", "disabled"] | None = None
