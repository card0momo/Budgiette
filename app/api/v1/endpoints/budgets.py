from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.session import get_db
from app.models.models import Budget, Category
from app.schemas.budgets import BudgetCreate, BudgetRead, BudgetStatus, BudgetUpdate
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


@router.patch("/{budget_id}", response_model=BudgetRead)
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> BudgetRead:
    budget = db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    ).scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    updates = payload.model_dump(exclude_unset=True)

    if "category_id" in updates and updates["category_id"] is not None:
        category = db.get(Category, updates["category_id"])
        if category is None or category.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category")

    for field, value in updates.items():
        setattr(budget, field, value)

    db.commit()
    db.refresh(budget)
    return BudgetRead.model_validate(budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> None:
    budget = db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    ).scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    db.delete(budget)
    db.commit()


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
