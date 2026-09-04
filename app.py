"""ReconcileAI Streamlit command centre."""

from datetime import datetime, timezone
import io
import os
import time
import uuid

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from src.ai_explainer import explain
from src.config import SETTINGS
from src.currency import format_breakdown, format_money
from src.database import AuditStore
from src.matcher import reconcile
from src.metrics import calculate_metrics
from src.report_generator import csv_bytes, summary_bytes
from src.input_data_reviewer import review_input_data
from src.ui import (
    ai_boundary,
    audit_feed,
    command_bar,
    data_feed_status,
    decision_card,
    exception_radar,
    inject_theme,
    metric_grid,
    page_heading,
    rail_brand,
    reconciliation_core,
    severity_for,
    source_card_header,
    sticky_summary,
    style_chart,
    transaction_lineage,
    validation_sequence,
)
from src.validator import validate_batch


load_dotenv()
st.set_page_config(page_title="ReconcileAI Command Centre", page_icon="R", layout="wide", initial_sidebar_state="expanded")


@st.cache_data(show_spinner=False)
def load_demo_data() -> dict[str, pd.DataFrame]:
    return {name: pd.read_csv(f"data/{name}.csv") for name in ("orders", "payments", "settlements", "ground_truth")}


def read_upload(upload) -> pd.DataFrame | None:
    return pd.read_csv(io.BytesIO(upload.getvalue())) if upload is not None else None


def clear_batch() -> None:
    for key in ("results", "metrics", "frames", "batch", "explanations", "last_processed", "validation", "input_review", "flow_active"):
        st.session_state.pop(key, None)


def source_frames() -> dict[str, pd.DataFrame | None]:
    if st.session_state.data_mode == "demo":
        return {name: frame.copy() for name, frame in load_demo_data().items()}
    return {
        "orders": read_upload(st.session_state.get("orders_upload")),
        "payments": read_upload(st.session_state.get("payments_upload")),
        "settlements": read_upload(st.session_state.get("settlements_upload")),
        "ground_truth": read_upload(st.session_state.get("ground_truth_upload")),
    }


def validation_statuses(validation) -> list[tuple[str, str, str]]:
    if validation is None:
        return [("Schema check", "Pending", "not run"), ("Data types", "Pending", "not run"),
                ("Identifiers", "Pending", "not run"), ("Financial rules", "Pending", "not run"),
                ("Readiness", "Pending", "not run")]
    row_messages = [message for report in validation.datasets.values() for messages in report.row_errors.values() for message in messages]
    schema_errors = len(validation.fatal_errors)
    type_issues = sum(any(token in message.lower() for token in ("numeric", "date", "status", "currency")) for message in row_messages)
    identifier_issues = sum(any(token in message.lower() for token in ("missing", "duplicate", "identifier", "reference")) for message in row_messages)
    identifier_issues += len(validation.warnings)
    financial_issues = sum(any(token in message.lower() for token in ("invalid value", "precedes")) for message in row_messages)

    def outcome(count: int, fatal: bool = False) -> tuple[str, str]:
        if fatal: return "Failed", f"{count} blocking issue(s)"
        return ("Warning", f"{count} row issue(s)") if count else ("Passed", "checks complete")

    return [
        ("Schema check", *outcome(schema_errors, schema_errors > 0)),
        ("Data types", *outcome(type_issues)),
        ("Identifiers", *outcome(identifier_issues)),
        ("Financial rules", *outcome(financial_issues)),
        ("Readiness", "Failed" if schema_errors else "Warning" if row_messages else "Passed",
         "blocked" if schema_errors else f"{len(row_messages)} row issue(s) retained" if row_messages else "ready to reconcile"),
    ]


