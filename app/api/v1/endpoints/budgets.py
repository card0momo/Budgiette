from decimal import Decimal

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.session import get_db
from app.models.models import Budget
from app.schemas.budgets import BudgetCreate, BudgetRead, BudgetStatus
from app.services.budget_service import budget_spent

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetRead])
def list_budgets(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[BudgetRead]:
    rows = db.execute(select(Budget).where(Budget.user_id == user_id).order_by(Budget.id.desc())).scalars().all()
    return [BudgetRead.model_validate(item) for item in rows]


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> BudgetRead:
    item = Budget(user_id=user_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return BudgetRead.model_validate(item)


@router.get("/status", response_model=list[BudgetStatus])
def list_budget_status(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[BudgetStatus]:
    rows = db.execute(select(Budget).where(Budget.user_id == user_id, Budget.is_active.is_(True))).scalars().all()
    status_items: list[BudgetStatus] = []

    for budget in rows:
        spent = budget_spent(db, budget)
        remaining = Decimal(budget.limit_amount) - spent
        status_items.append(
            BudgetStatus(
                **BudgetRead.model_validate(budget).model_dump(),
                spent=spent,
                remaining=remaining,
                is_over_limit=remaining < 0,
            )
        )

    return status_items
