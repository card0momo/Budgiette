from pydantic import Field

from app.schemas.common import APIModel


class MailboxCreate(APIModel):
    email_address: str = Field(min_length=3, max_length=255)
    host: str = Field(min_length=2, max_length=120)
    port: int = Field(default=993, gt=0)
    use_ssl: bool = True


class MailboxRead(APIModel):
    id: int
    user_id: int
    email_address: str
    host: str
    port: int
    use_ssl: bool
    is_active: bool