def run_reconciliation(frames: dict[str, pd.DataFrame | None], tolerance: float) -> bool:
    if any(frames[name] is None for name in ("orders", "payments", "settlements")):
        st.error("Reconciliation is blocked: provide orders, payments, and settlements before continuing.")
        return False
    counts = {"orders": len(frames["orders"]), "payments": 0, "settlements": 0, "verified": 0, "exceptions": 0}
    st.session_state.flow_active = True
    core_placeholder = st.empty()
    with core_placeholder.container(): reconciliation_core(counts, flow_active=True)
    progress = st.progress(8, text="Reading source manifests…")
    try:
        progress.progress(25, text="Running schema, identifier, and financial validation…")
        validation = validate_batch(frames["orders"], frames["payments"], frames["settlements"])
        st.session_state.validation = validation
        if validation.fatal_errors:
            core_placeholder.empty(); progress.empty()
            st.error("Reconciliation blocked by fatal validation errors: " + " | ".join(validation.fatal_errors))
            return False
        progress.progress(42, text="Running Mistral input-data quality review…")
        st.session_state.input_review = review_input_data({name: frames[name] for name in ("orders", "payments", "settlements")})
        progress.progress(55, text="Matching orders, payments, and settlements…")
        started = time.perf_counter()
        results = reconcile(frames["orders"], frames["payments"], frames["settlements"], tolerance)
        duration = time.perf_counter() - started
        progress.progress(78, text="Calculating ground-truth metrics and exception exposure…")
        metrics = calculate_metrics(results, frames.get("ground_truth"), duration)
        progress.progress(91, text="Writing immutable batch audit events…")
        batch_id = str(uuid.uuid4())
        AuditStore().save_results(results, batch_id)
        st.session_state.update(results=results, metrics=metrics, frames=frames, batch=batch_id,
                                explanations={}, last_processed=datetime.now(timezone.utc).strftime("%H:%M:%S UTC"))
        progress.progress(100, text="Reconciliation complete")
        core_placeholder.empty(); progress.empty()
        st.success(f"Batch {batch_id[:8]} processed {len(results)} records in {duration:.3f} seconds.")
        return True
    except Exception as exc:
        core_placeholder.empty(); progress.empty()
        st.error(f"Reconciliation could not be completed: {exc}")
        return False


def current_counts(frames, results) -> dict[str, int]:
    orders = len(frames["orders"]) if frames.get("orders") is not None else 0
    if results is None:
        return {"orders": orders, "payments": 0, "settlements": 0, "verified": 0, "exceptions": 0}
    return {
        "orders": orders,
        "payments": int(results.payment_id.notna().sum()),
        "settlements": int(results.settlement_id.notna().sum()),
        "verified": int((results.primary_classification == "MATCHED").sum()),
        "exceptions": int((results.primary_classification != "MATCHED").sum()),
    }


def selected_result_panel(selected: dict, frames: dict[str, pd.DataFrame]) -> None:
    transaction_lineage(selected)
    decision_card(selected)
    payment_rows = frames["payments"][frames["payments"].order_id.astype(str) == str(selected["order_id"])]
    settlement_rows = frames["settlements"][frames["settlements"].payment_id.astype(str).isin(payment_rows.payment_id.astype(str))]
    inspect_left, inspect_right = st.columns([1.35, .65])
    with inspect_left:
        with st.expander("Source transaction evidence", expanded=True):
            st.caption("ORDER"); st.dataframe(frames["orders"][frames["orders"].order_id.astype(str) == str(selected["order_id"])], width="stretch", hide_index=True)
            st.caption("PAYMENT"); st.dataframe(payment_rows, width="stretch", hide_index=True)
            st.caption("SETTLEMENT"); st.dataframe(settlement_rows, width="stretch", hide_index=True)
        with st.expander("Rules and complete deterministic record"):
            st.json(selected)
    with inspect_right:
        expected = selected.get("expected_settlement")
        actual = selected.get("actual_settlement")
        difference = abs(float(expected) - float(actual)) if expected is not None and actual is not None else None
        currency = selected.get("currency", "INR")
        st.metric("Expected settlement", format_money(expected, currency))
        st.metric("Actual settlement", format_money(actual, currency))
        st.metric("Absolute difference", format_money(difference, currency))
        st.info(selected["recommended_action"])


for key, default in (("data_mode", "demo"), ("theme_mode", "Dark"), ("navigation", "◈ Command Centre")):
    st.session_state.setdefault(key, default)

inject_theme(
    motion_enabled=True,
    theme_mode=st.session_state.theme_mode,
)

