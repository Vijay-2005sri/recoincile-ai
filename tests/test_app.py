"""Smoke tests for the seven current Streamlit workspaces."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
WORKSPACES = ("◈ Command Centre", "⇩ Data Intake", "⇄ Reconciliation", "⚠ Exceptions", "⌁ Analytics", "≡ Audit Trail", "↗ Export")


@pytest.mark.parametrize("workspace", WORKSPACES)
def test_current_workspace_renders_without_exception(workspace: str):
    app = AppTest.from_file(APP_PATH, default_timeout=30).run()
    app.radio[0].set_value(workspace).run()

    assert not app.exception
    assert app.session_state["navigation"] == workspace


def test_command_centre_exposes_intake_and_reconciliation_actions():
    app = AppTest.from_file(APP_PATH, default_timeout=30).run()

    assert not app.exception
    labels = {button.label for button in app.button}
    assert {"Validate and Reconcile", "Open Data Intake"}.issubset(labels)
