from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.models.models import TransactionDirection


@dataclass
class ParsedTransaction:
    direction: TransactionDirection
    amount: Decimal
    occurred_at: datetime
    merchant_name: str
    description: str
    external_reference: str | None = None


class BankParser(Protocol):
    key: str
    display_name: str
    sender_domains: list[str]

    def matches(self, from_addr: str, subject: str) -> bool: ...

    def parse(self, html: str, subject: str) -> ParsedTransaction | None: ...
