import json

import pandas as pd

from src.input_data_reviewer import review_input_data


class FakeMistral:
    call = None

    def __init__(self, api_key): self.api_key = api_key; self.chat = self

    def complete(self, **kwargs):
        type(self).call = kwargs
        content = json.dumps({"summary": "Input profile looks structurally complete.", "findings": ["No missing values detected."]})
        return type("Response", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]})()


def test_missing_key_skips_advisory_review(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    assert review_input_data({"orders": pd.DataFrame({"order_id": ["O-1"]})})["status"] == "not_configured"


def test_mistral_small_reviews_only_profile(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr("mistralai.Mistral", FakeMistral)
    review = review_input_data({"orders": pd.DataFrame({"order_id": ["O-1"], "order_amount": [100.0]})})
    assert review["status"] == "completed"
    assert FakeMistral.call["model"] == "mistral-small-latest"
    prompt = FakeMistral.call["messages"][0]["content"]
    assert "O-1" not in prompt and "100.0" not in prompt
