"""Regression checks for the semantic theme system."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.three_scene import _FRONTEND
from src.ui import THEME_TOKENS


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


def test_three_scene_contains_true_webgl_flow_primitives():
    html = (_FRONTEND / "index.html").read_text(encoding="utf-8")
    script = (_FRONTEND / "scene.js").read_text(encoding="utf-8")
    for primitive in ("THREE.IcosahedronGeometry", "THREE.TubeGeometry", "THREE.CatmullRomCurve3", "THREE.PerspectiveCamera", "THREE.PointLight", "requestAnimationFrame"):
        assert primitive in script
    assert "Tube width represents volume" in html
    for stage in ("Payment failed", "AI diagnosis", "Risk classification", "Recovery strategy", "Recovery action", "Recovered / escalated / stopped"):
        assert stage in script
    assert (_FRONTEND / "vendor" / "three.module.min.js").is_file()
