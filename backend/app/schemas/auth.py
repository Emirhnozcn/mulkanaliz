from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()

    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=1024)
    full_name: str = Field(min_length=2, max_length=150)
    registration_code: str = Field(min_length=1, max_length=200)

    @field_validator("username")
    @classmethod
    def normalize_registration_username(cls, value: str) -> str:
        return value.strip().lower()

