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
    "PAYMENT_CURRENCY_MISMATCH", "SETTLEMENT_MISSING", "SETTLEMENT_AMOUNT_MISMATCH", "SETTLEMENT_CURRENCY_MISMATCH", "INVALID_RECORD"])
def test_each_exception_is_generated_and_classified(label):
    orders, payments, settlements, truth = generate_data(180)
    oid = truth.loc[truth.expected_classification == label, "order_id"].iloc[0]
    result = reconcile(orders, payments, settlements).set_index("order_id").loc[oid]
    assert result.primary_classification == label


def test_missing_columns_and_empty_data_are_fatal():
    assert validate_dataset(pd.DataFrame(), "orders").fatal_errors
    assert validate_dataset(pd.DataFrame({"order_id": ["x"]}), "orders").fatal_errors