NAVIGATION = ("◈ Command Centre", "⇩ Data Intake", "⇄ Reconciliation", "⚠ Exceptions", "⌁ Analytics", "≡ Audit Trail", "↗ Export")
with st.sidebar:
    rail_brand()
    navigation = st.radio("Workspace", NAVIGATION, key="navigation", label_visibility="collapsed")
    st.markdown("---")
    theme_icon = "☾" if st.session_state.theme_mode == "Dark" else "☀"
    theme_flash = st.session_state.pop("theme_flash", None)
    with st.container(key="theme_switch_panel"):
        switch_theme = st.button(theme_icon, key="theme_switch")
        if theme_flash:
            st.markdown(f'<span class="theme-mode-flash">{theme_flash}</span>', unsafe_allow_html=True)
    if switch_theme:
        next_theme = "Light" if st.session_state.theme_mode == "Dark" else "Dark"
        st.session_state.theme_mode = next_theme
        st.session_state.theme_flash = f"{next_theme} mode"
        st.rerun()
    st.markdown('<div class="rail-foot"><strong>Synthetic-data demonstration</strong><br>No payments, refunds, or settlements can be initiated from this application.</div>', unsafe_allow_html=True)

results = st.session_state.get("results")
metrics = st.session_state.get("metrics")
active_frames = st.session_state.get("frames") or source_frames()
required_sources = ("orders", "payments", "settlements")
source_ready = all(active_frames.get(name) is not None for name in required_sources)
staged_order_count = len(active_frames["orders"]) if active_frames.get("orders") is not None else 0
missing_sources = [name.title() for name in required_sources if active_frames.get(name) is None]
gemini_key = os.getenv("GEMINI_API_KEY")
ai_available = bool(gemini_key and gemini_key != "replace_with_your_own_key")
system_status = "IDLE" if results is None else "ATTENTION" if (results.primary_classification != "MATCHED").any() else "HEALTHY"
command_bar(st.session_state.get("batch"), "DEMO" if st.session_state.data_mode == "demo" else "UPLOAD",
            system_status, ai_available, st.session_state.get("last_processed", "Not processed"))


if navigation == "◈ Command Centre":
    source_context = ("Batch " + st.session_state.batch[:8]) if results is not None else (
        "Demo data staged" if st.session_state.data_mode == "demo" else
        "Uploads staged" if source_ready else "Uploads required"
    )
    page_heading("Operations overview", "Finance command centre", "Current reconciliation posture, transaction flow, exposure, and real audit activity in one viewport.",
                 source_context)
    feed_panel, feed_action = st.columns([.82, .18], gap="small", vertical_alignment="center")
    with feed_panel:
        data_feed_status(st.session_state.data_mode, active_frames, source_ready, st.session_state.get("last_processed"))
    with feed_action:
        st.button("Open Data Intake", key="command_feed_action", on_click=lambda: st.session_state.update(navigation=NAVIGATION[1]))
    if results is None:
        action_col, note_col = st.columns([.28, .72])
        with action_col:
            if st.button("Validate and Reconcile", type="primary", key="command_run", disabled=not source_ready,
                         help="Stage all three required sources in Data Intake first." if not source_ready else None):
                if run_reconciliation(active_frames, SETTINGS.amount_tolerance): st.rerun()
        with note_col:
            if source_ready:
                source_label = "synthetic" if st.session_state.data_mode == "demo" else "uploaded"
                st.caption(f"{staged_order_count:,} {source_label} orders are staged. Run the deterministic pipeline to populate operational metrics.")
            else:
                st.warning("Reconciliation is waiting for: " + ", ".join(missing_sources) + ". Open Data Intake to stage the required CSV files.")
    displayed_metrics = [
        {"label": "Records processed", "value": f'{metrics["total_records"]:,}' if metrics else "—", "note": f'{staged_order_count:,} records staged' if source_ready else "Required sources not staged", "icon": "▤", "tone": "info"},
        {"label": "Match rate", "value": f'{metrics["match_rate"]:.1%}' if metrics else "—", "note": "Clean end-to-end chains", "icon": "✓", "tone": "success"},
        {"label": "Exceptions detected", "value": f'{metrics["exception_records"]:,}' if metrics else "—", "note": "Unresolved human queue", "icon": "!", "tone": "warning"},
        {"label": "Amount at risk", "value": format_breakdown(metrics["affected_amounts_by_currency"], compact=True) if metrics else "—", "note": "Value associated with exceptions", "icon": "¤", "tone": "critical"},
        {"label": "Classification accuracy", "value": "Unavailable" if not metrics or metrics["classification_accuracy"] is None else f'{metrics["classification_accuracy"]:.1%}', "note": "Measured against ground truth", "icon": "◎", "tone": "review"},
    ]
    metric_grid(displayed_metrics)
    reconciliation_core(current_counts(active_frames, results), flow_active=st.session_state.get("flow_active", False))
    operational_left, operational_right = st.columns(2, gap="medium")
    with operational_left:
        exception_radar(results, metrics["affected_amounts_by_currency"] if metrics else {})
    with operational_right:
        audit_feed(results)


