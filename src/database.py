import json
import sqlite3
import uuid
import pandas as pd


SCHEMA = """CREATE TABLE IF NOT EXISTS audit_log (
audit_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL, order_id TEXT, payment_id TEXT, settlement_id TEXT,
classification TEXT NOT NULL, rules_evaluated TEXT, rules_passed TEXT, rules_failed TEXT,
reason TEXT, ai_explanation_status TEXT, created_at TEXT NOT NULL)"""


class AuditStore:
    def __init__(self, path: str = "reconcile_audit.sqlite3"):
        self.path = path
        with sqlite3.connect(path) as con: con.execute(SCHEMA)

    def save_results(self, results: pd.DataFrame, batch_id: str, ai_status: str = "not_requested") -> None:
        with sqlite3.connect(self.path) as con:
            for row in results.to_dict("records"):
                passed, failed = row["matched_fields"], row["failed_checks"]
                con.execute("INSERT INTO audit_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), batch_id,
                    row["order_id"], row["payment_id"], row["settlement_id"], row["primary_classification"],
                    json.dumps(json.loads(passed)+json.loads(failed)), passed, failed, row["reason"], ai_status, row["processed_at"]))

    def read_all(self) -> pd.DataFrame:
        with sqlite3.connect(self.path) as con: return pd.read_sql_query("SELECT * FROM audit_log ORDER BY created_at DESC", con)

