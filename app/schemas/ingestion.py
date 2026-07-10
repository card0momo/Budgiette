from datetime import date, datetime

from pydantic import Field

from app.schemas.common import APIModel


class MailboxCreate(APIModel):
    email_address: str = Field(min_length=3, max_length=255)
    host: str = Field(min_length=2, max_length=120)
    port: int = Field(default=993, gt=0)
    use_ssl: bool = True
    password: str = Field(min_length=1)
    sync_start_date: date
    enabled_banks: list[str] = Field(default_factory=list)


class MailboxUpdate(APIModel):
    password: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None
    enabled_banks: list[str] | None = None


class MailboxRead(APIModel):
    id: int
    user_id: int
    email_address: str
    host: str
    port: int
    use_ssl: bool
    is_active: bool
    enabled_banks: list[str]
    sync_start_date: date
    last_synced_at: datetime | None
    last_sync_error: str | None


class BankInfo(APIModel):
    key: str
    display_name: str


class SyncResult(APIModel):
    fetched: int
    created: int
