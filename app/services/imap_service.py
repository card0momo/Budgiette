from app.models.models import IngestionMailbox


def mailbox_summary(mailbox: IngestionMailbox) -> str:
    transport = "imaps" if mailbox.use_ssl else "imap"
    return f"{transport}://{mailbox.host}:{mailbox.port}"
