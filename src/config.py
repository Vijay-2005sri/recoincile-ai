from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    amount_tolerance: float = 0.50
    database_path: str = "reconcile_audit.sqlite3"
    random_seed: int = 2026


SETTINGS = Settings()

