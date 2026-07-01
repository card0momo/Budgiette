from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.models import Budget, BudgetPeriod, Transaction, TransactionDirection


def period_window(period: BudgetPeriod, starts_on: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(starts_on, datetime.min.time())

    if period == BudgetPeriod.WEEK:
        end_dt = start_dt + timedelta(days=7)
    elif period == BudgetPeriod.MONTH:
        if starts_on.month == 12:
            end_dt = datetime(starts_on.year + 1, 1, 1)
        else:
            end_dt = datetime(starts_on.year, starts_on.month + 1, 1)
    else:
        end_dt = datetime(starts_on.year + 1, 1, 1)

    return start_dt, end_dt


def budget_spent(db: Session, budget: Budget) -> Decimal:
    start_dt, end_dt = period_window(budget.period, budget.starts_on)

    query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        and_(
            Transaction.user_id == budget.user_id,
            Transaction.direction == TransactionDirection.EXPENSE,
            Transaction.occurred_at >= start_dt,
            Transaction.occurred_at < end_dt,
        )
    )

    if budget.category_id is not None:
        query = query.where(Transaction.category_id == budget.category_id)

    result = db.execute(query).scalar_one()
    return Decimal(result)
