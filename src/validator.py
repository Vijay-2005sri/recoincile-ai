from dataclasses import dataclass, field
import pandas as pd
from .currency import has_valid_precision, is_supported_currency, normalise_currency


SCHEMAS = {
    "orders": ["order_id", "customer_id", "order_amount", "currency", "order_date", "order_status"],
    "payments": ["payment_id", "order_id", "paid_amount", "currency", "payment_status", "payment_method", "payment_date"],
    "settlements": ["settlement_id", "payment_id", "settled_amount", "fee", "tax", "currency", "settlement_status", "settlement_date"],
}
IDENTIFIER_COLUMNS = {
    "orders": ["order_id", "customer_id"],
    "payments": ["payment_id", "order_id"],
    "settlements": ["settlement_id", "payment_id"],
}
PRIMARY_IDENTIFIERS = {"orders": "order_id", "payments": "payment_id", "settlements": "settlement_id"}


@dataclass
class ValidationReport:
    fatal_errors: list[str] = field(default_factory=list)
    row_errors: dict[int, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.fatal_errors


@dataclass
class BatchValidationReport:
    datasets: dict[str, ValidationReport]
    warnings: list[str] = field(default_factory=list)

    @property
    def fatal_errors(self) -> list[str]:
        return [f"{name}: {error}" for name, report in self.datasets.items() for error in report.fatal_errors]

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
    id_col = PRIMARY_IDENTIFIERS[kind]
    amount_cols = {"orders": ["order_amount"], "payments": ["paid_amount"], "settlements": ["settled_amount", "fee", "tax"]}[kind]
    date_col = {"orders": "order_date", "payments": "payment_date", "settlements": "settlement_date"}[kind]
    duplicate_mask = df[id_col].notna() & df[id_col].astype(str).str.strip().ne("") & df[id_col].duplicated(keep=False)
    duplicate_ids = set(df.loc[duplicate_mask, id_col].astype(str))
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
        for identifier in IDENTIFIER_COLUMNS[kind]:
            if pd.isna(row[identifier]) or not str(row[identifier]).strip(): errors.append(f"Missing {identifier}")
        if duplicate_mask.loc[idx]: errors.append(f"Duplicate {id_col}")
        for col in amount_cols:
            value = pd.to_numeric(pd.Series([row[col]]), errors="coerce").iloc[0]
            if pd.isna(value): errors.append(f"{col} is not numeric")
            elif value < 0 or (col in {"order_amount", "paid_amount", "settled_amount"} and value <= 0): errors.append(f"{col} has invalid value")
        if pd.isna(pd.to_datetime(row[date_col], errors="coerce")): errors.append(f"Invalid {date_col}")
        if str(row[status_col]).lower() not in valid_statuses: errors.append(f"Unrecognized {status_col}")
        currency = normalise_currency(row["currency"])
        if not is_supported_currency(currency):
            errors.append("Unrecognized currency")
        elif any(not pd.isna(pd.to_numeric(pd.Series([row[col]]), errors="coerce")).iloc[0] and not has_valid_precision(row[col], currency) for col in amount_cols):
            errors.append(f"Amount exceeds {currency} decimal precision")
        if errors: report.row_errors[int(idx)] = errors
    return report


def validate_relationships(orders: pd.DataFrame, payments: pd.DataFrame, settlements: pd.DataFrame) -> list[str]:
    warnings = []
    orphan_payments = set(payments.order_id.astype(str)) - set(orders.order_id.astype(str))
    orphan_settlements = set(settlements.payment_id.astype(str)) - set(payments.payment_id.astype(str))
    if orphan_payments: warnings.append(f"{len(orphan_payments)} orphan payment order reference(s)")
    if orphan_settlements: warnings.append(f"{len(orphan_settlements)} orphan settlement payment reference(s)")
    return warnings


def validate_batch(orders: pd.DataFrame, payments: pd.DataFrame, settlements: pd.DataFrame) -> BatchValidationReport:
    """Validate individual datasets plus cross-file references and date ordering."""
    frames = {"orders": orders, "payments": payments, "settlements": settlements}
    reports = {name: validate_dataset(frame, name) for name, frame in frames.items()}
    bundle = BatchValidationReport(reports)
    if not bundle.is_valid:
        return bundle

    bundle.warnings.extend(validate_relationships(orders, payments, settlements))
    order_dates = orders.set_index(orders.order_id.astype(str))["order_date"].apply(lambda value: pd.to_datetime(value, errors="coerce"))
    payment_dates = payments.set_index(payments.payment_id.astype(str))["payment_date"].apply(lambda value: pd.to_datetime(value, errors="coerce"))

    for idx, payment in payments.iterrows():
        order_id = str(payment.order_id)
        if order_id in order_dates.index:
            payment_date = pd.to_datetime(payment.payment_date, errors="coerce")
            order_date = order_dates.loc[order_id]
            if isinstance(order_date, pd.Series):
                reports["payments"].row_errors.setdefault(int(idx), []).append("Ambiguous duplicate order reference")
            elif pd.notna(payment_date) and pd.notna(order_date) and payment_date < order_date:
                reports["payments"].row_errors.setdefault(int(idx), []).append("payment_date precedes order_date")

    for idx, settlement in settlements.iterrows():
        payment_id = str(settlement.payment_id)
        if payment_id in payment_dates.index:
            settlement_date = pd.to_datetime(settlement.settlement_date, errors="coerce")
            payment_date = payment_dates.loc[payment_id]
            if isinstance(payment_date, pd.Series):
                reports["settlements"].row_errors.setdefault(int(idx), []).append("Ambiguous duplicate payment reference")
            elif pd.notna(settlement_date) and pd.notna(payment_date) and settlement_date < payment_date:
                reports["settlements"].row_errors.setdefault(int(idx), []).append("settlement_date precedes payment_date")
    return bundle
