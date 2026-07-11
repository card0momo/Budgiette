from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.session import get_db
from app.models.models import Account, Card
from app.schemas.cards import CardCreate, CardRead, CardUpdate

router = APIRouter(prefix="/cards", tags=["cards"])


def _validate_account(db: Session, user_id: int, account_id: int | None) -> None:
    if account_id is None:
        return
    account = db.get(Account, account_id)
    if account is None or account.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account")


@router.get("", response_model=list[CardRead])
def list_cards(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[CardRead]:
    rows = db.execute(select(Card).where(Card.user_id == user_id).order_by(Card.id.desc())).scalars().all()
    return [CardRead.model_validate(item) for item in rows]


@router.post("", response_model=CardRead, status_code=status.HTTP_201_CREATED)
def create_card(
    payload: CardCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> CardRead:
    _validate_account(db, user_id, payload.account_id)

    card = Card(user_id=user_id, **payload.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)
    return CardRead.model_validate(card)


@router.patch("/{card_id}", response_model=CardRead)
def update_card(
    card_id: int,
    payload: CardUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> CardRead:
    card = db.execute(select(Card).where(Card.id == card_id, Card.user_id == user_id)).scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    updates = payload.model_dump(exclude_unset=True)
    if "account_id" in updates:
        _validate_account(db, user_id, updates["account_id"])

    for field, value in updates.items():
        setattr(card, field, value)

    db.commit()
    db.refresh(card)
    return CardRead.model_validate(card)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    card_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> None:
    card = db.execute(select(Card).where(Card.id == card_id, Card.user_id == user_id)).scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    db.delete(card)
    db.commit()
