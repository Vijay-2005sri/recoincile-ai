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
from src.ui import decision_card, inject_theme, render_hero, render_workflow, section_header, style_chart
from src.validator import validate_batch


load_dotenv(); st.set_page_config(page_title="ReconcileAI", page_icon="₹", layout="wide", initial_sidebar_state="expanded")
inject_theme(); render_hero(); render_workflow()


def load_csv(upload, fallback):
    return pd.read_csv(upload) if upload is not None else pd.read_csv(fallback)


with st.sidebar:
    st.markdown("## ReconcileAI Console")
    st.caption("CONTROL LAYER · SYNTHETIC DEMO")
    st.markdown("---")
    st.header("Data source")
    st.session_state.setdefault("data_mode", "demo")
    if st.button("Load bundled demo data", width="stretch"): st.session_state.data_mode = "demo"
    if st.button("Use uploaded files", width="stretch"): st.session_state.data_mode = "upload"
    st.caption(f"Selected source: **{st.session_state.data_mode}**")
    uploads = {name: st.file_uploader(f"{name.title()} CSV", type="csv", key=name) for name in ("orders", "payments", "settlements", "ground_truth")}
    st.caption("Ground truth is optional for uploaded data.")
    tolerance = st.number_input("Amount tolerance (₹)", min_value=0.0, value=SETTINGS.amount_tolerance, step=.1)
    run = st.button("Validate and reconcile", type="primary", width="stretch")

if run:
    for key in ("results", "metrics", "frames", "batch", "explanations"):
        st.session_state.pop(key, None)
    progress = st.progress(0, text="Loading CSV files…")
    try:
        use_demo = st.session_state.data_mode == "demo"
        frames = {name: load_csv(None, f"data/{name}.csv") if use_demo else (pd.read_csv(uploads[name]) if uploads[name] else None) for name in uploads}
        if any(frames[n] is None for n in ("orders", "payments", "settlements")): raise ValueError("Provide all three transaction CSV files.")
        progress.progress(25, text="Validating schemas, rows, references, and dates…")
        validation = validate_batch(frames["orders"], frames["payments"], frames["settlements"])
        st.session_state.validation = validation
        if validation.fatal_errors: raise ValueError(" | ".join(validation.fatal_errors))
        progress.progress(55, text="Applying deterministic reconciliation rules…")
        started = time.perf_counter(); results = reconcile(frames["orders"], frames["payments"], frames["settlements"], tolerance)
        duration = time.perf_counter() - started
        progress.progress(80, text="Calculating metrics and writing the audit trail…")
        metrics = calculate_metrics(results, frames["ground_truth"], duration) if frames["ground_truth"] is not None else calculate_metrics(results, duration=duration)
        store = AuditStore(); batch = str(uuid.uuid4()); store.save_results(results, batch)
        st.session_state.update(results=results, metrics=metrics, frames=frames, batch=batch, explanations={})
        progress.progress(100, text="Reconciliation complete.")
        st.success(f"Processed {len(results)} records without changing any source data.")
    except Exception as exc:
        progress.empty()
        st.error(f"Reconciliation could not be completed: {exc}")

if "validation" in st.session_state and "results" not in st.session_state:
    for name, report in st.session_state.validation.datasets.items():
        with st.expander(f"{name.title()} validation", expanded=True):
            st.write({"fatal_errors": report.fatal_errors, "row_errors": report.row_errors, "warnings": report.warnings})

if "results" not in st.session_state:
    st.info("Load the bundled demonstration data or upload CSV files, then select Validate and reconcile.")
    st.stop()

results, metrics = st.session_state.results, st.session_state.metrics
tabs = st.tabs(["◆ Overview", "▦ Results", "✦ Exception Assistant", "◈ Analytics", "⌁ Audit & Export"])
with tabs[0]:
    section_header("Batch intelligence", "A complete financial control surface", "Every metric below is calculated from the current reconciliation output. AI is limited to explanations and safe recommendations.")
    cols = st.columns(4)
    cols[0].metric("Records processed", metrics["total_records"]); cols[1].metric("Matched", metrics["matched_records"])
    cols[2].metric("Exceptions", metrics["exception_records"]); cols[3].metric("Match rate", f'{metrics["match_rate"]:.1%}')
    cols = st.columns(4)
    cols[0].metric("Measured accuracy", "Unavailable" if metrics["classification_accuracy"] is None else f'{metrics["classification_accuracy"]:.1%}')
    cols[1].metric("Amount reviewed", f'₹{metrics["total_amount_reviewed"]:,.2f}')
    cols[2].metric("Affected amount", f'₹{metrics["affected_amount"]:,.2f}'); cols[3].metric("Duration", f'{metrics["processing_duration"]:.3f}s')
    st.caption(metrics["evaluation_message"])
    for name, report in st.session_state.validation.datasets.items():
        with st.expander(f"{name.title()} validation"): st.write({"fatal_errors": report.fatal_errors, "row_errors": report.row_errors, "warnings": report.warnings})
    if st.session_state.validation.warnings: st.warning(" · ".join(st.session_state.validation.warnings))
with tabs[1]:
    section_header("Reconciliation ledger", "Search every deterministic decision", "Filter classifications or search across identifiers, checks, and human-readable reasons.")
    category = st.multiselect("Classification", sorted(results.primary_classification.unique()))
    query = st.text_input("Search identifiers or reasons")
    shown = results[results.primary_classification.isin(category)] if category else results
    if query: shown = shown[shown.astype(str).apply(lambda row: row.str.contains(query, case=False).any(), axis=1)]
    st.dataframe(
        shown,
        width="stretch",
        height=540,
        hide_index=True,
        column_config={
            "order_amount": st.column_config.NumberColumn("Order amount", format="₹ %.2f"),
            "paid_amount": st.column_config.NumberColumn("Paid amount", format="₹ %.2f"),
            "expected_settlement": st.column_config.NumberColumn("Expected settlement", format="₹ %.2f"),
            "actual_settlement": st.column_config.NumberColumn("Actual settlement", format="₹ %.2f"),
            "confidence": st.column_config.ProgressColumn("Rule confidence", min_value=0, max_value=1, format="percent"),
        },
    )
