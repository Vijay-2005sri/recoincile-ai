import pandas as pd

from src.currency import format_breakdown, format_money, has_valid_precision
from src.matcher import reconcile
from src.metrics import calculate_metrics
from src.validator import validate_dataset


def test_currency_precision_and_formatting_cover_zero_and_three_decimal_currencies():
    assert has_valid_precision("1200", "JPY")
    assert not has_valid_precision("1200.50", "JPY")
    assert has_valid_precision("12.345", "KWD")
    assert not has_valid_precision("12.3456", "KWD")
    assert format_money(1200, "JPY") == "¥1,200"
    assert format_money("12.345", "KWD", include_code=True) == "KWD 12.345"


def test_currency_aware_metrics_do_not_add_different_currencies():
    results = pd.DataFrame({"order_amount": [100, 20], "currency": ["USD", "INR"], "primary_classification": ["PAYMENT_MISSING", "MATCHED"]})
    metrics = calculate_metrics(results)
    assert metrics["total_amounts_by_currency"] == {"INR": 20.0, "USD": 100.0}
    assert metrics["affected_amounts_by_currency"] == {"USD": 100.0}
    assert format_breakdown(metrics["total_amounts_by_currency"], compact=True) == "₹20.00 INR · $100.00 USD"


def test_supported_foreign_currency_reconciles_when_all_records_match():
    orders = pd.DataFrame([{"order_id": "O-1", "customer_id": "C-1", "order_amount": 12.345, "currency": "KWD", "order_date": "2026-01-01", "order_status": "confirmed"}])
    payments = pd.DataFrame([{"payment_id": "P-1", "order_id": "O-1", "paid_amount": 12.345, "currency": "KWD", "payment_status": "captured", "payment_method": "card", "payment_date": "2026-01-01"}])
    settlements = pd.DataFrame([{"settlement_id": "S-1", "payment_id": "P-1", "settled_amount": 12.145, "fee": .1, "tax": .1, "currency": "KWD", "settlement_status": "processed", "settlement_date": "2026-01-02"}])
    assert validate_dataset(orders, "orders").is_valid
    result = reconcile(orders, payments, settlements)
    assert result.iloc[0].primary_classification == "MATCHED"
    assert result.iloc[0].currency == "KWD"
