from datetime import datetime, timezone
import json
import pandas as pd
from .exception_classifier import Classification as C
from .config import SETTINGS
from .validator import validate_batch


ACTIONS = {
    C.MATCHED: "No action required.", C.PAYMENT_MISSING: "Check the gateway for an attempted payment.",
    C.PAYMENT_FAILED: "Ask the customer to retry through an approved payment flow.",
    C.PAYMENT_DUPLICATE: "Review captured payments before considering a refund.",
    C.PAYMENT_AMOUNT_MISMATCH: "Compare the order invoice with the captured amount.",
    C.PAYMENT_CURRENCY_MISMATCH: "Verify currency configuration and transaction evidence.",
    C.SETTLEMENT_MISSING: "Check the expected settlement schedule with the gateway.",
    C.SETTLEMENT_AMOUNT_MISMATCH: "Review fee, tax, and settlement calculations.",
    C.SETTLEMENT_CURRENCY_MISMATCH: "Verify the settlement currency configuration.",
    C.INVALID_RECORD: "Correct the source record and run reconciliation again.",
    C.REQUIRES_MANUAL_REVIEW: "Have a finance operator review the available evidence.",
}


def _number(value):
    converted = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(converted) else float(converted)


def _secondary_issues(order, candidates: pd.DataFrame, settlements: pd.DataFrame, primary: C, tolerance: float) -> list[str]:
    """Collect additional deterministic issues without changing primary precedence."""
    issues: list[str] = []
    if candidates.empty:
        return issues
    captured = candidates[candidates.payment_status.astype(str).str.lower() == "captured"]
    payment = captured.iloc[0] if not captured.empty else candidates.iloc[0]
    paid, ordered = _number(payment.paid_amount), _number(order.order_amount)
    relevant_payments = captured if not captured.empty else candidates.iloc[[0]]
    if any(str(order.currency).upper() != str(item.currency).upper() for _, item in relevant_payments.iterrows()):
        issues.append(C.PAYMENT_CURRENCY_MISMATCH.value)
    if ordered is not None and any((value := _number(item.paid_amount)) is not None and abs(ordered - value) > tolerance for _, item in relevant_payments.iterrows()):
        issues.append(C.PAYMENT_AMOUNT_MISMATCH.value)
    related = settlements[settlements.payment_id.astype(str) == str(payment.payment_id)]
    if len(related) > 1: issues.append(C.REQUIRES_MANUAL_REVIEW.value)
    elif len(related) == 1 and paid is not None:
        settlement = related.iloc[0]
        if str(settlement.settlement_status).lower() != "processed": issues.append(C.REQUIRES_MANUAL_REVIEW.value)
        if str(payment.currency).upper() != str(settlement.currency).upper(): issues.append(C.SETTLEMENT_CURRENCY_MISMATCH.value)
        actual, fee, tax = _number(settlement.settled_amount), _number(settlement.fee), _number(settlement.tax)
        if None not in (actual, fee, tax) and abs((paid - fee - tax) - actual) > tolerance:
            issues.append(C.SETTLEMENT_AMOUNT_MISMATCH.value)
    return sorted(set(issues) - {primary.value})


