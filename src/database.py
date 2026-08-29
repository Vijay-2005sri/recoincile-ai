import json
import sqlite3
import uuid
from datetime import datetime, timezone
import pandas as pd


SCHEMA = """CREATE TABLE IF NOT EXISTS audit_log (
audit_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL, order_id TEXT, payment_id TEXT, settlement_id TEXT,
classification TEXT NOT NULL, rules_evaluated TEXT, rules_passed TEXT, rules_failed TEXT,
reason TEXT, ai_explanation_status TEXT, created_at TEXT NOT NULL)"""
AI_EVENT_SCHEMA = """CREATE TABLE IF NOT EXISTS ai_event_log (
event_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL, order_id TEXT NOT NULL, status TEXT NOT NULL,
error_code TEXT, created_at TEXT NOT NULL)"""


class AuditStore:
    def __init__(self, path: str = "reconcile_audit.sqlite3"):
        self.path = path
        with sqlite3.connect(path) as con:
            con.execute(SCHEMA)
            con.execute(AI_EVENT_SCHEMA)

    def save_results(self, results: pd.DataFrame, batch_id: str, ai_status: str = "not_requested") -> None:
        with sqlite3.connect(self.path) as con:
            for row in results.to_dict("records"):
                passed, failed = row["matched_fields"], row["failed_checks"]
                con.execute("INSERT INTO audit_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), batch_id,
                    row["order_id"], row["payment_id"], row["settlement_id"], row["primary_classification"],
                    json.dumps(json.loads(passed)+json.loads(failed)), passed, failed, row["reason"], ai_status, row["processed_at"]))

    def read_all(self) -> pd.DataFrame:
        with sqlite3.connect(self.path) as con: return pd.read_sql_query("SELECT * FROM audit_log ORDER BY created_at DESC", con)

    def read_batch(self, batch_id: str) -> pd.DataFrame:
        with sqlite3.connect(self.path) as con:
            return pd.read_sql_query("SELECT * FROM audit_log WHERE batch_id = ? ORDER BY created_at", con, params=(batch_id,))

    def record_ai_status(self, batch_id: str, order_id: str, status: str, error_code: str | None = None) -> None:
        """Update the record audit and append a sanitized AI event without error details or secrets."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.path) as con:
            con.execute("UPDATE audit_log SET ai_explanation_status = ? WHERE batch_id = ? AND order_id = ?", (status, batch_id, order_id))
            con.execute("INSERT INTO ai_event_log VALUES (?,?,?,?,?,?)", (str(uuid.uuid4()), batch_id, order_id, status, error_code, now))

    def read_ai_events(self, batch_id: str | None = None) -> pd.DataFrame:
        query, params = "SELECT * FROM ai_event_log", ()
        if batch_id is not None: query, params = query + " WHERE batch_id = ?", (batch_id,)
        with sqlite3.connect(self.path) as con: return pd.read_sql_query(query + " ORDER BY created_at DESC", con, params=params)
