from pydantic import Field

from app.schemas.common import APIModel


class AccountRead(APIModel):
    id: int
    user_id: int
    display_name: str
    provider: str
    nickname: str | None
    account_number: str | None


class AccountUpdate(APIModel):
    nickname: str | None = Field(default=None, max_length=120)
    account_number: str | None = Field(default=None, max_length=60)