elif navigation == "⇩ Data Intake":
    page_heading("Source control", "Data Intake Dock", "Stage the three financial sources, inspect their contracts, validate every row, and release one controlled reconciliation run.", "CSV · UTF-8")
    choice = st.selectbox("Source strategy", ("Use demonstration dataset", "Upload custom dataset"),
                          index=0 if st.session_state.data_mode == "demo" else 1, width=280)
    requested_mode = "demo" if choice == "Use demonstration dataset" else "upload"
    if requested_mode != st.session_state.data_mode:
        st.session_state.data_mode = requested_mode; clear_batch(); st.rerun()

    schemas = {
        "Orders": "6 required columns · order_id → status",
        "Payments": "7 required columns · payment_id → method",
        "Settlements": "8 required columns · fees, tax → status",
    }
    upload_keys = {"Orders": "orders_upload", "Payments": "payments_upload", "Settlements": "settlements_upload"}
    source_names = {"Orders": "orders", "Payments": "payments", "Settlements": "settlements"}
    columns = st.columns(3)
    for column, display_name in zip(columns, ("Orders", "Payments", "Settlements")):
        with column:
            if st.session_state.data_mode == "demo":
                frame = load_demo_data()[source_names[display_name]]
                source_card_header(display_name, schemas[display_name], "READY")
                with st.container(border=True):
                    st.write(f'**{source_names[display_name]}.csv**'); st.caption(f'{len(frame):,} rows · bundled synthetic source')
            else:
                existing = st.session_state.get(upload_keys[display_name])
                row_count = len(read_upload(existing)) if existing is not None else 0
                source_card_header(display_name, schemas[display_name], "STAGED" if existing else "WAITING")
                upload = st.file_uploader(f"Upload {display_name.lower()}", type="csv", key=upload_keys[display_name], label_visibility="collapsed")
                if upload is not None: st.caption(f'{upload.name} · {row_count:,} rows · choose another file to replace')

    with st.expander("Schema contracts and optional ground truth"):
        schema_cols = st.columns(3)
        schema_cols[0].code("order_id\ncustomer_id\norder_amount\ncurrency\norder_date\norder_status")
        schema_cols[1].code("payment_id\norder_id\npaid_amount\ncurrency\npayment_status\npayment_method\npayment_date")
        schema_cols[2].code("settlement_id\npayment_id\nsettled_amount\nfee\ntax\ncurrency\nsettlement_status\nsettlement_date")
        if st.session_state.data_mode == "upload": st.file_uploader("Optional ground-truth CSV", type="csv", key="ground_truth_upload")
        else: st.caption("Bundled ground_truth.csv is staged for post-reconciliation evaluation only.")

    staged_frames = source_frames()
    required_ready = all(staged_frames[name] is not None for name in ("orders", "payments", "settlements"))
    validation_sequence(validation_statuses(st.session_state.get("validation")))
    action_col, state_col = st.columns([.34, .66])
    with action_col:
        reconcile_now = st.button("Validate and Reconcile", type="primary", disabled=not required_ready, key="intake_run")
    with state_col:
        if required_ready: st.caption("All required source manifests are staged. Fatal schema errors will block processing; row issues remain inspectable.")
        else: st.warning("Primary action disabled: upload all three required CSV files.")
    if reconcile_now and run_reconciliation(staged_frames, SETTINGS.amount_tolerance): st.rerun()
    if "validation" in st.session_state:
        for name, report in st.session_state.validation.datasets.items():
            if report.fatal_errors or report.row_errors or report.warnings:
                with st.expander(f"{name.title()} validation evidence"):
                    st.write({"fatal_errors": report.fatal_errors, "row_errors": report.row_errors, "warnings": report.warnings})
        if st.session_state.validation.warnings: st.warning("Cross-file warnings: " + " · ".join(st.session_state.validation.warnings))
    if "input_review" in st.session_state:
        review = st.session_state.input_review
        with st.expander("Mistral input-data review", expanded=review["available"]):
            st.caption("Advisory review of row counts, columns, and missing-value counts only. Deterministic validation remains authoritative.")
            st.write(review["summary"])
            for finding in review["findings"]: st.write("• " + finding)


