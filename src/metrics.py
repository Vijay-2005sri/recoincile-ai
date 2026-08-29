import pandas as pd
from .exception_classifier import Classification


def calculate_metrics(results: pd.DataFrame, ground_truth: pd.DataFrame | None = None, duration: float | None = None) -> dict:
    total = len(results); matched = int((results.primary_classification == "MATCHED").sum())
    metrics = {"total_records": total, "matched_records": matched, "exception_records": total - matched,
        "match_rate": matched / total if total else None, "exception_rate": (total - matched) / total if total else None,
        "unresolved_count": total - matched, "total_amount_reviewed": float(results.order_amount.fillna(0).sum()) if total else 0,
        "affected_amount": float(results.loc[results.primary_classification != "MATCHED", "order_amount"].fillna(0).sum()) if total else 0,
        "processing_duration": duration, "counts_per_category": results.primary_classification.value_counts().to_dict() if total else {},
        "classification_accuracy": None, "correctly_classified": None, "per_category": {},
        "evaluation_message": "Ground truth was not provided; accuracy is unavailable."}
    if ground_truth is not None and not ground_truth.empty:
        missing = {"order_id", "expected_classification"} - set(ground_truth.columns)
        if missing:
            metrics["evaluation_message"] = f"Ground truth is missing columns: {', '.join(sorted(missing))}."
            return metrics
        if ground_truth.order_id.isna().any() or ground_truth.order_id.astype(str).duplicated().any():
            metrics["evaluation_message"] = "Ground truth contains missing or duplicate order IDs."
            return metrics
        allowed = {classification.value for classification in Classification}
        if ground_truth.expected_classification.isna().any() or not set(ground_truth.expected_classification.astype(str)).issubset(allowed):
            metrics["evaluation_message"] = "Ground truth contains missing or unknown classifications."
            return metrics
        result_ids, truth_ids = set(results.order_id.astype(str)), set(ground_truth.order_id.astype(str))
        if result_ids != truth_ids:
            metrics["evaluation_message"] = "Ground truth does not cover exactly the reconciled order IDs."
            return metrics
        result_copy, truth_copy = results.copy(), ground_truth.copy()
        result_copy["order_id"] = result_copy.order_id.astype(str); truth_copy["order_id"] = truth_copy.order_id.astype(str)
        joined = result_copy.merge(truth_copy, on="order_id", how="inner")
        joined["correct"] = joined.primary_classification == joined.expected_classification
        metrics["correctly_classified"] = int(joined.correct.sum())
        metrics["classification_accuracy"] = float(joined.correct.mean()) if len(joined) else None
        metrics["evaluation_message"] = f"Evaluated all {len(joined)} reconciled records against ground truth."
        categories = sorted(set(joined.primary_classification) | set(joined.expected_classification))
        for cat in categories:
            tp = int(((joined.primary_classification == cat) & (joined.expected_classification == cat)).sum())
            predicted = int((joined.primary_classification == cat).sum()); actual = int((joined.expected_classification == cat).sum())
            metrics["per_category"][cat] = {"precision": tp / predicted if predicted else None, "recall": tp / actual if actual else None}
    return metrics
