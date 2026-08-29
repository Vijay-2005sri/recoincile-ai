from dataclasses import dataclass, field
import pandas as pd


SCHEMAS = {
    "orders": ["order_id", "customer_id", "order_amount", "currency", "order_date", "order_status"],
    "payments": ["payment_id", "order_id", "paid_amount", "currency", "payment_status", "payment_method", "payment_date"],
    "settlements": ["settlement_id", "payment_id", "settled_amount", "fee", "tax", "currency", "settlement_status", "settlement_date"],
}


@dataclass
class ValidationReport:
    fatal_errors: list[str] = field(default_factory=list)
    row_errors: dict[int, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.fatal_errors


def validate_dataset(df: pd.DataFrame, kind: str) -> ValidationReport:
    report = ValidationReport()
    required = SCHEMAS[kind]
    if df.empty:
        report.fatal_errors.append(f"{kind} file is empty")
        return report
    missing = sorted(set(required) - set(df.columns))
    if missing:
        report.fatal_errors.append(f"Missing required columns: {', '.join(missing)}")
        return report
    id_col = {"orders": "order_id", "payments": "payment_id", "settlements": "settlement_id"}[kind]
    amount_cols = {"orders": ["order_amount"], "payments": ["paid_amount"], "settlements": ["settled_amount", "fee", "tax"]}[kind]
    date_col = {"orders": "order_date", "payments": "payment_date", "settlements": "settlement_date"}[kind]
    duplicate_ids = set(df.loc[df[id_col].duplicated(keep=False), id_col].astype(str))
    if duplicate_ids:
        report.warnings.append(f"Duplicate {id_col} values: {', '.join(sorted(duplicate_ids))}")
    valid_statuses = {
        "orders": {"created", "confirmed"},
        "payments": {"captured", "failed"},
        "settlements": {"processed", "pending"},
    }[kind]
    status_col = {"orders": "order_status", "payments": "payment_status", "settlements": "settlement_status"}[kind]
    for idx, row in df.iterrows():
        errors = []
        if pd.isna(row[id_col]) or not str(row[id_col]).strip(): errors.append(f"Missing {id_col}")
        for col in amount_cols:
            value = pd.to_numeric(pd.Series([row[col]]), errors="coerce").iloc[0]
            if pd.isna(value): errors.append(f"{col} is not numeric")
            elif value < 0 or (col in {"order_amount", "paid_amount", "settled_amount"} and value <= 0): errors.append(f"{col} has invalid value")
        if pd.isna(pd.to_datetime(row[date_col], errors="coerce")): errors.append(f"Invalid {date_col}")
        if str(row[status_col]).lower() not in valid_statuses: errors.append(f"Unrecognized {status_col}")
        if str(row["currency"]).upper() not in {"INR", "USD"}: errors.append("Unrecognized currency")
        if errors: report.row_errors[int(idx)] = errors
    return report


def validate_relationships(orders: pd.DataFrame, payments: pd.DataFrame, settlements: pd.DataFrame) -> list[str]:
    warnings = []
    orphan_payments = set(payments.order_id.astype(str)) - set(orders.order_id.astype(str))
    orphan_settlements = set(settlements.payment_id.astype(str)) - set(payments.payment_id.astype(str))
    if orphan_payments: warnings.append(f"{len(orphan_payments)} orphan payment order reference(s)")
    if orphan_settlements: warnings.append(f"{len(orphan_settlements)} orphan settlement payment reference(s)")
    return warnings

