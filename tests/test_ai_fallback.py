from src.ai_explainer import explain
import json


RESULT = {"primary_classification": "PAYMENT_MISSING", "reason": "No payment references this order.",
          "recommended_action": "Check the gateway for an attempted payment.", "order_amount": 1499.0}


class FakeResponse:
    def __init__(self, text): self.text = text


class FakeModels:
    def __init__(self, response=None, error=None): self.response, self.error = response, error
    def generate_content(self, **_kwargs):
        if self.error: raise self.error
        return FakeResponse(self.response)


class FakeClient:
    def __init__(self, response=None, error=None): self.models = FakeModels(response, error)


def test_missing_key_uses_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert explain(RESULT)["status"] == "deterministic_fallback"


def test_service_failure_uses_fallback(monkeypatch):
    outcome = explain(RESULT, client=FakeClient(error=ConnectionError("offline")))
    assert outcome["status"] == "deterministic_fallback"
    assert outcome["error_code"] == "service_unavailable"


def test_valid_structured_ai_response():
    response = json.dumps({"explanation": "No payment was found.", "financial_impact": "₹1,499 requires review.",
                           "recommended_action": "Verify the gateway records."})
    outcome = explain(RESULT, client=FakeClient(response=response))
    assert outcome["status"] == "ai_generated" and outcome["ai_available"] is True


def test_invalid_json_and_unsafe_action_fall_back():
    assert explain(RESULT, client=FakeClient(response="not-json"))["error_code"] == "invalid_json"
    unsafe = json.dumps({"explanation": "Done", "financial_impact": "Affected", "recommended_action": "Refund issued"})
    assert explain(RESULT, client=FakeClient(response=unsafe))["error_code"] == "unsafe_recommendation"
