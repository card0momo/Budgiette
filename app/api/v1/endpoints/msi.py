from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.session import get_db
from app.models.models import Card, MSIPlan, MSIPayment
from app.schemas.msi import MSIPlanCreate, MSIPlanRead, MSIPlanUpdate, MSIPaymentCreate, MSIPaymentRead
from app.services.msi_service import remaining_balance

router = APIRouter(prefix="/msi", tags=["msi"])


def _validate_card(db: Session, user_id: int, card_id: int | None) -> None:
    if card_id is None:
        return
    card = db.get(Card, card_id)
    if card is None or card.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid card")


def _plan_to_read(plan: MSIPlan) -> MSIPlanRead:
    return MSIPlanRead(
        id=plan.id,
        user_id=plan.user_id,
        card_id=plan.card_id,
        purchase_name=plan.purchase_name,
        start_date=plan.start_date,
        total_amount=plan.total_amount,
        months_total=plan.months_total,
        monthly_payment=plan.monthly_payment,
        payments_done=plan.payments_done,
        remaining_balance=remaining_balance(plan),
    )


@router.get("/plans", response_model=list[MSIPlanRead])
def list_plans(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[MSIPlanRead]:
    rows = db.execute(select(MSIPlan).where(MSIPlan.user_id == user_id).order_by(MSIPlan.id.desc())).scalars().all()
    return [_plan_to_read(item) for item in rows]


@router.post("/plans", response_model=MSIPlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: MSIPlanCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> MSIPlanRead:
    _validate_card(db, user_id, payload.card_id)

    plan = MSIPlan(user_id=user_id, payments_done=0, **payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _plan_to_read(plan)


@router.patch("/plans/{plan_id}", response_model=MSIPlanRead)
def update_plan(
    plan_id: int,
    payload: MSIPlanUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> MSIPlanRead:
    plan = db.execute(select(MSIPlan).where(MSIPlan.id == plan_id, MSIPlan.user_id == user_id)).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MSI plan not found")

    updates = payload.model_dump(exclude_unset=True)
    if "card_id" in updates:
        _validate_card(db, user_id, updates["card_id"])

    for field, value in updates.items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return _plan_to_read(plan)


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> None:
    plan = db.execute(select(MSIPlan).where(MSIPlan.id == plan_id, MSIPlan.user_id == user_id)).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MSI plan not found")

    db.delete(plan)
    db.commit()


@router.get("/payments", response_model=list[MSIPaymentRead])
def list_all_payments(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[MSIPaymentRead]:
    rows = db.execute(
        select(MSIPayment).where(MSIPayment.user_id == user_id).order_by(MSIPayment.paid_on.desc())
    ).scalars().all()
    return [MSIPaymentRead.model_validate(item) for item in rows]


@router.post("/plans/{plan_id}/payments", response_model=MSIPaymentRead, status_code=status.HTTP_201_CREATED)
def register_payment(
    plan_id: int,
    payload: MSIPaymentCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> MSIPaymentRead:
    plan = db.execute(select(MSIPlan).where(MSIPlan.id == plan_id, MSIPlan.user_id == user_id)).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MSI plan not found")

    payment = MSIPayment(msi_plan_id=plan.id, user_id=user_id, **payload.model_dump())
    db.add(payment)

    plan.payments_done += 1
    if Decimal(plan.payments_done) * Decimal(plan.monthly_payment) > Decimal(plan.total_amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment exceeds outstanding balance")

    db.commit()
    db.refresh(payment)
    return MSIPaymentRead.model_validate(payment)


@router.get("/plans/{plan_id}/payments", response_model=list[MSIPaymentRead])
def list_payments(
    plan_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[MSIPaymentRead]:
    rows = db.execute(
        select(MSIPayment)
        .where(MSIPayment.msi_plan_id == plan_id, MSIPayment.user_id == user_id)
        .order_by(MSIPayment.paid_on.desc())
    ).scalars().all()
    return [MSIPaymentRead.model_validate(item) for item in rows]