elif navigation == "⇄ Reconciliation":
    page_heading("Decision ledger", "Reconciliation workspace", "Filter, sort, and inspect deterministic results without losing the batch-level control context.", "Dense review mode")
    if results is None:
        st.info("No reconciliation result exists yet. Open Data Intake or run the staged demonstration batch from Command Centre.")
    else:
        severity_series = results.primary_classification.map(severity_for)
        sticky_summary([("Batch", st.session_state.batch[:8]), ("Records", f"{len(results):,}"), ("Matched", f'{metrics["matched_records"]:,}'),
                        ("Exceptions", f'{metrics["exception_records"]:,}'), ("At risk", format_breakdown(metrics["affected_amounts_by_currency"], compact=True)), ("Accuracy", "Unavailable" if metrics["classification_accuracy"] is None else f'{metrics["classification_accuracy"]:.1%}')])
        filter_cols = st.columns([1.35, 1, 1, .75, .75])
        query = filter_cols[0].text_input("Search IDs or reason", placeholder="Order, payment, settlement…")
        classifications = filter_cols[1].multiselect("Classification", sorted(results.primary_classification.unique()))
        severities = filter_cols[2].multiselect("Severity", ("Matched", "Warning", "Critical", "Manual review"))
        min_amount = float(results.order_amount.min()); max_amount = float(results.order_amount.max())
        amount_min = filter_cols[3].number_input("Min amount", value=min_amount, step=100.0)
        amount_max = filter_cols[4].number_input("Max amount", value=max_amount, step=100.0)
        sort_by = st.selectbox("Sort results", ("Exception priority", "Amount high to low", "Amount low to high", "Classification"), width=260)

        filtered = results.assign(severity=severity_series)
        if query:
            searchable = filtered[["order_id", "payment_id", "settlement_id", "reason"]].fillna("").astype(str)
            filtered = filtered[searchable.apply(lambda row: row.str.contains(query, case=False, regex=False).any(), axis=1)]
        if classifications: filtered = filtered[filtered.primary_classification.isin(classifications)]
        if severities: filtered = filtered[filtered.severity.isin(severities)]
        filtered = filtered[filtered.order_amount.between(amount_min, amount_max)]
        if sort_by == "Amount high to low": filtered = filtered.sort_values("order_amount", ascending=False)
        elif sort_by == "Amount low to high": filtered = filtered.sort_values("order_amount")
        elif sort_by == "Classification": filtered = filtered.sort_values("primary_classification")
        else:
            priority = {"Critical": 0, "Manual review": 1, "Warning": 2, "Matched": 3}
            filtered = filtered.assign(_priority=filtered.severity.map(priority)).sort_values(["_priority", "order_amount"], ascending=[True, False]).drop(columns="_priority")

        display = filtered.copy()
        display.insert(0, "status", display.severity.map({"Matched": "✓ Matched", "Warning": "△ Warning", "Critical": "✕ Failed", "Manual review": "◇ Manual review"}))
        st.caption(f"Showing {len(display):,} of {len(results):,} records")
        st.dataframe(display[["status", "order_id", "payment_id", "settlement_id", "currency", "primary_classification", "order_amount", "expected_settlement", "actual_settlement", "reason", "confidence"]], width="stretch", height=340, hide_index=True,
                     column_config={"currency": st.column_config.TextColumn("Currency"), "order_amount": st.column_config.NumberColumn("Order amount", format="%.2f"), "expected_settlement": st.column_config.NumberColumn("Expected", format="%.2f"), "actual_settlement": st.column_config.NumberColumn("Actual", format="%.2f"), "confidence": st.column_config.ProgressColumn("Rule confidence", min_value=0, max_value=1, format="percent")})
        st.download_button("Export filtered results", csv_bytes(filtered), "filtered_reconciliation.csv", "text/csv")
        if not filtered.empty:
            selected_order = st.selectbox("Inspect transaction", filtered.order_id.tolist(), format_func=lambda value: f"{value} · {filtered.loc[filtered.order_id == value, 'primary_classification'].iloc[0].replace('_', ' ').title()}")
            selected_result_panel(filtered[filtered.order_id == selected_order].iloc[0].to_dict(), st.session_state.frames)


