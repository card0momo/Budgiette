from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.common import APIModel


class MSIPlanCreate(APIModel):
    purchase_name: str = Field(min_length=1, max_length=200)
    start_date: date
    total_amount: Decimal = Field(gt=0)
    months_total: int = Field(gt=0)
    monthly_payment: Decimal = Field(gt=0)


class MSIPlanRead(APIModel):
    id: int
    user_id: int
    purchase_name: str
    start_date: date
    total_amount: Decimal
    months_total: int
    monthly_payment: Decimal
    payments_done: int
    remaining_balance: Decimal


class MSIPaymentCreate(APIModel):
    paid_on: date
    amount: Decimal = Field(gt=0)
    payment_source: str = Field(min_length=1, max_length=120)


class MSIPaymentRead(APIModel):
    id: int
    msi_plan_id: int
    user_id: int
    paid_on: date
    amount: Decimal
    payment_source: str
