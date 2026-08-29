# Testing

Run `python -m pytest -q`. Tests cover matching, each generated exception, invalid and empty input, metrics and ground-truth evaluation, missing-key and service-failure fallback, and audit persistence.

Final verification also compiles Python sources, regenerates CSVs, measures results, starts Streamlit headlessly for an HTTP smoke check, and scans repository candidates for likely secrets.

