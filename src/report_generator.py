import json
import pandas as pd


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def summary_bytes(metrics: dict) -> bytes:
    return json.dumps(metrics, indent=2, default=str).encode("utf-8")

