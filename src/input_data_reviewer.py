"""Mistral-backed advisory review for de-identified input-data profiles."""

from __future__ import annotations

import json
import os

import pandas as pd


MISTRAL_MODEL = "mistral-small-latest"
_PLACEHOLDER = "replace_with_your_own_key"


def _profile(frames: dict[str, pd.DataFrame]) -> dict[str, dict[str, object]]:
    """Return only structural metadata; never send transaction rows or identifiers."""
    profile: dict[str, dict[str, object]] = {}
    for name, frame in frames.items():
        profile[name] = {
            "rows": int(len(frame)),
            "columns": list(frame.columns.astype(str)),
            "missing_values": {column: int(frame[column].isna().sum()) for column in frame.columns},
        }
    return profile


def _fallback(status: str, summary: str) -> dict:
    return {"status": status, "available": False, "summary": summary, "findings": []}


def review_input_data(frames: dict[str, pd.DataFrame]) -> dict:
    """Ask Mistral for advisory data-quality observations without exposing row data."""
    key = os.getenv("MISTRAL_API_KEY")
    if not key or key == _PLACEHOLDER:
        return _fallback("not_configured", "Mistral input review is not configured.")
    prompt = (
        "Return only JSON with a short 'summary' string and a 'findings' array of at most five strings. "
        "Review this de-identified reconciliation input-data profile for likely data-quality risks. "
        "This is advisory only: do not approve, reject, alter, or invent transaction data. Profile: "
        + json.dumps(_profile(frames), default=str)
    )
    try:
        from mistralai import Mistral

        response = Mistral(api_key=key).chat.complete(
            model=MISTRAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=350,
        )
        payload = json.loads(response.choices[0].message.content)
        summary, findings = payload.get("summary"), payload.get("findings")
        if not isinstance(summary, str) or not isinstance(findings, list) or not all(isinstance(item, str) for item in findings):
            raise ValueError("invalid_response")
        return {"status": "completed", "available": True, "summary": summary.strip()[:1000],
                "findings": [item.strip()[:500] for item in findings[:5] if item.strip()]}
    except (json.JSONDecodeError, ValueError):
        return _fallback("invalid_response", "Mistral returned an unusable input review.")
    except Exception:
        return _fallback("service_unavailable", "Mistral input review is unavailable; deterministic validation still ran.")
