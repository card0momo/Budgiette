from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

from app.models.models import TransactionDirection
from app.services.bank_parsers.base import ParsedTransaction

_MONTHS_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_CARD_PURCHASE_RE = re.compile(r"servicio de alertas", re.IGNORECASE)
_SPEI_SENT_RE = re.compile(r"solicitud de transferencia", re.IGNORECASE)
_SPEI_RECEIVED_RE = re.compile(r"recepci[oó]n de transferencia", re.IGNORECASE)

_SPANISH_DATETIME_RE = re.compile(
    r"(\d{1,2})\s+(\w+)\s+(\d{4})\s+(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?",
    re.IGNORECASE,
)


def _extract_fields(soup: BeautifulSoup) -> dict[str, str]:
    """Walk every <h4> in the email and build a label->value map.

    HeyBanco uses two different layouts for these rows: a label h4 ending in
    ':' followed by a sibling value h4, or a single h4 with label+value lines
    separated by <br/>. Both collapse to the same dict shape here.
    """
    fields: dict[str, str] = {}
    headers = soup.find_all("h4")
    i = 0
    while i < len(headers):
        lines = [line.strip() for line in headers[i].get_text("\n").split("\n") if line.strip()]
        if not lines:
            i += 1
            continue
        if len(lines) == 1:
            label = lines[0]
            if label.endswith(":") and i + 1 < len(headers):
                value_lines = [line.strip() for line in headers[i + 1].get_text("\n").split("\n") if line.strip()]
                fields[label.rstrip(":").strip()] = " ".join(value_lines)
                i += 2
                continue
            i += 1
            continue
        label = lines[0].rstrip(":").strip()
        fields[label] = " ".join(lines[1:])
        i += 1
    return fields


def _parse_amount(raw: str) -> Decimal:
    cleaned = re.sub(r"[^0-9.\-]", "", raw)
    return Decimal(cleaned)


def _clean_text(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip()


def _parse_slash_datetime(raw: str, *, with_seconds: bool) -> datetime:
    cleaned = raw.replace("hrs", "").replace(" - ", " ").strip()
    fmt = "%d/%m/%Y %H:%M:%S" if with_seconds else "%d/%m/%Y %H:%M"
    return datetime.strptime(cleaned, fmt)


def _parse_spanish_datetime(raw: str) -> datetime:
    match = _SPANISH_DATETIME_RE.match(raw.strip())
    if not match:
        raise ValueError(f"Unrecognized HeyBanco date: {raw!r}")
    day, month_name, year, hour, minute, meridiem = match.groups()
    month = _MONTHS_ES.get(month_name.lower())
    if month is None:
        raise ValueError(f"Unknown Spanish month: {month_name!r}")
    hour_value = int(hour) % 12
    if meridiem.lower() == "p":
        hour_value += 12
    return datetime(int(year), month, int(day), hour_value, int(minute))


class HeyBancoParser:
    key = "heybanco"
    display_name = "HeyBanco"
    sender_domains = ["hey.inc", "heybanco.com"]

    def matches(self, from_addr: str, subject: str) -> bool:
        lowered = from_addr.lower()
        return any(domain in lowered for domain in self.sender_domains)

    def parse(self, html: str, subject: str) -> ParsedTransaction | None:
        soup = BeautifulSoup(html, "html.parser")
        fields = _extract_fields(soup)
        try:
            if _CARD_PURCHASE_RE.search(subject):
                return self._parse_card_purchase(fields)
            if _SPEI_SENT_RE.search(subject):
                return self._parse_spei_sent(fields)
            if _SPEI_RECEIVED_RE.search(subject):
                return self._parse_spei_received(fields)
        except (KeyError, ValueError, InvalidOperation):
            return None
        return None

    def _parse_card_purchase(self, fields: dict[str, str]) -> ParsedTransaction:
        merchant = _clean_text(fields["Comercio"])
        return ParsedTransaction(
            direction=TransactionDirection.EXPENSE,
            amount=_parse_amount(fields["Cantidad"]),
            occurred_at=_parse_slash_datetime(fields["Fecha y hora de la transacción"], with_seconds=False),
            merchant_name=merchant,
            description=f"Compra HeyBanco en {merchant}",
        )

    def _parse_spei_sent(self, fields: dict[str, str]) -> ParsedTransaction:
        return ParsedTransaction(
            direction=TransactionDirection.EXPENSE,
            amount=_parse_amount(fields["Monto"]),
            occurred_at=_parse_spanish_datetime(fields["Fecha de autorización"]),
            merchant_name=_clean_text(fields.get("Cuenta Destino", "Transferencia SPEI")),
            description=_clean_text(fields.get("Concepto de pago", "Transferencia SPEI enviada")),
        )

    def _parse_spei_received(self, fields: dict[str, str]) -> ParsedTransaction:
        reference = fields.get("Clave rastreo", "").strip("'").strip() or None
        return ParsedTransaction(
            direction=TransactionDirection.INCOME,
            amount=_parse_amount(fields["Cantidad"]),
            occurred_at=_parse_slash_datetime(fields["Fecha de aplicación"], with_seconds=True),
            merchant_name=_clean_text(fields.get("Cuenta origen", "Transferencia SPEI")),
            description=_clean_text(fields.get("Concepto pago", "Transferencia SPEI recibida")),
            external_reference=reference,
        )
