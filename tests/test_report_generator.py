import json
import pandas as pd
from src.report_generator import csv_bytes, summary_bytes


def test_csv_and_summary_exports():
    frame = pd.DataFrame([{"order_id": "ORD-1", "primary_classification": "MATCHED"}])
    assert b"ORD-1" in csv_bytes(frame)
    assert json.loads(summary_bytes({"total_records": 1})) == {"total_records": 1}

