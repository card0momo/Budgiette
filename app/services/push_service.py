from __future__ import annotations

import json
import logging

import httpx
import requests
from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import PushToken, WebPushSubscription

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_push_to_user(db: Session, user_id: int, title: str, body: str, data: dict | None = None) -> None:
    tokens = db.execute(select(PushToken.token).where(PushToken.user_id == user_id)).scalars().all()
    if not tokens:
        return

    messages = [
        {"to": token, "title": title, "body": body, **({"data": data} if data else {})} for token in tokens
    ]

    try:
        response = httpx.post(EXPO_PUSH_URL, json=messages, timeout=10.0)
        response.raise_for_status()
        results = response.json().get("data", [])
        for token, result in zip(tokens, results):
            if isinstance(result, dict) and result.get("status") == "error":
                logger.warning("Expo push error for token %s: %s", token, result.get("message"))
    except httpx.HTTPError:
        logger.exception("Failed to send push notification for user %s", user_id)


def send_web_push_to_user(db: Session, user_id: int, title: str, body: str, data: dict | None = None) -> None:
    settings = get_settings()
    if not settings.vapid_private_key:
        return

    subscriptions = db.execute(
        select(WebPushSubscription).where(WebPushSubscription.user_id == user_id)
    ).scalars().all()
    if not subscriptions:
        return

    payload = json.dumps({"title": title, "body": body, **({"data": data} if data else {})})

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh_key, "auth": subscription.auth_key},
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
                timeout=10.0,
            )
        except WebPushException as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in (404, 410):
                logger.info("Pruning expired web push subscription %s (status %s)", subscription.id, status_code)
                db.delete(subscription)
                db.commit()
            else:
                logger.warning("Web push failed for subscription %s: %s", subscription.id, exc)
        except requests.exceptions.RequestException:
            logger.exception("Web push network error for subscription %s", subscription.id)
