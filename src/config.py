from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    amount_tolerance: float = 0.50
    settlement_review_days: int = 5
    ai_timeout_ms: int = 10_000
    database_path: str = "reconcile_audit.sqlite3"
    random_seed: int = 2026


SETTINGS = Settings()