def reconcile(orders: pd.DataFrame, payments: pd.DataFrame, settlements: pd.DataFrame, tolerance: float = .5) -> pd.DataFrame:
    validation = validate_batch(orders, payments, settlements)
    reports = validation.datasets
    if validation.fatal_errors: raise ValueError("; ".join(validation.fatal_errors))
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    for idx, order in orders.iterrows():
        failed, passed, secondary = [], [], []
        candidates = payments.iloc[0:0]
        payment_id = settlement_id = None
        paid = expected = actual = None
        classification = C.MATCHED
        reason = "Order, captured payment, and settlement agree within tolerance."
        if idx in reports["orders"].row_errors:
            classification, reason = C.INVALID_RECORD, "; ".join(reports["orders"].row_errors[idx])
            failed.append("valid_order")
        else:
            candidates = payments[payments.order_id.astype(str) == str(order.order_id)]
            captured = candidates[candidates.payment_status.astype(str).str.lower() == "captured"]
            if candidates.empty:
                classification, reason = C.PAYMENT_MISSING, "No payment references this order."
                failed.append("payment_exists")
            elif any(index in reports["payments"].row_errors for index in candidates.index):
                invalid_index = next(index for index in candidates.index if index in reports["payments"].row_errors)
                payment_id = str(payments.loc[invalid_index, "payment_id"])
                classification, reason = C.INVALID_RECORD, "; ".join(reports["payments"].row_errors[invalid_index])
                failed.append("valid_payment")
            elif len(captured) > 1:
                classification, reason = C.PAYMENT_DUPLICATE, "Multiple captured payments reference this order."
                failed.append("single_captured_payment")
                payment_id = str(captured.iloc[0].payment_id)
            else:
                payment = captured.iloc[0] if len(captured) == 1 else candidates.iloc[0]
                payment_id = str(payment.payment_id)
                pidx = payment.name
                if pidx in reports["payments"].row_errors:
                    classification, reason = C.INVALID_RECORD, "; ".join(reports["payments"].row_errors[pidx]); failed.append("valid_payment")
                elif str(payment.payment_status).lower() == "failed":
                    classification, reason = C.PAYMENT_FAILED, "The recorded payment attempt failed."; failed.append("payment_captured")
                    paid = float(payment.paid_amount)
                else:
                    paid = float(payment.paid_amount)
                if classification == C.MATCHED and str(order.currency).upper() != str(payment.currency).upper():
                    classification, reason = C.PAYMENT_CURRENCY_MISMATCH, "Order and payment currencies differ."; failed.append("payment_currency")
                elif classification == C.MATCHED and abs(float(order.order_amount) - paid) > tolerance:
                    classification, reason = C.PAYMENT_AMOUNT_MISMATCH, "Order and payment amounts differ beyond tolerance."; failed.append("payment_amount")
                elif classification == C.MATCHED:
                    passed += ["payment_exists", "payment_captured", "payment_currency", "payment_amount"]
                    ss = settlements[settlements.payment_id.astype(str) == payment_id]
                    if ss.empty:
                        classification, reason = C.SETTLEMENT_MISSING, "No settlement references the captured payment."; failed.append("settlement_exists")
                    elif any(index in reports["settlements"].row_errors for index in ss.index):
                        invalid_index = next(index for index in ss.index if index in reports["settlements"].row_errors)
                        settlement_id = str(settlements.loc[invalid_index, "settlement_id"])
                        classification, reason = C.INVALID_RECORD, "; ".join(reports["settlements"].row_errors[invalid_index])
                        failed.append("valid_settlement")
                    elif len(ss) > 1:
                        classification, reason = C.REQUIRES_MANUAL_REVIEW, "Multiple settlements reference the payment."; failed.append("single_settlement")
                    else:
                        settlement = ss.iloc[0]; settlement_id = str(settlement.settlement_id)
                        if settlement.name in reports["settlements"].row_errors:
                            classification, reason = C.INVALID_RECORD, "; ".join(reports["settlements"].row_errors[settlement.name]); failed.append("valid_settlement")
                        else:
                            actual = float(settlement.settled_amount); expected = paid - float(settlement.fee) - float(settlement.tax)
                        if classification == C.MATCHED and str(settlement.settlement_status).lower() != "processed":
                            classification, reason = C.REQUIRES_MANUAL_REVIEW, "The settlement is not yet processed and requires human review."; failed.append("settlement_processed")
                        elif classification == C.MATCHED and str(payment.currency).upper() != str(settlement.currency).upper():
                            classification, reason = C.SETTLEMENT_CURRENCY_MISMATCH, "Payment and settlement currencies differ."; failed.append("settlement_currency")
                        elif classification == C.MATCHED and abs(expected - actual) > tolerance:
                            classification, reason = C.SETTLEMENT_AMOUNT_MISMATCH, "Actual settlement differs from paid amount less fee and tax."; failed.append("settlement_amount")
                        elif classification == C.MATCHED:
                            delay_days = (pd.to_datetime(settlement.settlement_date) - pd.to_datetime(payment.payment_date)).total_seconds() / 86400
                            if delay_days > SETTINGS.settlement_review_days:
                                classification, reason = C.REQUIRES_MANUAL_REVIEW, f"Settlement delay of {delay_days:.1f} days exceeds the review threshold."; failed.append("settlement_delay")
                            else: passed += ["settlement_exists", "settlement_processed", "settlement_currency", "settlement_amount", "settlement_delay"]
        secondary = _secondary_issues(order, candidates, settlements, classification, tolerance)
        rows.append({"order_id": str(order.order_id), "payment_id": payment_id, "settlement_id": settlement_id,
            "currency": str(order.currency).upper(), "order_amount": float(order.order_amount) if pd.notna(pd.to_numeric(order.order_amount, errors="coerce")) else None,
            "paid_amount": paid, "expected_settlement": expected, "actual_settlement": actual,
            "primary_classification": classification.value, "secondary_issues": json.dumps(secondary), "reason": reason,
            "matched_fields": json.dumps(passed), "failed_checks": json.dumps(failed), "recommended_action": ACTIONS[classification],
            "confidence": 1.0 if classification != C.REQUIRES_MANUAL_REVIEW else .5, "processed_at": now})
    return pd.DataFrame(rows)
