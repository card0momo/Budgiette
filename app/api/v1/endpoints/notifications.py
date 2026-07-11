from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import Notification, PushToken, WebPushSubscription
from app.schemas.notifications import (
    NotificationCreate,
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    NotificationRead,
    PushTokenCreate,
    PushTokenRead,
    VapidPublicKeyRead,
    WebPushSubscriptionCreate,
    WebPushSubscriptionRead,
)
from app.services.notification_service import get_or_create_preferences

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


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> NotificationRead:
    notification = db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    ).scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return NotificationRead.model_validate(notification)


@router.post("/push-tokens", response_model=PushTokenRead, status_code=status.HTTP_201_CREATED)
def register_push_token(
    payload: PushTokenCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> PushTokenRead:
    existing = db.execute(
        select(PushToken).where(PushToken.user_id == user_id, PushToken.token == payload.token)
    ).scalar_one_or_none()
    if existing is not None:
        existing.platform = payload.platform
        existing.last_seen_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return PushTokenRead.model_validate(existing)

    token = PushToken(user_id=user_id, token=payload.token, platform=payload.platform)
    db.add(token)
    db.commit()
    db.refresh(token)
    return PushTokenRead.model_validate(token)


@router.delete("/push-tokens", status_code=status.HTTP_204_NO_CONTENT)
def unregister_push_token(
    token: str = Query(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> None:
    existing = db.execute(
        select(PushToken).where(PushToken.user_id == user_id, PushToken.token == token)
    ).scalar_one_or_none()
    if existing is not None:
        db.delete(existing)
        db.commit()


@router.get("/vapid-public-key", response_model=VapidPublicKeyRead)
def get_vapid_public_key() -> VapidPublicKeyRead:
    return VapidPublicKeyRead(public_key=get_settings().vapid_public_key)


@router.post("/web-push-subscriptions", response_model=WebPushSubscriptionRead, status_code=status.HTTP_201_CREATED)
def register_web_push_subscription(
    payload: WebPushSubscriptionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> WebPushSubscriptionRead:
    existing = db.execute(
        select(WebPushSubscription).where(
            WebPushSubscription.user_id == user_id, WebPushSubscription.endpoint == payload.endpoint
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.p256dh_key = payload.p256dh
        existing.auth_key = payload.auth
        db.commit()
        db.refresh(existing)
        return WebPushSubscriptionRead.model_validate(existing)

    subscription = WebPushSubscription(
        user_id=user_id, endpoint=payload.endpoint, p256dh_key=payload.p256dh, auth_key=payload.auth
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return WebPushSubscriptionRead.model_validate(subscription)


@router.delete("/web-push-subscriptions", status_code=status.HTTP_204_NO_CONTENT)
def unregister_web_push_subscription(
    endpoint: str = Query(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> None:
    existing = db.execute(
        select(WebPushSubscription).where(
            WebPushSubscription.user_id == user_id, WebPushSubscription.endpoint == endpoint
        )
    ).scalar_one_or_none()
    if existing is not None:
        db.delete(existing)
        db.commit()


@router.get("/preferences", response_model=NotificationPreferenceRead)
def get_preferences(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> NotificationPreferenceRead:
    prefs = get_or_create_preferences(db, user_id)
    db.commit()
    return NotificationPreferenceRead.model_validate(prefs)


@router.patch("/preferences", response_model=NotificationPreferenceRead)
def update_preferences(
    payload: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> NotificationPreferenceRead:
    prefs = get_or_create_preferences(db, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    db.commit()
    db.refresh(prefs)
    return NotificationPreferenceRead.model_validate(prefs)
