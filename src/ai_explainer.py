import json
import os
from .exception_classifier import Classification
from .config import SETTINGS


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "explanation": {"type": "string"},
        "financial_impact": {"type": "string"},
        "recommended_action": {"type": "string"},
    },
    "required": ["explanation", "financial_impact", "recommended_action"],
    "additionalProperties": False,
}
UNSAFE_ACTION_PHRASES = ("refund issued", "refund completed", "payment sent", "funds transferred", "marked resolved")


def fallback_explanation(result: dict, error_code: str = "missing_key") -> dict:
    amount = result.get("order_amount")
    impact = "The affected amount is unavailable."
    if isinstance(amount, (int, float)): impact = f"This record involves ₹{amount:,.2f}. Verify the source evidence before taking action."
    return {"explanation": result["reason"], "financial_impact": impact,
            "recommended_action": result["recommended_action"], "status": "deterministic_fallback",
            "ai_available": False, "error_code": error_code, "classification": result["primary_classification"]}


def _validate_response(parsed: object) -> dict:
    if not isinstance(parsed, dict): raise ValueError("response_not_object")
    required = ("explanation", "financial_impact", "recommended_action")
    if set(parsed) != set(required) or any(not isinstance(parsed[key], str) or not parsed[key].strip() for key in required):
        raise ValueError("invalid_response_schema")
    if any(phrase in parsed["recommended_action"].lower() for phrase in UNSAFE_ACTION_PHRASES):
        raise ValueError("unsafe_recommendation")
    return {key: parsed[key].strip()[:1500] for key in required}


def explain(result: dict, client=None) -> dict:
    key = os.getenv("GEMINI_API_KEY")
    if client is None and (not key or key == "replace_with_your_own_key"): return fallback_explanation(result, "missing_key")
    try:
        from google import genai
        from google.genai import types
        client = client or genai.Client(api_key=key, http_options=types.HttpOptions(timeout=SETTINGS.ai_timeout_ms))
        allowed = {c.value for c in Classification}
        if result.get("primary_classification") not in allowed: return fallback_explanation(result, "invalid_classification")
        prompt = ("Use only this structured reconciliation result. Explain the exception, state its supplied financial impact, "
                  "and recommend a safe human verification step. Never alter the classification, invent facts, move money, "
                  "or claim an action was completed. Context: " + json.dumps(result, default=str))
        config = types.GenerateContentConfig(response_mime_type="application/json", response_json_schema=RESPONSE_SCHEMA,
                                             temperature=0.1, max_output_tokens=500)
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config=config)
        parsed = _validate_response(json.loads(response.text))
        return {**parsed, "status": "ai_generated", "ai_available": True, "error_code": None,
                "classification": result["primary_classification"]}
    except json.JSONDecodeError:
        return fallback_explanation(result, "invalid_json")
    except (TimeoutError, ConnectionError):
        return fallback_explanation(result, "service_unavailable")
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc) in {"response_not_object", "invalid_response_schema", "unsafe_recommendation"} else "service_unavailable"
        return fallback_explanation(result, code)
