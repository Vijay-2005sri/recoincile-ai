"""Currency metadata and display helpers for deterministic reconciliation."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


# Curated ISO-4217 set used by the demo and custom CSV validation.  The
# decimal precision is important: JPY is zero-decimal, while KWD/BHD/OMR use
# three decimal places.
CURRENCY_DECIMALS = {
    "INR": 2, "USD": 2, "EUR": 2, "GBP": 2, "AED": 2, "SGD": 2,
    "AUD": 2, "CAD": 2, "JPY": 0, "KWD": 3, "BHD": 3, "OMR": 3,
}
CURRENCY_SYMBOLS = {
    "INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "AED": "AED ",
    "SGD": "S$", "AUD": "A$", "CAD": "C$", "JPY": "¥", "KWD": "KWD ",
    "BHD": "BHD ", "OMR": "OMR ",
}


def normalise_currency(value: object) -> str:
    return str(value or "").strip().upper()


def is_supported_currency(value: object) -> bool:
    return normalise_currency(value) in CURRENCY_DECIMALS


def has_valid_precision(value: object, currency: object) -> bool:
    """Return whether a major-unit amount fits that currency's precision."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return False
    if not amount.is_finite() or not is_supported_currency(currency):
        return False
    return max(0, -amount.as_tuple().exponent) <= CURRENCY_DECIMALS[normalise_currency(currency)]


def format_money(value: object, currency: object, *, include_code: bool = False) -> str:
    code = normalise_currency(currency)
    if value is None or code not in CURRENCY_DECIMALS:
        return "—"
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "—"
    if not amount.is_finite():
        return "—"
    decimals = CURRENCY_DECIMALS[code]
    rendered = f"{amount:,.{decimals}f}"
    prefix = CURRENCY_SYMBOLS[code]
    # A code suffix keeps symbols such as $ unambiguous in mixed-currency
    # summaries, while codes that are already prefixes are not repeated.
    if include_code and prefix.strip() != code:
        return f"{prefix}{rendered} {code}"
    return f"{prefix}{rendered}"


def format_breakdown(amounts: dict[str, float], *, compact: bool = False) -> str:
    if not amounts:
        return "—"
    parts = [format_money(amount, code, include_code=True) for code, amount in sorted(amounts.items())]
    return " · ".join(parts) if compact else " | ".join(parts)
