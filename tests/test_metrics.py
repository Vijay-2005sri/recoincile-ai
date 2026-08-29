from src.data_generator import generate_data
from src.matcher import reconcile
from src.metrics import calculate_metrics


def test_ground_truth_metrics():
    orders, payments, settlements, truth = generate_data(50)
    metrics = calculate_metrics(reconcile(orders, payments, settlements), truth, .25)
    assert metrics["total_records"] == 50
    assert metrics["classification_accuracy"] == 1.0
    assert metrics["correctly_classified"] == 50
    assert metrics["processing_duration"] == .25


def test_incomplete_ground_truth_is_reported_unavailable():
    orders, payments, settlements, truth = generate_data(20)
    metrics = calculate_metrics(reconcile(orders, payments, settlements), truth.iloc[:-1])
    assert metrics["classification_accuracy"] is None
    assert "does not cover exactly" in metrics["evaluation_message"]


def test_unknown_ground_truth_classification_is_unavailable():
    orders, payments, settlements, truth = generate_data(20)
    truth.loc[0, "expected_classification"] = "AI_INVENTED_CATEGORY"
    metrics = calculate_metrics(reconcile(orders, payments, settlements), truth)
    assert metrics["classification_accuracy"] is None
    assert "unknown classifications" in metrics["evaluation_message"]
