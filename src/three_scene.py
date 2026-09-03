"""Local Streamlit wrapper for the Three.js revenue-recovery scene."""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components


_FRONTEND = Path(__file__).with_name("reconciliation_scene_frontend")
_SCENE = components.declare_component("reconcile_three_scene", path=str(_FRONTEND))


def recovery_pipeline_scene(
    counts: dict[str, int], theme: dict[str, str], motion_enabled: bool, processing: bool = False
) -> None:
    """Render the recovery pipeline as genuine WebGL geometry in a local iframe."""
    payload = {
        "counts": {name: max(0, int(value)) for name, value in counts.items()},
        "theme": theme,
        "motionEnabled": bool(motion_enabled),
        "processing": bool(processing),
    }
    _SCENE(scene=payload, key="recovery-pipeline-scene", default=None)


def reconciliation_scene(
    counts: dict[str, int], theme: dict[str, str], motion_enabled: bool, processing: bool = False
) -> None:
    """Backward-compatible entry point retained for existing UI helpers."""
    recovery_pipeline_scene(counts, theme, motion_enabled, processing)
