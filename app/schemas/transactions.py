from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models.models import TransactionDirection
from app.schemas.common import APIModel


class TransactionCreate(APIModel):
    category_id: int | None = None
    merchant_name: str = Field(min_length=1, max_length=200)
    description: str = ""
    direction: TransactionDirection
    amount: Decimal = Field(gt=0)
    occurred_at: datetime
    source: str = "manual"


class TransactionUpdate(APIModel):
    category_id: int | None = None
    merchant_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    direction: TransactionDirection | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    occurred_at: datetime | None = None


class TransactionRead(APIModel):
    id: int
    user_id: int
    category_id: int | None = None
    account_id: int | None = None
    merchant_name: str
    description: str
    direction: TransactionDirection
    amount: Decimal
    occurred_at: datetime
    source: str
