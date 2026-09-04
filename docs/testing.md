# Testing

Run `python -m pytest -q`. Tests cover matching, every generated exception, manual review, secondary issues, malformed numeric rows, required identifiers, duplicate primary IDs, empty/missing schemas, orphan references, date ordering, metrics, exact ground-truth coverage, zero- and three-decimal currency validation, multi-currency summary separation, missing-key/service/invalid-output AI fallback, structured AI success, audit persistence, and sanitized AI events. AI tests use local fakes and never require network access.

Final verification also compiles Python sources, performs a fixed-seed 180-record dry run against its ground truth, starts Streamlit headlessly for an HTTP smoke check, and scans repository candidates for likely secrets.
