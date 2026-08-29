import json
import os
from .exception_classifier import Classification


def fallback_explanation(result: dict) -> dict:
    return {"explanation": result["reason"], "recommended_action": result["recommended_action"],
            "status": "deterministic_fallback", "classification": result["primary_classification"]}


def explain(result: dict) -> dict:
    key = os.getenv("GEMINI_API_KEY")
    if not key or key == "replace_with_your_own_key": return fallback_explanation(result)
    try:
        from google import genai
        client = genai.Client(api_key=key)
        allowed = {c.value for c in Classification}
        prompt = ("Explain this deterministic reconciliation result briefly. Do not alter its classification, invent facts, "
                  "or suggest executing money movement. Return JSON with explanation and recommended_action. Context: " + json.dumps(result, default=str))
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        parsed = json.loads(response.text)
        if result["primary_classification"] not in allowed or not all(k in parsed for k in ("explanation", "recommended_action")): raise ValueError("Invalid AI response")
        return {**parsed, "status": "ai_generated", "classification": result["primary_classification"]}
    except Exception:
        return fallback_explanation(result)

