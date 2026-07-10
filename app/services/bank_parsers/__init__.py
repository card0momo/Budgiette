from app.services.bank_parsers.base import BankParser, ParsedTransaction
from app.services.bank_parsers.heybanco import HeyBancoParser

BANK_PARSERS: dict[str, BankParser] = {
    "heybanco": HeyBancoParser(),
}

__all__ = ["BANK_PARSERS", "BankParser", "ParsedTransaction"]
