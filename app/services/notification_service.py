from __future__ import annotations

import calendar
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import (
    Budget,
    MSIPlan,
    Notification,
    NotificationPreference,
    NotificationType,
    Transaction,
    TransactionDirection,
)
from app.services.budget_service import budget_spent
from app.services.push_service import send_push_to_user, send_web_push_to_user

logger = logging.getLogger(__name__)

_TYPE_PREFERENCE_FIELD = {
    NotificationType.BUDGET_EXCEEDED: "budget_alerts_enabled",
    NotificationType.SPENDING_SPIKE: "budget_alerts_enabled",
    NotificationType.MSI_DUE: "msi_reminders_enabled",
    NotificationType.MSI_LATE: "msi_reminders_enabled",
    NotificationType.NEW_TRANSACTIONS: "ingestion_alerts_enabled",
    NotificationType.SYNC_FAILED: "sync_failure_alerts_enabled",
}

_SPIKE_MULTIPLIER = 3
_SPIKE_MIN_FLOOR = Decimal("500")
_SPIKE_LOOKBACK_DAYS = 14
_MSI_DUE_WINDOW_DAYS = 3


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def get_or_create_preferences(db: Session, user_id: int) -> NotificationPreference:
    prefs = db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    ).scalar_one_or_none()
    if prefs is None:
        prefs = NotificationPreference(user_id=user_id)
        db.add(prefs)
        db.flush()
    return prefs


def _already_notified_recently(
    db: Session,
    user_id: int,
    notification_type: NotificationType,
    related_type: str | None,
    related_id: int | None,
) -> bool:
    if related_id is not None:
        existing = db.execute(
            select(Notification.id).where(
                Notification.user_id == user_id,
                Notification.type == notification_type,
                Notification.related_type == related_type,
                Notification.related_id == related_id,
                Notification.is_read.is_(False),
            )
        ).scalar_one_or_none()
        return existing is not None

    cutoff = datetime.utcnow() - timedelta(hours=24)
    existing = db.execute(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.type == notification_type,
            Notification.created_at >= cutoff,
        )
    ).scalar_one_or_none()
    return existing is not None


def notify(
    db: Session,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> None:
    prefs = get_or_create_preferences(db, user_id)
    if not getattr(prefs, _TYPE_PREFERENCE_FIELD[notification_type]):
        return

    if _already_notified_recently(db, user_id, notification_type, related_type, related_id):
        return

    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        related_type=related_type,
        related_id=related_id,
    )
    db.add(notification)
    db.commit()

    if prefs.push_enabled:
        send_push_to_user(db, user_id, title, message)
        send_web_push_to_user(db, user_id, title, message)


def check_budget_alerts(db: Session, user_id: int) -> None:
    budgets = db.execute(
        select(Budget).where(Budget.user_id == user_id, Budget.is_active.is_(True))
    ).scalars().all()

    for budget in budgets:
        spent = budget_spent(db, budget)
        if spent > budget.limit_amount:
            notify(
                db,
                user_id,
                NotificationType.BUDGET_EXCEEDED,
                title=f"Budget exceeded: {budget.name}",
                message=f"You've spent {spent} of your {budget.limit_amount} {budget.period.value}ly budget for {budget.name}.",
                related_type="budget",
                related_id=budget.id,
            )


def check_spending_spike(db: Session, user_id: int) -> None:
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    lookback_start = today_start - timedelta(days=_SPIKE_LOOKBACK_DAYS)

    today_total = Decimal(
        db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user_id,
                Transaction.direction == TransactionDirection.EXPENSE,
                Transaction.occurred_at >= today_start,
            )
        ).scalar_one()
    )
    trailing_total = Decimal(
        db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user_id,
                Transaction.direction == TransactionDirection.EXPENSE,
                Transaction.occurred_at >= lookback_start,
                Transaction.occurred_at < today_start,
            )
        ).scalar_one()
    )

    trailing_average = trailing_total / _SPIKE_LOOKBACK_DAYS
    threshold = max(trailing_average * _SPIKE_MULTIPLIER, _SPIKE_MIN_FLOOR)

    if today_total > 0 and today_total > threshold:
        notify(
            db,
            user_id,
            NotificationType.SPENDING_SPIKE,
            title="Unusual spending today",
            message=f"You've spent {today_total} today, well above your recent daily average.",
        )


def check_msi_reminders(db: Session, user_id: int) -> None:
    plans = db.execute(
        select(MSIPlan).where(MSIPlan.user_id == user_id, MSIPlan.payments_done < MSIPlan.months_total)
    ).scalars().all()
    today = date.today()

    for plan in plans:
        next_due = _add_months(plan.start_date, plan.payments_done)

        if next_due < today:
            notify(
                db,
                user_id,
                NotificationType.MSI_LATE,
                title=f"MSI payment late: {plan.purchase_name}",
                message=f"Your payment of {plan.monthly_payment} for {plan.purchase_name} was due {next_due.isoformat()}.",
                related_type="msi_plan",
                related_id=plan.id,
            )
        elif next_due - today <= timedelta(days=_MSI_DUE_WINDOW_DAYS):
            notify(
                db,
                user_id,
                NotificationType.MSI_DUE,
                title=f"MSI payment due soon: {plan.purchase_name}",
                message=f"Your payment of {plan.monthly_payment} for {plan.purchase_name} is due {next_due.isoformat()}.",
                related_type="msi_plan",
                related_id=plan.id,
            )


def check_all(db: Session, user_id: int) -> None:
    for check in (check_budget_alerts, check_spending_spike, check_msi_reminders):
        try:
            check(db, user_id)
        except Exception:
            logger.exception("Notification check %s failed for user %s", check.__name__, user_id)
