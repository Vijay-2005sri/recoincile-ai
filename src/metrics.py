import pandas as pd


def calculate_metrics(results: pd.DataFrame, ground_truth: pd.DataFrame | None = None, duration: float | None = None) -> dict:
    total = len(results); matched = int((results.primary_classification == "MATCHED").sum())
    metrics = {"total_records": total, "matched_records": matched, "exception_records": total - matched,
        "match_rate": matched / total if total else None, "exception_rate": (total - matched) / total if total else None,
        "unresolved_count": total - matched, "total_amount_reviewed": float(results.order_amount.fillna(0).sum()) if total else 0,
        "affected_amount": float(results.loc[results.primary_classification != "MATCHED", "order_amount"].fillna(0).sum()) if total else 0,
        "processing_duration": duration, "counts_per_category": results.primary_classification.value_counts().to_dict() if total else {},
        "classification_accuracy": None, "correctly_classified": None, "per_category": {}}
    if ground_truth is not None and not ground_truth.empty:
        joined = results.merge(ground_truth, on="order_id", how="inner")
        joined["correct"] = joined.primary_classification == joined.expected_classification
        metrics["correctly_classified"] = int(joined.correct.sum())
        metrics["classification_accuracy"] = float(joined.correct.mean()) if len(joined) else None
        categories = sorted(set(joined.primary_classification) | set(joined.expected_classification))
        for cat in categories:
            tp = int(((joined.primary_classification == cat) & (joined.expected_classification == cat)).sum())
            predicted = int((joined.primary_classification == cat).sum()); actual = int((joined.expected_classification == cat).sum())
            metrics["per_category"][cat] = {"precision": tp / predicted if predicted else None, "recall": tp / actual if actual else None}
    return metrics

