from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.session import get_db
from app.models.models import Notification
from app.schemas.notifications import NotificationCreate, NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[NotificationRead]:
    rows = db.execute(
        select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
    ).scalars().all()
    return [NotificationRead.model_validate(item) for item in rows]


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> NotificationRead:
    item = Notification(user_id=user_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return NotificationRead.model_validate(item)
