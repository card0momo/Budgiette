from pydantic import Field

from app.schemas.common import APIModel


class CardCreate(APIModel):
    account_id: int | None = None
    nickname: str = Field(min_length=1, max_length=120)
    network: str = Field(min_length=1, max_length=30)
    last4: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")


class CardUpdate(APIModel):
    account_id: int | None = None
    nickname: str | None = Field(default=None, min_length=1, max_length=120)
    network: str | None = Field(default=None, min_length=1, max_length=30)
    last4: str | None = Field(default=None, min_length=4, max_length=4, pattern=r"^\d{4}$")


class CardRead(APIModel):
    id: int
    user_id: int
    account_id: int | None
    nickname: str
    network: str
    last4: str
