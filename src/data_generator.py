from pathlib import Path
import random
from datetime import datetime, timedelta
import pandas as pd


CATEGORIES = ["PAYMENT_MISSING", "PAYMENT_FAILED", "PAYMENT_DUPLICATE", "PAYMENT_AMOUNT_MISMATCH",
              "PAYMENT_CURRENCY_MISMATCH", "SETTLEMENT_MISSING", "SETTLEMENT_AMOUNT_MISMATCH",
              "SETTLEMENT_CURRENCY_MISMATCH", "INVALID_RECORD", "REQUIRES_MANUAL_REVIEW"]


def generate_data(count: int = 180, seed: int = 2026) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if count < 10: raise ValueError("count must be at least 10")
    rng = random.Random(seed); orders, payments, settlements, truth = [], [], [], []
    anomaly_count = round(count * .27)
    anomaly_labels = [CATEGORIES[i % len(CATEGORIES)] for i in range(anomaly_count)]
    rng.shuffle(anomaly_labels)
    for i in range(count):
        oid = f"ORD-{i+1:04d}"; pid = f"PAY-{i+1:04d}"; amount = float(rng.randrange(200, 20001)); day = (i % 27) + 1
        order_date = datetime(2026, 7, day, 10)
        label = anomaly_labels[i] if i < anomaly_count else "MATCHED"
        order = {"order_id": oid, "customer_id": f"CUS-{rng.randrange(1, 91):03d}", "order_amount": amount,
                 "currency": "INR", "order_date": order_date.isoformat(), "order_status": "confirmed"}
        if label == "INVALID_RECORD": order["order_amount"] = -amount
        orders.append(order); truth.append({"order_id": oid, "expected_classification": label})
        if label == "PAYMENT_MISSING": continue
        payment = {"payment_id": pid, "order_id": oid, "paid_amount": amount, "currency": "INR",
                   "payment_status": "failed" if label == "PAYMENT_FAILED" else "captured", "payment_method": rng.choice(["upi", "card", "netbanking"]),
                   "payment_date": (order_date + timedelta(minutes=3)).isoformat()}
        if label == "PAYMENT_AMOUNT_MISMATCH": payment["paid_amount"] += 25
        if label == "PAYMENT_CURRENCY_MISMATCH": payment["currency"] = "USD"
        payments.append(payment)
        if label == "PAYMENT_DUPLICATE":
            payments.append({**payment, "payment_id": f"PAY-DUP-{i+1:04d}"})
        if label in {"PAYMENT_FAILED", "PAYMENT_DUPLICATE", "PAYMENT_AMOUNT_MISMATCH", "PAYMENT_CURRENCY_MISMATCH", "SETTLEMENT_MISSING", "INVALID_RECORD"}: continue
        fee, tax = round(amount * .02, 2), round(amount * .0036, 2)
        settled = round(amount - fee - tax, 2)
        delay_days = 7 if label == "REQUIRES_MANUAL_REVIEW" else rng.choice([1, 2, 2, 3, 4])
        settlement = {"settlement_id": f"SET-{i+1:04d}", "payment_id": pid, "settled_amount": settled,
                      "fee": fee, "tax": tax, "currency": "USD" if label == "SETTLEMENT_CURRENCY_MISMATCH" else "INR",
                      "settlement_status": "pending" if label == "REQUIRES_MANUAL_REVIEW" else "processed",
                      "settlement_date": (order_date + timedelta(days=delay_days, hours=2)).isoformat()}
        if label == "SETTLEMENT_AMOUNT_MISMATCH": settlement["settled_amount"] += 15
        settlements.append(settlement)
    return tuple(pd.DataFrame(x) for x in (orders, payments, settlements, truth))


def write_data(directory: str | Path = "data", count: int = 180, seed: int = 2026) -> None:
    path = Path(directory); path.mkdir(parents=True, exist_ok=True)
    for name, df in zip(("orders", "payments", "settlements", "ground_truth"), generate_data(count, seed)):
        df.to_csv(path / f"{name}.csv", index=False)


if __name__ == "__main__": write_data()
