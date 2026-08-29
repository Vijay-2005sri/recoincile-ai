from src.ai_explainer import explain


RESULT = {"primary_classification": "PAYMENT_MISSING", "reason": "No payment references this order.",
          "recommended_action": "Check the gateway for an attempted payment."}


def test_missing_key_uses_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert explain(RESULT)["status"] == "deterministic_fallback"


def test_service_failure_uses_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "invalid-test-placeholder")
    assert explain(RESULT)["status"] == "deterministic_fallback"

