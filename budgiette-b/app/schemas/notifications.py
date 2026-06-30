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
    is_read: bool
    created_at: datetime
