import pandas as pd
import pytest
from src.data_generator import generate_data
from src.matcher import reconcile
from src.validator import validate_dataset


def test_generated_data_matches_ground_truth():
    orders, payments, settlements, truth = generate_data(180)
    results = reconcile(orders, payments, settlements)
    joined = results.merge(truth, on="order_id")
    assert len(results) == 180
    assert (joined.primary_classification == joined.expected_classification).all()
    assert .70 <= (results.primary_classification == "MATCHED").mean() <= .75


@pytest.mark.parametrize("label", ["PAYMENT_MISSING", "PAYMENT_FAILED", "PAYMENT_DUPLICATE", "PAYMENT_AMOUNT_MISMATCH",
    "PAYMENT_CURRENCY_MISMATCH", "SETTLEMENT_MISSING", "SETTLEMENT_AMOUNT_MISMATCH", "SETTLEMENT_CURRENCY_MISMATCH",
    "INVALID_RECORD", "REQUIRES_MANUAL_REVIEW"])
def test_each_exception_is_generated_and_classified(label):
    orders, payments, settlements, truth = generate_data(180)
    oid = truth.loc[truth.expected_classification == label, "order_id"].iloc[0]
    result = reconcile(orders, payments, settlements).set_index("order_id").loc[oid]
    assert result.primary_classification == label


def test_missing_columns_and_empty_data_are_fatal():
    assert validate_dataset(pd.DataFrame(), "orders").fatal_errors
    assert validate_dataset(pd.DataFrame({"order_id": ["x"]}), "orders").fatal_errors


def test_invalid_payment_amount_becomes_invalid_record():
    orders, payments, settlements, _ = generate_data(20)
    matched_id = reconcile(orders, payments, settlements).query("primary_classification == 'MATCHED'").order_id.iloc[0]
    payments["paid_amount"] = payments.paid_amount.astype(object)
    payments.loc[payments.order_id == matched_id, "paid_amount"] = "not-a-number"
    result = reconcile(orders, payments, settlements).set_index("order_id").loc[matched_id]
    assert result.primary_classification == "INVALID_RECORD"


def test_invalid_settlement_amount_becomes_invalid_record():
    orders, payments, settlements, _ = generate_data(20)
    matched = reconcile(orders, payments, settlements).query("primary_classification == 'MATCHED'").iloc[0]
    settlements["settled_amount"] = settlements.settled_amount.astype(object)
    settlements.loc[settlements.settlement_id == matched.settlement_id, "settled_amount"] = "bad"
    result = reconcile(orders, payments, settlements).set_index("order_id").loc[matched.order_id]
    assert result.primary_classification == "INVALID_RECORD"


def test_secondary_issues_are_preserved():
    orders, payments, settlements, _ = generate_data(30)
    oid = orders.iloc[-1].order_id
    original = payments[payments.order_id == oid].iloc[0]
    payments = pd.concat([payments, pd.DataFrame([{**original.to_dict(), "payment_id": "PAY-SECONDARY", "currency": "USD"}])], ignore_index=True)
    result = reconcile(orders, payments, settlements).set_index("order_id").loc[oid]
    assert result.primary_classification == "PAYMENT_DUPLICATE"
    assert "PAYMENT_CURRENCY_MISMATCH" in result.secondary_issues


def test_duplicate_primary_payment_identifier_is_invalid_record():
    orders, payments, settlements, _ = generate_data(30)
    oid = orders.iloc[-1].order_id
    original = payments[payments.order_id == oid].iloc[0]
    payments = pd.concat([payments, pd.DataFrame([original.to_dict()])], ignore_index=True)
    result = reconcile(orders, payments, settlements).set_index("order_id").loc[oid]
    assert result.primary_classification == "INVALID_RECORD"


def test_processed_delayed_settlement_requires_manual_review():
    orders, payments, settlements, _ = generate_data(30)
    matched = reconcile(orders, payments, settlements).query("primary_classification == 'MATCHED'").iloc[0]
    payment_date = pd.to_datetime(payments.loc[payments.payment_id == matched.payment_id, "payment_date"].iloc[0])
    settlements.loc[settlements.settlement_id == matched.settlement_id, "settlement_date"] = (payment_date + pd.Timedelta(days=8)).isoformat()
    result = reconcile(orders, payments, settlements).set_index("order_id").loc[matched.order_id]
    assert result.primary_classification == "REQUIRES_MANUAL_REVIEW"
    assert "settlement delay" in result.reason.lower()
