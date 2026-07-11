from datetime import date
from decimal import Decimal

from pydantic import Field

from app.models.models import BudgetPeriod
from app.schemas.common import APIModel


class BudgetCreate(APIModel):
    category_id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    period: BudgetPeriod
    limit_amount: Decimal = Field(gt=0)
    starts_on: date


class BudgetUpdate(APIModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    period: BudgetPeriod | None = None
    limit_amount: Decimal | None = Field(default=None, gt=0)
    starts_on: date | None = None
    is_active: bool | None = None


class BudgetRead(APIModel):
    id: int
    user_id: int
    category_id: int | None = None
    name: str
    period: BudgetPeriod
    limit_amount: Decimal
    starts_on: date
    is_active: bool


class BudgetStatus(BudgetRead):
    spent: Decimal
    remaining: Decimal
    is_over_limit: bool
