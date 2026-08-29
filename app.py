import io
import time
import uuid
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from src.ai_explainer import explain
from src.config import SETTINGS
from src.database import AuditStore
from src.matcher import reconcile
from src.metrics import calculate_metrics
from src.report_generator import csv_bytes, summary_bytes
from src.validator import validate_dataset, validate_relationships


load_dotenv(); st.set_page_config(page_title="ReconcileAI", page_icon="₹", layout="wide")
st.title("ReconcileAI")
st.caption("Intelligent Payment Reconciliation and Exception Assistant · Synthetic-data demonstration")


def load_csv(upload, fallback):
    return pd.read_csv(upload) if upload is not None else pd.read_csv(fallback)


with st.sidebar:
    st.header("Data source")
    use_demo = st.toggle("Use bundled demonstration data", value=True)
    uploads = {name: st.file_uploader(f"{name.title()} CSV", type="csv", key=name) for name in ("orders", "payments", "settlements", "ground_truth")}
    tolerance = st.number_input("Amount tolerance (₹)", min_value=0.0, value=SETTINGS.amount_tolerance, step=.1)
    run = st.button("Validate and reconcile", type="primary", use_container_width=True)

if run:
    try:
        frames = {name: load_csv(uploads[name], f"data/{name}.csv") if use_demo or uploads[name] else None for name in uploads}
        if any(frames[n] is None for n in ("orders", "payments", "settlements")): raise ValueError("Provide all three transaction CSV files.")
        reports = {n: validate_dataset(frames[n], n) for n in ("orders", "payments", "settlements")}
        fatals = [f"{n}: {e}" for n, report in reports.items() for e in report.fatal_errors]
        if fatals: raise ValueError(" | ".join(fatals))
        started = time.perf_counter(); results = reconcile(frames["orders"], frames["payments"], frames["settlements"], tolerance)
        duration = time.perf_counter() - started
        metrics = calculate_metrics(results, frames["ground_truth"], duration) if frames["ground_truth"] is not None else calculate_metrics(results, duration=duration)
        store = AuditStore(); batch = str(uuid.uuid4()); store.save_results(results, batch)
        st.session_state.update(results=results, metrics=metrics, reports=reports, frames=frames, batch=batch)
    except Exception as exc: st.error(str(exc))

if "results" not in st.session_state:
    st.info("Load the bundled demonstration data or upload CSV files, then select Validate and reconcile.")
    st.stop()

results, metrics = st.session_state.results, st.session_state.metrics
tabs = st.tabs(["Overview", "Results", "Exception Assistant", "Analytics", "Audit Log & Export"])
with tabs[0]:
    cols = st.columns(4)
    cols[0].metric("Records processed", metrics["total_records"]); cols[1].metric("Matched", metrics["matched_records"])
    cols[2].metric("Exceptions", metrics["exception_records"]); cols[3].metric("Match rate", f'{metrics["match_rate"]:.1%}')
    cols = st.columns(4)
    cols[0].metric("Measured accuracy", "Unavailable" if metrics["classification_accuracy"] is None else f'{metrics["classification_accuracy"]:.1%}')
    cols[1].metric("Amount reviewed", f'₹{metrics["total_amount_reviewed"]:,.2f}')
    cols[2].metric("Affected amount", f'₹{metrics["affected_amount"]:,.2f}'); cols[3].metric("Duration", f'{metrics["processing_duration"]:.3f}s')
    for name, report in st.session_state.reports.items():
        with st.expander(f"{name.title()} validation"): st.write({"row_errors": report.row_errors, "warnings": report.warnings})
    warnings = validate_relationships(st.session_state.frames["orders"], st.session_state.frames["payments"], st.session_state.frames["settlements"])
    if warnings: st.warning(" · ".join(warnings))
with tabs[1]:
    category = st.multiselect("Classification", sorted(results.primary_classification.unique()))
    query = st.text_input("Search identifiers or reasons")
    shown = results[results.primary_classification.isin(category)] if category else results
    if query: shown = shown[shown.astype(str).apply(lambda row: row.str.contains(query, case=False).any(), axis=1)]
    st.dataframe(shown, use_container_width=True, hide_index=True)
with tabs[2]:
    exceptions = results[results.primary_classification != "MATCHED"]
    if exceptions.empty: st.success("No exceptions require review.")
    else:
        oid = st.selectbox("Select an exception", exceptions.order_id)
        selected = exceptions[exceptions.order_id == oid].iloc[0].to_dict(); st.json(selected)
        if st.button("Generate safe explanation"): st.json(explain(selected))
        st.warning("Recommendations are advisory. ReconcileAI never moves money or marks a case resolved.")
with tabs[3]:
    counts = results.primary_classification.value_counts().rename_axis("classification").reset_index(name="count")
    st.plotly_chart(px.bar(counts, x="classification", y="count", title="Records by classification"), use_container_width=True)
    st.plotly_chart(px.pie(counts, names="classification", values="count", title="Matched versus exceptions"), use_container_width=True)
with tabs[4]:
    audit = AuditStore().read_all(); st.dataframe(audit, use_container_width=True, hide_index=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("Results CSV", csv_bytes(results), "results.csv", "text/csv")
    c2.download_button("Exceptions CSV", csv_bytes(results[results.primary_classification != "MATCHED"]), "exceptions.csv", "text/csv")
    c3.download_button("Audit CSV", csv_bytes(audit), "audit_log.csv", "text/csv")
    c4.download_button("Summary JSON", summary_bytes(metrics), "summary.json", "application/json")

