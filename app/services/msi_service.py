from decimal import Decimal

from app.models.models import MSIPlan


def remaining_balance(plan: MSIPlan) -> Decimal:
    paid = plan.monthly_payment * Decimal(plan.payments_done)
    remaining = Decimal(plan.total_amount) - paid
    return max(remaining, Decimal("0"))
