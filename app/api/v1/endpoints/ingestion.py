from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.core.crypto import encrypt_secret
from app.db.session import get_db
from app.models.models import IngestionMailbox
from app.schemas.ingestion import BankInfo, MailboxCreate, MailboxRead, MailboxUpdate, SyncResult
from app.services.bank_parsers import BANK_PARSERS
from app.services.imap_service import mailbox_summary
from app.services.ingestion_service import get_or_create_bank_account, sync_mailbox

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _get_owned_mailbox(db: Session, mailbox_id: int, user_id: int) -> IngestionMailbox:
    mailbox = db.execute(
        select(IngestionMailbox).where(IngestionMailbox.id == mailbox_id, IngestionMailbox.user_id == user_id)
    ).scalar_one_or_none()
    if mailbox is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mailbox not found")
    return mailbox


@router.get("/banks", response_model=list[BankInfo])
def list_banks() -> list[BankInfo]:
    return [BankInfo(key=parser.key, display_name=parser.display_name) for parser in BANK_PARSERS.values()]


@router.get("/mailboxes", response_model=list[MailboxRead])
def list_mailboxes(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[MailboxRead]:
    rows = db.execute(
        select(IngestionMailbox).where(IngestionMailbox.user_id == user_id).order_by(IngestionMailbox.id.desc())
    ).scalars().all()
    return [MailboxRead.model_validate(item) for item in rows]


@router.post("/mailboxes", response_model=MailboxRead, status_code=status.HTTP_201_CREATED)
def create_mailbox(
    payload: MailboxCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> MailboxRead:
    data = payload.model_dump(exclude={"password"})
    mailbox = IngestionMailbox(user_id=user_id, encrypted_password=encrypt_secret(payload.password), **data)
    db.add(mailbox)
    db.flush()

    for bank_key in mailbox.enabled_banks:
        parser = BANK_PARSERS.get(bank_key)
        if parser is not None:
            get_or_create_bank_account(db, user_id, parser.key, parser.display_name)

    db.commit()
    db.refresh(mailbox)
    return MailboxRead.model_validate(mailbox)


@router.patch("/mailboxes/{mailbox_id}", response_model=MailboxRead)
def update_mailbox(
    mailbox_id: int,
    payload: MailboxUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> MailboxRead:
    mailbox = _get_owned_mailbox(db, mailbox_id, user_id)

    if payload.password is not None:
        mailbox.encrypted_password = encrypt_secret(payload.password)
    if payload.is_active is not None:
        mailbox.is_active = payload.is_active
    if payload.enabled_banks is not None:
        mailbox.enabled_banks = payload.enabled_banks
        for bank_key in mailbox.enabled_banks:
            parser = BANK_PARSERS.get(bank_key)
            if parser is not None:
                get_or_create_bank_account(db, user_id, parser.key, parser.display_name)

    db.commit()
    db.refresh(mailbox)
    return MailboxRead.model_validate(mailbox)


@router.delete("/mailboxes/{mailbox_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mailbox(
    mailbox_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> None:
    mailbox = _get_owned_mailbox(db, mailbox_id, user_id)
    db.delete(mailbox)
    db.commit()


@router.get("/mailboxes/{mailbox_id}/summary")
def get_mailbox_summary(
    mailbox_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, str]:
    mailbox = db.execute(
        select(IngestionMailbox).where(IngestionMailbox.id == mailbox_id, IngestionMailbox.user_id == user_id)
    ).scalar_one_or_none()
    if mailbox is None:
        return {"status": "not_found"}

    return {"status": "ok", "target": mailbox_summary(mailbox)}


@router.post("/mailboxes/{mailbox_id}/sync", response_model=SyncResult)
def trigger_sync(
    mailbox_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> SyncResult:
    mailbox = _get_owned_mailbox(db, mailbox_id, user_id)
    return sync_mailbox(db, mailbox)
