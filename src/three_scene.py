"""Local Streamlit wrapper for the Three.js revenue-recovery scene."""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components


_FRONTEND = Path(__file__).with_name("reconciliation_scene_frontend")
_SCENE = components.declare_component("reconcile_three_scene", path=str(_FRONTEND))


def recovery_pipeline_scene(counts: dict[str, int], theme: dict[str, str], flow_active: bool = False) -> None:
    """Render a batch-specific reconciliation flow with an explicit replay state."""
    payload = {
        "counts": {name: max(0, int(value)) for name, value in counts.items()},
        "theme": theme,
        "flowActive": bool(flow_active),
    }
    _SCENE(scene=payload, key="recovery-pipeline-scene", default=None)


def reconciliation_scene(counts: dict[str, int], theme: dict[str, str], flow_active: bool = False) -> None:
    """Backward-compatible entry point retained for existing UI helpers."""
    recovery_pipeline_scene(counts, theme, flow_active)
