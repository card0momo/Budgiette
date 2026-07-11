from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Account, IngestionMailbox, IngestionMessage, NotificationType, Transaction
from app.services.bank_parsers import BANK_PARSERS
from app.services.imap_service import fetch_messages
from app.services.notification_service import notify


@dataclass
class SyncResult:
    fetched: int
    created: int


def get_or_create_bank_account(db: Session, user_id: int, bank_key: str, bank_display_name: str) -> Account:
    account = db.execute(
        select(Account).where(Account.user_id == user_id, Account.provider == bank_key)
    ).scalar_one_or_none()
    if account is not None:
        return account

    account = Account(user_id=user_id, display_name=bank_display_name, provider=bank_key)
    db.add(account)
    db.flush()
    return account


def sync_mailbox(db: Session, mailbox: IngestionMailbox) -> SyncResult:
    since = mailbox.last_synced_at.date() if mailbox.last_synced_at else mailbox.sync_start_date
    parsers = [BANK_PARSERS[key] for key in mailbox.enabled_banks if key in BANK_PARSERS]

    try:
        raw_emails = fetch_messages(mailbox, since)
    except Exception as exc:  # IMAP/network failures shouldn't crash the sync loop
        mailbox.last_sync_error = str(exc)
        db.commit()
        notify(
            db,
            mailbox.user_id,
            NotificationType.SYNC_FAILED,
            title=f"Mailbox sync failed: {mailbox.email_address}",
            message=str(exc),
            related_type="mailbox",
            related_id=mailbox.id,
        )
        return SyncResult(fetched=0, created=0)

    created = 0
    for raw in raw_emails:
        if not raw.message_id:
            continue

        already_seen = db.execute(
            select(IngestionMessage.id).where(
                IngestionMessage.mailbox_id == mailbox.id,
                IngestionMessage.message_id == raw.message_id,
            )
        ).scalar_one_or_none()
        if already_seen is not None:
            continue

        message = IngestionMessage(
            mailbox_id=mailbox.id,
            user_id=mailbox.user_id,
            message_id=raw.message_id,
            subject=raw.subject,
            received_at=raw.date.replace(tzinfo=None) if raw.date.tzinfo else raw.date,
            status="unmatched",
        )

        parser = next((p for p in parsers if p.matches(raw.from_addr, raw.subject)), None)
        if parser is not None:
            try:
                parsed = parser.parse(raw.html, raw.subject)
            except Exception as exc:
                parsed = None
                message.error = str(exc)

            if parsed is None:
                message.status = "parse_failed"
            else:
                account = get_or_create_bank_account(db, mailbox.user_id, parser.key, parser.display_name)
                transaction = Transaction(
                    user_id=mailbox.user_id,
                    account_id=account.id,
                    merchant_name=parsed.merchant_name,
                    description=parsed.description,
                    direction=parsed.direction,
                    amount=parsed.amount,
                    occurred_at=parsed.occurred_at,
                    source=f"email:{parser.key}",
                )
                db.add(transaction)
                db.flush()
                message.status = "parsed"
                message.transaction_id = transaction.id
                created += 1

        db.add(message)

    mailbox.last_synced_at = datetime.utcnow()
    mailbox.last_sync_error = None
    db.commit()

    if created > 0:
        notify(
            db,
            mailbox.user_id,
            NotificationType.NEW_TRANSACTIONS,
            title="New transactions",
            message=f"{created} new transaction(s) from {mailbox.email_address}.",
            related_type="mailbox",
            related_id=mailbox.id,
        )

    return SyncResult(fetched=len(raw_emails), created=created)
