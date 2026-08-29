# Testing

Run `python -m pytest -q`. Tests cover matching, every generated exception, manual review, secondary issues, malformed numeric rows, required identifiers, duplicate primary IDs, empty/missing schemas, orphan references, date ordering, metrics, exact ground-truth coverage, missing-key/service/invalid-output AI fallback, structured AI success, audit persistence, and sanitized AI events. AI tests use local fakes and never require network access.

Final verification also compiles Python sources, regenerates CSVs, measures results, starts Streamlit headlessly for an HTTP smoke check, and scans repository candidates for likely secrets.
