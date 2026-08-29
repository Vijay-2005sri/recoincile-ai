from datetime import datetime, timezone
import json
import pandas as pd
from .exception_classifier import Classification as C
from .validator import validate_dataset


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


def reconcile(orders: pd.DataFrame, payments: pd.DataFrame, settlements: pd.DataFrame, tolerance: float = .5) -> pd.DataFrame:
    reports = {k: validate_dataset(v, k) for k, v in (("orders", orders), ("payments", payments), ("settlements", settlements))}
    fatal = [e for r in reports.values() for e in r.fatal_errors]
    if fatal: raise ValueError("; ".join(fatal))
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    for idx, order in orders.iterrows():
        failed, passed, secondary = [], [], []
        payment_id = settlement_id = None
        paid = expected = actual = None
        classification = C.MATCHED
        reason = "Order, captured payment, and settlement agree within tolerance."
        if idx in reports["orders"].row_errors:
            classification, reason = C.INVALID_RECORD, "; ".join(reports["orders"].row_errors[idx])
            failed.append("valid_order")
        else:
            candidates = payments[payments.order_id.astype(str) == str(order.order_id)]
            captured = candidates[candidates.payment_status.str.lower() == "captured"]
            if candidates.empty:
                classification, reason = C.PAYMENT_MISSING, "No payment references this order."
                failed.append("payment_exists")
            elif len(captured) > 1:
                classification, reason = C.PAYMENT_DUPLICATE, "Multiple captured payments reference this order."
                failed.append("single_captured_payment")
                payment_id = str(captured.iloc[0].payment_id)
            else:
                payment = captured.iloc[0] if len(captured) == 1 else candidates.iloc[0]
                payment_id, paid = str(payment.payment_id), float(payment.paid_amount)
                pidx = payment.name
                if pidx in reports["payments"].row_errors:
                    classification, reason = C.INVALID_RECORD, "; ".join(reports["payments"].row_errors[pidx]); failed.append("valid_payment")
                elif str(payment.payment_status).lower() == "failed":
                    classification, reason = C.PAYMENT_FAILED, "The recorded payment attempt failed."; failed.append("payment_captured")
                elif str(order.currency).upper() != str(payment.currency).upper():
                    classification, reason = C.PAYMENT_CURRENCY_MISMATCH, "Order and payment currencies differ."; failed.append("payment_currency")
                elif abs(float(order.order_amount) - paid) > tolerance:
                    classification, reason = C.PAYMENT_AMOUNT_MISMATCH, "Order and payment amounts differ beyond tolerance."; failed.append("payment_amount")
                else:
                    passed += ["payment_exists", "payment_captured", "payment_currency", "payment_amount"]
                    ss = settlements[settlements.payment_id.astype(str) == payment_id]
                    if ss.empty:
                        classification, reason = C.SETTLEMENT_MISSING, "No settlement references the captured payment."; failed.append("settlement_exists")
                    elif len(ss) > 1:
                        classification, reason = C.REQUIRES_MANUAL_REVIEW, "Multiple settlements reference the payment."; failed.append("single_settlement")
                    else:
                        settlement = ss.iloc[0]; settlement_id = str(settlement.settlement_id)
                        actual = float(settlement.settled_amount); expected = paid - float(settlement.fee) - float(settlement.tax)
                        if settlement.name in reports["settlements"].row_errors:
                            classification, reason = C.INVALID_RECORD, "; ".join(reports["settlements"].row_errors[settlement.name]); failed.append("valid_settlement")
                        elif str(payment.currency).upper() != str(settlement.currency).upper():
                            classification, reason = C.SETTLEMENT_CURRENCY_MISMATCH, "Payment and settlement currencies differ."; failed.append("settlement_currency")
                        elif abs(expected - actual) > tolerance:
                            classification, reason = C.SETTLEMENT_AMOUNT_MISMATCH, "Actual settlement differs from paid amount less fee and tax."; failed.append("settlement_amount")
                        else: passed += ["settlement_exists", "settlement_currency", "settlement_amount"]
        rows.append({"order_id": str(order.order_id), "payment_id": payment_id, "settlement_id": settlement_id,
            "order_amount": float(order.order_amount) if pd.notna(pd.to_numeric(order.order_amount, errors="coerce")) else None,
            "paid_amount": paid, "expected_settlement": expected, "actual_settlement": actual,
            "primary_classification": classification.value, "secondary_issues": json.dumps(secondary), "reason": reason,
            "matched_fields": json.dumps(passed), "failed_checks": json.dumps(failed), "recommended_action": ACTIONS[classification],
            "confidence": 1.0 if classification != C.REQUIRES_MANUAL_REVIEW else .5, "processed_at": now})
    return pd.DataFrame(rows)

