from src.data_generator import generate_data
from src.database import AuditStore
from src.matcher import reconcile


def test_audit_entry_per_record(tmp_path):
    orders, payments, settlements, _ = generate_data(10)
    results = reconcile(orders, payments, settlements)
    store = AuditStore(str(tmp_path / "audit.sqlite3")); store.save_results(results, "batch-test")
    assert len(store.read_all()) == 10

