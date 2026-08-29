# ReconcileAI

## 1. Project overview

**ReconcileAI — Intelligent Payment Reconciliation and Exception Assistant** is a hackathon-quality synthetic-data demonstration for the Razorpay AI Buildathon 2026, Track 4: AI Finance Controller. It is designed for merchant finance and operations teams.

## 2. Problem statement

Merchants often keep orders, payment-gateway transactions, and bank settlements in separate files. Missing, failed, duplicated, incorrectly valued, or delayed records make these files disagree.

## 3. Why the problem matters

Manual spreadsheet comparison is slow, error-prone, hard to reproduce, and difficult to audit. ReconcileAI gives every order a consistent classification, evidence, safe next action, and permanent local audit entry.

## 4. Features

- Load 180 bundled synthetic orders or upload CSV files.
- Validate schemas, identifiers, amounts, dates, statuses, currencies, duplicates, ordering, and orphan references.
- Reconcile orders to payments and captured payments to settlements with a configurable ₹0.50 tolerance.
- Inspect primary and secondary issues, passed and failed rules, reasons, confidence, and original source rows.
- View batch metrics and five useful analytics views.
- Export full results, exceptions, the current batch audit log, and a JSON summary.
- Request a bounded Gemini explanation or use the deterministic fallback automatically.

## 5. Architecture

CSV inputs pass through structured validation, deterministic matching, metrics, SQLite auditing, and Streamlit presentation. See [docs/architecture.md](docs/architecture.md) for the Mermaid diagram and component responsibilities.

## 6. Reconciliation workflow

The engine validates an order, finds its payment candidates, applies payment checks, finds a settlement, calculates `paid_amount - fee - tax`, and applies settlement checks. Ground truth is merged only after results exist. Fatal file errors stop the batch; row errors become `INVALID_RECORD`; relationship problems remain visible as warnings.

## 7. Meaningful AI usage

Gemini receives only one already-classified result at a time. It may explain the exception, describe the supplied financial impact, and recommend a human verification step. JSON output is schema-constrained and locally validated. AI never performs matching or arithmetic and cannot change a classification.

## 8. Safety boundaries

This demonstration uses synthetic data only. It does not call Razorpay APIs, initiate payments, issue refunds, transfer funds, change transaction data, or mark exceptions resolved. Recommendations are advisory; the deterministic engine is the source of truth.

## 9. Technology stack

Python 3.11+, Pandas, Streamlit, Plotly, SQLite through `sqlite3`, python-dotenv, Pytest, and optional Google Gemini.

## 10. Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 11. Environment configuration

```powershell
Copy-Item .env.example .env
```

Replace the placeholder `GEMINI_API_KEY` only if AI explanations are wanted. Do not commit `.env`. With no key, every deterministic feature and fallback explanation still works.

## 12. Generate data

```powershell
python -m src.data_generator
```

Generation uses seed `2026`, produces 180 orders by default, and includes all controlled exception categories, including delayed/pending manual-review cases.

## 13. Run the application

```powershell
streamlit run app.py
```

Select **Load bundled demo data**, then **Validate and reconcile**. The complete demo flow is designed to take less than three minutes.

## 14. Run tests

```powershell
python -m pytest -q
python -m compileall -q app.py src tests
```

See [docs/testing.md](docs/testing.md) for the test scope.

## 15. Dataset schemas

- Orders: `order_id`, `customer_id`, `order_amount`, `currency`, `order_date`, `order_status`
- Payments: `payment_id`, `order_id`, `paid_amount`, `currency`, `payment_status`, `payment_method`, `payment_date`
- Settlements: `settlement_id`, `payment_id`, `settled_amount`, `fee`, `tax`, `currency`, `settlement_status`, `settlement_date`
- Ground truth: `order_id`, `expected_classification`

## 16. Exception categories

The controlled enum contains `MATCHED`, `PAYMENT_MISSING`, `PAYMENT_FAILED`, `PAYMENT_DUPLICATE`, `PAYMENT_AMOUNT_MISMATCH`, `PAYMENT_CURRENCY_MISMATCH`, `SETTLEMENT_MISSING`, `SETTLEMENT_AMOUNT_MISMATCH`, `SETTLEMENT_CURRENCY_MISMATCH`, `INVALID_RECORD`, and `REQUIRES_MANUAL_REVIEW`.

Primary precedence is invalid record, missing payment, duplicate captured payment, failed payment, payment currency, payment amount, missing settlement, ambiguous or pending settlement, settlement currency, settlement amount, then matched. Additional detected problems are retained as secondary issues.

## 17. Actual measured results

The committed 180-record fixed-seed dataset produces 131 matches and 49 exceptions: a 72.78% match rate and 100% classification accuracy (180/180) against its separate generated ground truth. It includes four manual-review cases. Total reviewed amount is ₹1,794,381.00 and exception-associated amount is ₹482,481.00. These are reproducible synthetic-data results, not production performance claims; duration is measured live.

## 18. Failure handling

Missing columns and empty files stop processing with a helpful message. Invalid rows remain visible and produce `INVALID_RECORD` without being silently deleted. Missing keys, timeouts, network/quota failures, unsafe responses, and malformed AI JSON use a labelled deterministic fallback. Sanitized AI status codes—not exceptions, credentials, or stack traces—are stored in the audit database.

## 19. Limitations

The demo supports a focused schema, INR and USD, local single-user storage, and a rule-based settlement review threshold. It has no authentication or real payment integration. Accuracy measures agreement with intentionally generated ground truth, not performance on real merchant data.

## 20. Future improvements

Potential extensions include configurable rule packs, role-based access, a reviewed human-resolution workflow, signed exports, larger adversarial datasets, and evaluated batch-level natural-language questions—without granting AI financial authority.

## 21. Demo video

Video link: _to be added after recording a genuine verified demonstration_.

## 22. Screenshots

Screenshots will be added to `screenshots/` only after genuine captures exist.
