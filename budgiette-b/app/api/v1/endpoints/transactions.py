from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.session import get_db
from app.models.models import Transaction
from app.schemas.transactions import TransactionCreate, TransactionRead

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[TransactionRead]:
    rows = db.execute(
        select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.occurred_at.desc())
    ).scalars().all()
    return [TransactionRead.model_validate(item) for item in rows]


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> TransactionRead:
    item = Transaction(user_id=user_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return TransactionRead.model_validate(item)
