from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from src.database import AuditStore


WORKSPACES = (
    ("◈ Command Centre", "Finance command centre"),
    ("⇩ Data Intake", "Data Intake Dock"),
    ("⇄ Reconciliation", "Reconciliation workspace"),
    ("⚠ Exceptions", "Exception intelligence"),
    ("⌁ Analytics", "Financial control analytics"),
    ("≡ Audit Trail", "Audit trail"),
    ("↗ Export", "Export centre"),
)


def _appearance_control(app: AppTest):
    """Return the sidebar appearance control without relying on its position.

    A page such as Data Intake has its own segmented control, so positional
    selection would silently toggle the wrong control.
    """
    return next(control for control in app.button_group if control.label == "Appearance")


def _prepare_button_groups(app: AppTest, appearance: str | None = None) -> None:
    """Prepare every segmented control for a Streamlit 1.54 AppTest rerun.

    AppTest exposes a segmented_control as a ButtonGroup and serializes its
    selection as a list, even when the application control is single-select.
    Data Intake has an additional source-strategy control, so normalizing only
    Appearance still leaves the test client unable to rerun that page. The
    frontend correctly restores each app value as its selected string.
    """
    for control in app.button_group:
        value = control.value
        control.set_value(value if isinstance(value, list) else [] if value is None else [value])
    if appearance is not None:
        _appearance_control(app).set_value([appearance])


def _assert_workspace_is_rendered(app: AppTest, workspace: str, heading: str, theme: str) -> None:
    assert not app.exception
    assert app.session_state["navigation"] == workspace
    assert app.session_state["theme_mode"] == theme
    assert app.radio[0].value == workspace
    rendered_markdown = "\n".join(str(markdown.value) for markdown in app.markdown)
    assert heading in rendered_markdown


@pytest.mark.parametrize(("workspace", "heading"), WORKSPACES)
def test_every_workspace_rerenders_when_the_theme_is_toggled(workspace: str, heading: str):
    """Exercise navigation plus Dark → Light → Dark without reloading the app."""
    app = AppTest.from_file("app.py", default_timeout=30).run()

    # Select the workspace through the real sidebar control. Explicitly
    # serializing Dark also works around the AppTest ButtonGroup mismatch.
    _prepare_button_groups(app, "Dark")
    app.radio[0].set_value(workspace).run()
    _assert_workspace_is_rendered(app, workspace, heading, "Dark")

    _prepare_button_groups(app, "Light")
    app.run()
    _assert_workspace_is_rendered(app, workspace, heading, "Light")

    _prepare_button_groups(app, "Dark")
    app.run()
    _assert_workspace_is_rendered(app, workspace, heading, "Dark")


def test_bundled_demo_reconciles_in_streamlit():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    _prepare_button_groups(app, "Dark")
    run_button = next(button for button in app.button if button.label == "Validate and Reconcile")
    run_button.click().run()

    assert not app.exception
    assert app.session_state["metrics"]["total_records"] == 180

    batch = app.session_state["batch"]
    audit = AuditStore().read_batch(batch)
    assert len(audit) == 180

    _prepare_button_groups(app, "Dark")
    app.radio[0].set_value("≡ Audit Trail").run()
    assert not app.exception
    assert any("Audit trail" in str(markdown.value) for markdown in app.markdown)
    assert app.dataframe[0].value.shape[0] == 180

    _prepare_button_groups(app, "Dark")
    app.radio[0].set_value("⚠ Exceptions").run()
    explanation_button = next(button for button in app.button if button.label == "Generate bounded explanation")
    _prepare_button_groups(app, "Dark")
    explanation_button.click().run()

    assert not app.exception
    assert app.session_state["explanations"]
    assert any("explanation" in str(markdown.value).lower() for markdown in app.markdown)
