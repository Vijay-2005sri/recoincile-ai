from src.data_generator import generate_data
from src.database import AuditStore
from src.matcher import reconcile


def test_audit_entry_per_record(tmp_path):
    orders, payments, settlements, _ = generate_data(10)
    results = reconcile(orders, payments, settlements)
    store = AuditStore(str(tmp_path / "audit.sqlite3")); store.save_results(results, "batch-test")
    assert len(store.read_all()) == 10
    assert len(store.read_batch("batch-test")) == 10


def test_ai_status_and_sanitized_event_are_recorded(tmp_path):
    orders, payments, settlements, _ = generate_data(10)
    results = reconcile(orders, payments, settlements)
    store = AuditStore(str(tmp_path / "audit.sqlite3")); store.save_results(results, "batch-ai")
    order_id = results.iloc[0].order_id
    store.record_ai_status("batch-ai", order_id, "deterministic_fallback", "service_unavailable")
    audit = store.read_batch("batch-ai").set_index("order_id")
    events = store.read_ai_events("batch-ai")
    assert audit.loc[order_id].ai_explanation_status == "deterministic_fallback"
    assert events.iloc[0].error_code == "service_unavailable"
