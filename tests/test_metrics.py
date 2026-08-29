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

