from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.models.models import TransactionDirection
from app.services.bank_parsers import BANK_PARSERS
from app.services.imap_service import parse_raw_email

FIXTURES = Path(__file__).parent / "fixtures"
PARSER = BANK_PARSERS["heybanco"]


def _parse_fixture(filename: str):
    raw_bytes = (FIXTURES / filename).read_bytes()
    raw_email = parse_raw_email(raw_bytes)
    assert PARSER.matches(raw_email.from_addr, raw_email.subject)
    parsed = PARSER.parse(raw_email.html, raw_email.subject)
    assert parsed is not None
    return parsed


def test_card_purchase():
    parsed = _parse_fixture("heybanco_card_purchase.eml")
    assert parsed.direction == TransactionDirection.EXPENSE
    assert parsed.amount == Decimal("55.00")
    assert parsed.occurred_at == datetime(2026, 7, 8, 9, 44)
    assert "TIENDA DEMO" in parsed.merchant_name


def test_spei_sent():
    parsed = _parse_fixture("heybanco_spei_sent.eml")
    assert parsed.direction == TransactionDirection.EXPENSE
    assert parsed.amount == Decimal("200.00")
    assert parsed.occurred_at == datetime(2026, 7, 7, 20, 31)
    assert "1111" in parsed.merchant_name
    assert "prueba" in parsed.description


def test_spei_received():
    parsed = _parse_fixture("heybanco_spei_received.eml")
    assert parsed.direction == TransactionDirection.INCOME
    assert parsed.amount == Decimal("500.00")
    assert parsed.occurred_at == datetime(2026, 6, 29, 15, 9, 0)
    assert "9988" in parsed.merchant_name
    assert parsed.description == "TRANSFERENCIA DE PRUEBA"
    assert parsed.external_reference == "2026010100001SAMPLE0000000000001"