with tabs[2]:
    section_header("Exception intelligence", "Understand the evidence before acting", "Inspect original rows, deterministic checks, financial impact, and a bounded explanation. Cases always remain human-controlled.")
    exceptions = results[results.primary_classification != "MATCHED"]
    if exceptions.empty: st.success("No exceptions require review.")
    else:
        oid = st.selectbox("Select an exception", exceptions.order_id)
        selected = exceptions[exceptions.order_id == oid].iloc[0].to_dict()
        decision_card(selected)
        with st.expander("View complete deterministic evidence"): st.json(selected)
        status = "Open — human review required" if selected["primary_classification"] != "MATCHED" else "No review required"
        st.warning(f"Manual-review status: {status}")
        frames = st.session_state.frames
        section_header("Source evidence", "Original transaction records", "These source rows are displayed exactly as supplied and are never modified by the assistant.")
        st.write("Order"); st.dataframe(frames["orders"][frames["orders"].order_id.astype(str) == str(oid)], hide_index=True, width="stretch")
        source_payments = frames["payments"][frames["payments"].order_id.astype(str) == str(oid)]
        st.write("Payments"); st.dataframe(source_payments, hide_index=True, width="stretch")
        source_settlements = frames["settlements"][frames["settlements"].payment_id.astype(str).isin(source_payments.payment_id.astype(str))]
        st.write("Settlements"); st.dataframe(source_settlements, hide_index=True, width="stretch")
        if st.button("Generate safe explanation"):
            outcome = explain(selected)
            AuditStore().record_ai_status(st.session_state.batch, str(oid), outcome["status"], outcome["error_code"])
            st.session_state.explanations[str(oid)] = outcome
        outcome = st.session_state.explanations.get(str(oid))
        if outcome:
            st.subheader("Explanation assistant")
            st.write(outcome["explanation"]); st.write(f'**Financial impact:** {outcome["financial_impact"]}')
            st.write(f'**Safe next action:** {outcome["recommended_action"]}')
            if not outcome["ai_available"]: st.info("Gemini assistance is unavailable; this is the deterministic fallback explanation.")
        st.warning("Recommendations are advisory. ReconcileAI never moves money or marks a case resolved.")
with tabs[3]:
    section_header("Control analytics", "See where reconciliation risk concentrates", "These charts focus on exception volume, affected value, payment mix, and settlement timing—not decorative metrics.")
    counts = results.primary_classification.value_counts().rename_axis("classification").reset_index(name="count")
    match_summary = results.assign(outcome=results.primary_classification.eq("MATCHED").map({True: "Matched", False: "Exception"})).outcome.value_counts().rename_axis("outcome").reset_index(name="count")
    chart_left, chart_right = st.columns(2)
    with chart_left: st.plotly_chart(style_chart(px.bar(counts, x="classification", y="count", color="classification", title="Records by classification")), width="stretch")
    with chart_right: st.plotly_chart(style_chart(px.pie(match_summary, names="outcome", values="count", hole=.58, title="Matched versus exceptions")), width="stretch")
    affected = results[results.primary_classification != "MATCHED"].groupby("primary_classification", as_index=False).order_amount.sum()
    payment_methods = st.session_state.frames["payments"].payment_method.value_counts().rename_axis("payment_method").reset_index(name="count")
    chart_left, chart_right = st.columns(2)
    with chart_left: st.plotly_chart(style_chart(px.bar(affected, x="primary_classification", y="order_amount", color="primary_classification", title="Financial amount affected by category", labels={"order_amount": "Amount (₹)"})), width="stretch")
    with chart_right: st.plotly_chart(style_chart(px.bar(payment_methods, x="payment_method", y="count", color="payment_method", title="Payment-method distribution")), width="stretch")
    delay_data = st.session_state.frames["payments"].merge(st.session_state.frames["settlements"], on="payment_id", how="inner")
    delay_data["settlement_delay_days"] = (pd.to_datetime(delay_data.settlement_date, errors="coerce") - pd.to_datetime(delay_data.payment_date, errors="coerce")).dt.total_seconds() / 86400
    delay_data = delay_data[delay_data.settlement_delay_days.notna() & delay_data.settlement_delay_days.ge(0)]
    st.plotly_chart(style_chart(px.histogram(delay_data, x="settlement_delay_days", color_discrete_sequence=["#6ee7f9"], title="Settlement-delay distribution", labels={"settlement_delay_days": "Delay (days)"})), width="stretch")
with tabs[4]:
    section_header("Audit fabric", "Trace and export every decision", "The current batch is isolated by batch ID. AI events contain sanitized status codes and never store credentials or raw exceptions.")
    store = AuditStore(); audit = store.read_batch(st.session_state.batch); st.dataframe(audit, width="stretch", hide_index=True)
    with st.expander("AI assistance events"): st.dataframe(store.read_ai_events(st.session_state.batch), width="stretch", hide_index=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("Results CSV", csv_bytes(results), "results.csv", "text/csv")
    c2.download_button("Exceptions CSV", csv_bytes(results[results.primary_classification != "MATCHED"]), "exceptions.csv", "text/csv")
    c3.download_button("Audit CSV", csv_bytes(audit), "audit_log.csv", "text/csv")
    c4.download_button("Summary JSON", summary_bytes(metrics), "summary.json", "application/json")
