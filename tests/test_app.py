"""Smoke tests for the Streamlit application shell without mutating audit storage."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
WORKSPACES = (
    ("Overview", "Recovery operations at a glance"),
    ("Recovery Intelligence", "Evidence-led prioritisation"),
    ("Failed Payments", "Failed and at-risk payment evidence"),
    ("AI Decisions", "Explain a deterministic decision"),
    ("Recovery Campaigns", "Recommended follow-up queue"),
    ("Analytics", "Financial control performance"),
    ("Audit Trail", "Explainable, persistent evidence"),
    ("Guardrails", "Guardrails for a future recovery workflow"),
    ("Settings", "Sources, appearance, and controlled exports"),
)


@pytest.mark.parametrize(("workspace", "heading"), WORKSPACES)
def test_every_workspace_renders_without_an_analysis(workspace: str, heading: str):
    app = AppTest.from_file(APP_PATH, default_timeout=30).run()
    app.radio[0].set_value(workspace).run()

    assert not app.exception
    assert app.session_state["navigation"] == workspace
    rendered_markdown = "\n".join(str(markdown.value) for markdown in app.markdown)
    assert heading in rendered_markdown


def test_overview_exposes_controlled_analysis_action():
    app = AppTest.from_file(APP_PATH, default_timeout=30).run()

    assert not app.exception
    assert any(button.label == "Run Recovery Analysis" for button in app.button)
    assert app.radio[0].value == "Overview"
