from __future__ import annotations

import imaplib
from dataclasses import dataclass
from datetime import date, datetime
from email import message_from_bytes, utils as email_utils
from email.header import decode_header
from email.message import Message

from app.core.crypto import decrypt_secret
from app.models.models import IngestionMailbox


def mailbox_summary(mailbox: IngestionMailbox) -> str:
    transport = "imaps" if mailbox.use_ssl else "imap"
    return f"{transport}://{mailbox.host}:{mailbox.port}"


@dataclass
class RawEmail:
    message_id: str
    subject: str
    from_addr: str
    date: datetime
    html: str


def _decode_header_value(raw: str | None) -> str:
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded: list[str] = []
    for value, encoding in parts:
        if isinstance(value, bytes):
            decoded.append(value.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded.append(value)
    return "".join(decoded)


def _extract_html_body(message: Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() != "text/html":
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        return ""

    if message.get_content_type() == "text/html":
        payload = message.get_payload(decode=True)
        if payload is None:
            return ""
        charset = message.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    return ""


def parse_raw_email(raw_bytes: bytes) -> RawEmail:
    message = message_from_bytes(raw_bytes)
    message_id = (message.get("Message-ID") or "").strip()
    subject = _decode_header_value(message.get("Subject"))
    from_addr = _decode_header_value(message.get("From"))
    date_header = message.get("Date")
    parsed_date = email_utils.parsedate_to_datetime(date_header) if date_header else datetime.utcnow()
    html = _extract_html_body(message)
    return RawEmail(message_id=message_id, subject=subject, from_addr=from_addr, date=parsed_date, html=html)


def fetch_messages(mailbox: IngestionMailbox, since: date) -> list[RawEmail]:
    transport_cls = imaplib.IMAP4_SSL if mailbox.use_ssl else imaplib.IMAP4
    connection = transport_cls(mailbox.host, mailbox.port)
    try:
        connection.login(mailbox.email_address, decrypt_secret(mailbox.encrypted_password))
        connection.select("INBOX")
        status, data = connection.search(None, "SINCE", since.strftime("%d-%b-%Y"))
        if status != "OK" or not data or not data[0]:
            return []

        raw_emails: list[RawEmail] = []
        for msg_num in data[0].split():
            fetch_status, msg_data = connection.fetch(msg_num, "(RFC822)")
            if fetch_status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw_bytes = msg_data[0][1]
            raw_emails.append(parse_raw_email(raw_bytes))
        return raw_emails
    finally:
        try:
            connection.close()
        except Exception:
            pass
        connection.logout()
