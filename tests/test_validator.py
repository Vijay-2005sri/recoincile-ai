import pandas as pd
from src.data_generator import generate_data
from src.validator import validate_batch, validate_dataset


def test_missing_foreign_identifier_is_row_error():
    _, payments, _, _ = generate_data(20)
    payments.loc[0, "order_id"] = None
    report = validate_dataset(payments, "payments")
    assert "Missing order_id" in report.row_errors[0]


def test_duplicate_primary_identifier_is_row_error_and_warning():
    orders, _, _, _ = generate_data(20)
    orders.loc[1, "order_id"] = orders.loc[0, "order_id"]
    report = validate_dataset(orders, "orders")
    assert 0 in report.row_errors and 1 in report.row_errors
    assert report.warnings


def test_orphans_are_reported_as_batch_warnings():
    orders, payments, settlements, _ = generate_data(20)
    payments.loc[len(payments)] = {**payments.iloc[0].to_dict(), "payment_id": "PAY-ORPHAN", "order_id": "ORD-NOT-FOUND"}
    settlements.loc[len(settlements)] = {**settlements.iloc[0].to_dict(), "settlement_id": "SET-ORPHAN", "payment_id": "PAY-NOT-FOUND"}
    bundle = validate_batch(orders, payments, settlements)
    assert any("orphan payment" in warning for warning in bundle.warnings)
    assert any("orphan settlement" in warning for warning in bundle.warnings)


def test_payment_and_settlement_date_ordering():
    orders, payments, settlements, _ = generate_data(20)
    payment_idx = payments[payments.order_id == orders.iloc[-1].order_id].index[0]
    payments.loc[payment_idx, "payment_date"] = "2020-01-01"
    settlement_idx = settlements[settlements.payment_id == settlements.iloc[-1].payment_id].index[0]
    settlements.loc[settlement_idx, "settlement_date"] = "2019-01-01"
    bundle = validate_batch(orders, payments, settlements)
    assert "payment_date precedes order_date" in bundle.datasets["payments"].row_errors[payment_idx]
    assert "settlement_date precedes payment_date" in bundle.datasets["settlements"].row_errors[settlement_idx]
