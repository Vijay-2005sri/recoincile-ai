"""Regression checks for the semantic theme system."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.three_scene import _FRONTEND
from src.ui import THEME_TOKENS, data_feed_status


def _relative_luminance(colour: str) -> float:
    value = colour.lstrip("#")
    channels = [int(value[index : index + 2], 16) / 255 for index in range(0, 6, 2)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(foreground: str, background: str) -> float:
    foreground_luminance = _relative_luminance(foreground)
    background_luminance = _relative_luminance(background)
    return (max(foreground_luminance, background_luminance) + 0.05) / (min(foreground_luminance, background_luminance) + 0.05)


@pytest.mark.parametrize("mode", ("Dark", "Light"))
def test_normal_text_tokens_meet_wcag_aa(mode: str):
    theme = THEME_TOKENS[mode]
    pairs = (
        ("text-primary", "bg-canvas"),
        ("text-primary", "surface-1"),
        ("text-secondary", "surface-1"),
        ("text-muted", "surface-1"),
        ("status-success", "surface-1"),
        ("status-warning", "surface-1"),
        ("status-critical", "surface-1"),
        ("status-review", "surface-1"),
        ("text-on-action", "accent-action"),
        ("scene-label-success", "surface-2"),
        ("scene-label-warning", "surface-2"),
        ("scene-label-critical", "surface-2"),
        ("scene-label-review", "surface-2"),
    )
    for foreground, background in pairs:
        assert _contrast(theme[foreground], theme[background]) >= 4.5, f"{mode}: {foreground} on {background}"


def test_css_rules_use_semantic_colour_variables():
    ui_source = Path("src/ui.py").read_text(encoding="utf-8")
    scene_source = Path("src/reconciliation_scene_frontend/scene.css").read_text(encoding="utf-8")
    css_rules = ui_source.split('css = dedent(', maxsplit=1)[1]
    direct_colour = re.compile(r"(?:color|background|border-color|outline)\s*:\s*(?:#|rgb|hsl|black|white)", re.IGNORECASE)
    assert not direct_colour.search(css_rules)
    assert not direct_colour.search(scene_source)


def test_collapsed_sidebar_releases_main_layout_width():
    ui_source = Path("src/ui.py").read_text(encoding="utf-8")
    assert '[data-testid="stSidebar"][aria-expanded="false"] { flex:0 0 0!important; width:0!important; min-width:0!important; max-width:0!important; }' in ui_source
    assert '[data-testid="stAppViewContainer"]:has([data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stMain"] { width:100%!important; }' in ui_source


def test_command_centre_has_data_feed_status_panel():
    app_source = Path("app.py").read_text(encoding="utf-8")
    ui_source = Path("src/ui.py").read_text(encoding="utf-8")
    assert "data_feed_status(st.session_state.data_mode, active_frames, source_ready" in app_source
    assert 'st.button("Open Data Intake", key="command_feed_action"' in app_source
    assert "def data_feed_status" in ui_source
    assert callable(data_feed_status)


def test_shared_theme_layer_defines_requested_font_roles():
    ui_source = Path("src/ui.py").read_text(encoding="utf-8")
    assert 'family=Inter' in ui_source
    assert 'html,body,[class*="css"],.stApp { font-family:"Palatino Linotype",Palatino,Georgia,serif; }' in ui_source
    assert '[data-testid="stSidebar"],[data-testid="stSidebar"] *, .rail-title,.rail-sub { font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif!important; }' in ui_source
    assert '.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6,.page-title,.page-kicker,.panel-title,.command-bar,.metric-value { font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif!important; }' in ui_source
    assert 'font-family:"Material Symbols Rounded","Material Symbols Outlined",sans-serif!important;' in ui_source
    assert '[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button::after { content:"«";' in ui_source


def test_three_scene_contains_true_webgl_flow_primitives():
    html = (_FRONTEND / "index.html").read_text(encoding="utf-8")
    script = (_FRONTEND / "scene.js").read_text(encoding="utf-8")
    for primitive in ("THREE.IcosahedronGeometry", "THREE.TubeGeometry", "THREE.CatmullRomCurve3", "THREE.PerspectiveCamera", "THREE.PointLight", "requestAnimationFrame"):
        assert primitive in script
    assert "Tube width shows actual record volume" in html
    for stage in ("Input data", "Schema validation", "Deterministic matching", "Matched records", "Exception queue", "Audit trail"):
        assert stage in script
    for interaction in ("pointerdown", "pointermove", "sessionStorage", "dblclick"):
        assert interaction in script
    assert (_FRONTEND / "vendor" / "three.module.min.js").is_file()
