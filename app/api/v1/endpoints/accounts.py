from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.session import get_db
from app.models.models import Account
from app.schemas.accounts import AccountRead, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountRead])
def list_accounts(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[AccountRead]:
    rows = db.execute(
        select(Account).where(Account.user_id == user_id).order_by(Account.id.desc())
    ).scalars().all()
    return [AccountRead.model_validate(item) for item in rows]


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> AccountRead:
    account = db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    if payload.nickname is not None:
        account.nickname = payload.nickname
    if payload.account_number is not None:
        account.account_number = payload.account_number

    db.commit()
    db.refresh(account)
    return AccountRead.model_validate(account)
