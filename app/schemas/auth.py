from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel


class TokenRead(APIModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(APIModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    full_name: str = Field(default="", max_length=120)


class UserLogin(APIModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class UserRead(APIModel):
    id: int
    username: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