elif navigation == "⚠ Exceptions":
    page_heading("Human-controlled queue", "Exception intelligence", "Deterministic evidence comes first. AI is isolated as a bounded explanation layer and cannot alter financial records.", "AI-assisted · never AI-decided")
    if results is None:
        st.info("No exception queue exists yet. Reconcile a batch to generate controlled exception classifications.")
    else:
        exceptions = results[results.primary_classification != "MATCHED"].copy()
        exceptions["severity"] = exceptions.primary_classification.map(severity_for)
        queue_cols = st.columns([1.2, 1, .8])
        selected_severity = queue_cols[0].multiselect("Queue severity", ("Warning", "Critical", "Manual review"))
        category_filter = queue_cols[1].multiselect("Exception category", sorted(exceptions.primary_classification.unique()))
        queue_cols[2].metric("Open queue", len(exceptions))
        if selected_severity: exceptions = exceptions[exceptions.severity.isin(selected_severity)]
        if category_filter: exceptions = exceptions[exceptions.primary_classification.isin(category_filter)]
        if exceptions.empty:
            st.success("No exceptions match the selected queue filters.")
        else:
            selected_order = st.selectbox("Select exception", exceptions.order_id.tolist(), format_func=lambda value: f"{value} · {exceptions.loc[exceptions.order_id == value, 'primary_classification'].iloc[0].replace('_', ' ').title()}")
            selected = exceptions[exceptions.order_id == selected_order].iloc[0].to_dict()
            selected_result_panel(selected, st.session_state.frames)
            st.markdown("### AI Exception Assistant")
            ai_boundary()
            with st.expander("Evidence supplied to AI"):
                st.json({key: selected.get(key) for key in ("order_id", "payment_id", "settlement_id", "order_amount", "paid_amount", "expected_settlement", "actual_settlement", "primary_classification", "secondary_issues", "reason", "failed_checks", "recommended_action")})
            if st.button("Generate bounded explanation", type="primary"):
                outcome = explain(selected)
                AuditStore().record_ai_status(st.session_state.batch, str(selected_order), outcome["status"], outcome["error_code"])
                st.session_state.explanations[str(selected_order)] = outcome
            outcome = st.session_state.explanations.get(str(selected_order))
            if outcome:
                ai_col, action_col = st.columns([1.35, .65])
                with ai_col:
                    st.markdown("**AI explanation**" if outcome["ai_available"] else "**Deterministic fallback explanation**")
                    st.write(outcome["explanation"]); st.caption(outcome["financial_impact"])
                with action_col:
                    st.markdown("**Safe recommended action**"); st.info(outcome["recommended_action"])
                if not outcome["ai_available"]: st.warning("No AI provider is configured. Reconciliation remains fully operational using deterministic evidence.")


