from datetime import datetime

from pydantic import Field

from app.models.models import NotificationType
from app.schemas.common import APIModel


class NotificationCreate(APIModel):
    type: NotificationType
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1)


class NotificationRead(APIModel):
    id: int
    user_id: int
    type: NotificationType
    title: str
    message: str
    related_type: str | None = None
    related_id: int | None = None
    is_read: bool
    created_at: datetime


class PushTokenCreate(APIModel):
    token: str = Field(min_length=1, max_length=255)
    platform: str = Field(min_length=1, max_length=20)


class PushTokenRead(APIModel):
    id: int
    user_id: int
    token: str
    platform: str
    created_at: datetime
    last_seen_at: datetime


class WebPushSubscriptionCreate(APIModel):
    endpoint: str = Field(min_length=1, max_length=500)
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class WebPushSubscriptionRead(APIModel):
    id: int
    user_id: int
    endpoint: str
    created_at: datetime


class VapidPublicKeyRead(APIModel):
    public_key: str


class NotificationPreferenceRead(APIModel):
    push_enabled: bool
    budget_alerts_enabled: bool
    msi_reminders_enabled: bool
    ingestion_alerts_enabled: bool
    sync_failure_alerts_enabled: bool


class NotificationPreferenceUpdate(APIModel):
    push_enabled: bool | None = None
    budget_alerts_enabled: bool | None = None
    msi_reminders_enabled: bool | None = None
    ingestion_alerts_enabled: bool | None = None
    sync_failure_alerts_enabled: bool | None = None
