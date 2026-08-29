# ReconcileAI

**ReconcileAI — Intelligent Payment Reconciliation and Exception Assistant** is a synthetic-data demonstration for the Razorpay AI Buildathon 2026, Track 4: AI Finance Controller. It helps finance teams compare orders, payments, and settlements while keeping AI away from accounting decisions.

## Features and safety

- Upload transaction CSVs or use 180 fixed-seed synthetic records.
- Validate data, deterministically classify exceptions, preserve reasons and SQLite audit records, display metrics and charts, and export results.
- Use Gemini for bounded explanations when configured, with a deterministic offline fallback.

This is not an accounting platform. It uses synthetic data, does not call Razorpay APIs, cannot move money, and never resolves cases. The deterministic engine is always the source of truth.

## Architecture

CSV inputs flow through structured validation, deterministic matching, metrics, SQLite audit storage, and Streamlit. Ground truth is used only after classification. See [architecture details](docs/architecture.md).

Stack: Python 3.11+, Pandas, Streamlit, Plotly, SQLite, python-dotenv, Pytest, and optional Gemini.

## Setup and commands

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m src.data_generator
python -m pytest -q
streamlit run app.py
```

Set `GEMINI_API_KEY` in `.env` only if wanted. Never commit `.env`; the app works without it. Data generation defaults to 180 records with seed `2026`.

## Schemas

- Orders: `order_id`, `customer_id`, `order_amount`, `currency`, `order_date`, `order_status`
- Payments: `payment_id`, `order_id`, `paid_amount`, `currency`, `payment_status`, `payment_method`, `payment_date`
- Settlements: `settlement_id`, `payment_id`, `settled_amount`, `fee`, `tax`, `currency`, `settlement_status`, `settlement_date`
- Ground truth: `order_id`, `expected_classification`

Expected settlement is `paid_amount - fee - tax`.

## Categories and precedence

Primary precedence is `INVALID_RECORD`, `PAYMENT_MISSING`, `PAYMENT_DUPLICATE`, `PAYMENT_FAILED`, `PAYMENT_CURRENCY_MISMATCH`, `PAYMENT_AMOUNT_MISMATCH`, `SETTLEMENT_MISSING`, `REQUIRES_MANUAL_REVIEW`, `SETTLEMENT_CURRENCY_MISMATCH`, `SETTLEMENT_AMOUNT_MISMATCH`, then `MATCHED`. AI cannot invent categories.

## Measured results

The committed 180-record dataset produces 131 matches and 49 exceptions: 72.78% match rate and 100% classification accuracy (180/180) against generated ground truth. Total reviewed amount is ₹1,753,829.00; exception-associated amount is ₹467,411.00. These deterministic synthetic-data results are not production claims. Duration is measured live.

## Failure handling

Fatal schema and empty-file errors stop processing. Row errors remain visible and can produce `INVALID_RECORD`. Missing keys, timeouts, quota failures, network failures, or invalid AI output use deterministic explanations without leaking stack traces or secrets.

## Limitations and future work

The demo has a narrow CSV schema, two currencies, local storage, and no user authentication. Future work could add configurable rules, role-based access, signed exports, and human resolution workflows without granting AI authority over money.

## Demo video and screenshots

Video: _to be added after recording_. Screenshots will be added only after genuine captures exist.