elif navigation == "⌁ Analytics":
    page_heading("Measured intelligence", "Financial control analytics", "Actual output metrics, exception exposure, category quality, payment mix, settlement timing, and processing throughput.", "No fabricated metrics")
    if results is None:
        st.info("Analytics become available after a reconciliation batch is processed.")
    else:
        duration = metrics["processing_duration"] or 0
        throughput = metrics["total_records"] / duration if duration else 0
        metric_grid([
            {"label": "Match rate", "value": f'{metrics["match_rate"]:.1%}', "note": f'{metrics["matched_records"]} verified records', "icon": "✓", "tone": "success"},
            {"label": "Exception rate", "value": f'{metrics["exception_rate"]:.1%}', "note": f'{metrics["unresolved_count"]} unresolved records', "icon": "!", "tone": "warning"},
            {"label": "Affected amount", "value": format_breakdown(metrics["affected_amounts_by_currency"], compact=True), "note": "Value associated with exceptions", "icon": "¤", "tone": "critical"},
            {"label": "Throughput", "value": f'{throughput:,.0f}/s', "note": f'{duration:.3f}s deterministic runtime', "icon": "↯", "tone": "info"},
            {"label": "Accuracy", "value": "Unavailable" if metrics["classification_accuracy"] is None else f'{metrics["classification_accuracy"]:.1%}', "note": metrics["evaluation_message"], "icon": "◎", "tone": "review"},
        ])
        counts = results.primary_classification.value_counts().rename_axis("classification").reset_index(name="count")
        affected = (results[results.primary_classification != "MATCHED"]
                    .groupby(["primary_classification", "currency"], as_index=False)
                    .order_amount.sum())
        methods = st.session_state.frames["payments"].payment_method.value_counts().rename_axis("payment_method").reset_index(name="count")
        delays = st.session_state.frames["payments"].merge(st.session_state.frames["settlements"], on="payment_id", how="inner")
        delays["settlement_delay_days"] = (pd.to_datetime(delays.settlement_date, errors="coerce") - pd.to_datetime(delays.payment_date, errors="coerce")).dt.total_seconds() / 86400
        delays = delays[delays.settlement_delay_days.notna() & delays.settlement_delay_days.ge(0)]
        chart_left, chart_right = st.columns(2)
        with chart_left: st.plotly_chart(style_chart(px.bar(counts, x="classification", y="count", color="classification", title="Exceptions by category")), width="stretch")
        with chart_right: st.plotly_chart(style_chart(px.bar(affected, x="primary_classification", y="order_amount", color="currency", barmode="group", title="Affected amount by category and currency", labels={"order_amount": "Amount (source currency)", "currency": "Currency"})), width="stretch")
        chart_left, chart_right = st.columns(2)
        with chart_left: st.plotly_chart(style_chart(px.bar(methods, x="payment_method", y="count", color="payment_method", title="Payment-method distribution")), width="stretch")
        with chart_right: st.plotly_chart(style_chart(px.histogram(delays, x="settlement_delay_days", title="Settlement-delay distribution", labels={"settlement_delay_days": "Delay (days)"})), width="stretch")
        quality = pd.DataFrame([{"classification": name, **values} for name, values in metrics["per_category"].items()])
        if not quality.empty:
            quality = quality.melt(id_vars="classification", value_vars=("precision", "recall"), var_name="metric", value_name="score")
            st.plotly_chart(style_chart(px.bar(quality, x="classification", y="score", color="metric", barmode="group", title="Precision and recall by category", range_y=(0, 1.05))), width="stretch")


elif navigation == "≡ Audit Trail":
    page_heading("Immutable evidence", "Audit trail", "Every processed order records its identifiers, classification, evaluated rules, reason, AI status, and timestamp.", "SQLite persistence")
    if results is None:
        st.info("The audit trail will appear after the first reconciliation batch.")
    else:
        store = AuditStore(); audit = store.read_batch(st.session_state.batch); ai_events = store.read_ai_events(st.session_state.batch)
        sticky_summary([("Batch", st.session_state.batch), ("Audit entries", str(len(audit))), ("AI events", str(len(ai_events))), ("Storage", "Local SQLite")])
        audit_feed(results, limit=10)
        st.dataframe(audit, width="stretch", height=360, hide_index=True)
        with st.expander("AI assistance event log"): st.dataframe(ai_events, width="stretch", hide_index=True)


else:
    page_heading("Controlled delivery", "Export centre", "Download only computed reconciliation artifacts from the current batch. Source records remain unchanged.", "CSV · JSON")
    if results is None:
        st.info("Process a batch before exporting reconciliation artifacts.")
    else:
        store = AuditStore(); audit = store.read_batch(st.session_state.batch)
        exports = [
            ("Full results", results, "reconciliation_results.csv", "All deterministic classifications and evidence"),
            ("Exception queue", results[results.primary_classification != "MATCHED"], "reconciliation_exceptions.csv", "Only unresolved exception records"),
            ("Audit trail", audit, "reconciliation_audit.csv", "Persistent per-record audit events"),
        ]
        export_cols = st.columns(3)
        for column, (title, frame, filename, description) in zip(export_cols, exports):
            with column:
                with st.container(border=True):
                    st.markdown(f"### {title}"); st.metric("Rows", len(frame)); st.caption(description)
                    st.download_button(f"Download {title}", csv_bytes(frame), filename, "text/csv")
        st.download_button("Download batch summary JSON", summary_bytes(metrics), "reconciliation_summary.json", "application/json", type="primary")
        st.caption(f"Batch {st.session_state.batch} · generated from synthetic demonstration data · no source records modified")
