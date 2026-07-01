from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.session import get_db
from app.models.models import IngestionMailbox
from app.schemas.ingestion import MailboxCreate, MailboxRead
from app.services.imap_service import mailbox_summary

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


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
    mailbox = IngestionMailbox(user_id=user_id, **payload.model_dump())
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    return MailboxRead.model_validate(mailbox)


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
