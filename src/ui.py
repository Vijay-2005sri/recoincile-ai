"""Semantic, theme-aware presentation components for ReconcileAI."""

from __future__ import annotations

from html import escape
from textwrap import dedent

import plotly.graph_objects as go
import streamlit as st
from src.three_scene import reconciliation_scene


# Colour values live in one semantic map. Every CSS rule consumes the matching
# custom property, and programmatic renderers receive this same map.
THEME_TOKENS: dict[str, dict[str, str]] = {
    "Dark": {
        "bg-canvas": "#020617", "bg-sidebar": "#0F172A", "bg-grid": "#1E293B",
        "surface-1": "#0E1223", "surface-2": "#111827", "surface-3": "#1E293B", "surface-inverse": "#020617",
        "border-subtle": "#334155", "border-strong": "#475569",
        "text-primary": "#F8FAFC", "text-secondary": "#CBD5E1", "text-muted": "#94A3B8", "text-inverse": "#020617", "text-on-action": "#020617",
        "accent-info": "#38BDF8", "accent-info-soft": "#0C4A6E", "accent-action": "#22C55E",
        "status-success": "#22C55E", "status-success-soft": "#133B2C", "status-warning": "#F59E0B", "status-warning-soft": "#472C0A",
        "status-critical": "#EF4444", "status-critical-soft": "#4A151A", "status-review": "#A78BFA", "status-review-soft": "#2E2155",
        "focus": "#FFFFFF", "shadow-color": "#01030A",
        "scene-canvas": "#020617", "scene-grid": "#334155", "scene-outline": "#475569", "scene-light-top": "#CFFAFE", "scene-light-bottom": "#0F172A", "scene-particle": "#F8FAFC",
        "scene-node-success": "#22C55E", "scene-node-warning": "#F59E0B", "scene-node-critical": "#EF4444", "scene-node-review": "#A78BFA",
        "scene-label-success": "#4ADE80", "scene-label-warning": "#FCD34D", "scene-label-critical": "#FDA4AF", "scene-label-review": "#C4B5FD",
        "chart-grid": "#334155", "chart-paper": "#0E1223", "chart-hover": "#1E293B",
    },
    "Light": {
        "bg-canvas": "#F7F8FA", "bg-sidebar": "#FFFFFF", "bg-grid": "#D6E2E8",
        "surface-1": "#FFFFFF", "surface-2": "#F2F5F7", "surface-3": "#E7EDF1", "surface-inverse": "#0F1D29",
        "border-subtle": "#D1DCE3", "border-strong": "#8AA8B8",
        "text-primary": "#101828", "text-secondary": "#475467", "text-muted": "#667085", "text-inverse": "#FFFFFF", "text-on-action": "#FFFFFF",
        "accent-info": "#0B6E99", "accent-info-soft": "#E0F2F8", "accent-action": "#0B6E99",
        "status-success": "#087443", "status-success-soft": "#E4F5EF", "status-warning": "#9A5200", "status-warning-soft": "#FFF0D8",
        "status-critical": "#B42318", "status-critical-soft": "#FDE8E7", "status-review": "#5B3FA3", "status-review-soft": "#EEE9FE",
        "focus": "#075E91", "shadow-color": "#95A5B4",
        "scene-canvas": "#10202C", "scene-grid": "#466277", "scene-outline": "#6A8797", "scene-light-top": "#D2F6FF", "scene-light-bottom": "#0D1720", "scene-particle": "#F8FAFC",
        "scene-node-success": "#56E0B7", "scene-node-warning": "#FFD166", "scene-node-critical": "#FF8FA3", "scene-node-review": "#C9B7FF",
        "scene-label-success": "#087443", "scene-label-warning": "#9A5200", "scene-label-critical": "#B42318", "scene-label-review": "#5B3FA3",
        "chart-grid": "#D0D8DF", "chart-paper": "#FFFFFF", "chart-hover": "#F6F9FB",
    },
}

_TONES = {"info", "success", "warning", "critical", "review", "muted"}


def theme_tokens(theme_mode: str | None = None) -> dict[str, str]:
    """Return the current semantic palette for CSS-adjacent renderers."""
    mode = theme_mode or st.session_state.get("theme_mode", "Dark")
    return THEME_TOKENS["Light" if mode == "Light" else "Dark"]


def _tone(value: str | None) -> str:
    return value if value in _TONES else "info"


def inject_theme(motion_enabled: bool = True, theme_mode: str = "Dark") -> None:
    """Install the sole colour system used by the Streamlit presentation layer."""
    declarations = "".join(f"--{name}:{value};" for name, value in theme_tokens(theme_mode).items())
    motion_override = "" if motion_enabled else "*,*::before,*::after{animation:none!important;transition:none!important}"
    css = dedent(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Fira+Sans:wght@400;500;600;700;800&display=swap');
        :root { __TOKENS__ --radius:16px; --tone:var(--accent-info); }
        html,body,[class*="css"] { font-family:"Fira Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
        .stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6,[data-testid="stMarkdownContainer"] { color:var(--text-primary); } [data-testid="stCaptionContainer"] { color:var(--text-muted)!important; }
        .stApp { color:var(--text-primary); background:radial-gradient(circle at 54% 12%,color-mix(in srgb,var(--accent-info-soft) 52%,transparent),transparent 31rem),linear-gradient(145deg,var(--bg-canvas),var(--surface-2)); }
        .stApp::before { content:""; position:fixed; inset:0; pointer-events:none; opacity:.32; background-image:linear-gradient(var(--bg-grid) 1px,transparent 1px),linear-gradient(90deg,var(--bg-grid) 1px,transparent 1px); background-size:48px 48px; mask-image:linear-gradient(to bottom,transparent,var(--surface-inverse) 18%,var(--surface-inverse) 84%,transparent); transform:perspective(900px) rotateX(62deg) scale(1.55) translateY(17%); transform-origin:center bottom; }
        [data-testid="stAppViewContainer"]>.main { position:relative; z-index:1; }.block-container { max-width:1920px; padding:4.15rem clamp(1.65rem,3vw,4rem) 2.25rem; }
        #MainMenu,[data-testid="stToolbar"],[data-testid="stDecoration"],footer { display:none!important; } [data-testid="stHeader"] { height:3.5rem; background:transparent; pointer-events:none; } [data-testid="stSidebarCollapsedControl"] { position:fixed!important; z-index:1000!important; top:.72rem; left:.72rem; display:flex!important; pointer-events:auto!important; } [data-testid="stSidebarCollapsedControl"] button { width:2.35rem!important; height:2.35rem!important; min-height:2.35rem!important; padding:0!important; border:1px solid var(--border-strong)!important; border-radius:.7rem!important; background:var(--surface-1)!important; color:var(--text-primary)!important; box-shadow:0 .5rem 1.3rem color-mix(in srgb,var(--shadow-color) 18%,transparent)!important; } [data-testid="stSidebarCollapsedControl"] button:hover { border-color:var(--accent-info)!important; background:var(--surface-2)!important; }

        [data-testid="stSidebar"],[data-testid="stSidebar"]>div:first-child { width:232px!important; min-width:232px!important; background:var(--bg-sidebar)!important; border-right:1px solid var(--border-subtle); box-shadow:1rem 0 2.8rem color-mix(in srgb,var(--shadow-color) 22%,transparent); }
        [data-testid="stSidebar"]>div:first-child { padding-top:1rem; } [data-testid="stSidebar"],[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,[data-testid="stSidebar"] label,[data-testid="stSidebar"] label *,[data-testid="stSidebar"] svg { color:var(--text-primary)!important; }
        [data-testid="stSidebar"] svg { stroke:currentColor; } [data-testid="stSidebar"] [data-testid="stRadio"] label { padding:.58rem .68rem; margin:.12rem 0; border:1px solid transparent; border-radius:.72rem; color:var(--text-secondary)!important; transition:background .16s ease,border-color .16s ease; } [data-testid="stSidebar"] [data-testid="stRadio"] label * { color:var(--text-secondary)!important; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:var(--surface-2); border-color:var(--border-subtle); } [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background:var(--accent-info-soft); border-color:var(--border-strong); box-shadow:inset .2rem 0 var(--accent-info); } [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked),[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) * { color:var(--text-primary)!important; }
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,[data-testid="stSidebar"] [data-testid="stWidgetLabel"] span { color:var(--text-secondary)!important; }
        [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked)>div:first-child { border-color:var(--accent-info)!important; background:var(--accent-info)!important; } [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked)>div:first-child>div { background:var(--text-on-action)!important; }
        [data-testid="stSidebar"] input[type="checkbox"] { accent-color:var(--accent-info)!important; } [data-testid="stSidebar"] input[type="checkbox"][aria-checked="true"] { background:var(--accent-info)!important; border-color:var(--accent-info)!important; }
        [data-testid="stSidebar"] [data-testid="stBaseButton-segmented_control"],[data-testid="stSidebar"] [data-testid="stBaseButton-segmented_controlActive"] { color:var(--text-secondary)!important; background:var(--surface-2)!important; border-color:var(--border-subtle)!important; } [data-testid="stSidebar"] [data-testid="stBaseButton-segmented_controlActive"] { color:var(--text-primary)!important; background:var(--accent-info-soft)!important; border-color:var(--accent-info)!important; }
        [data-testid="stBaseButton-segmented_control"],[data-testid="stBaseButton-segmented_control"] *,[data-testid="stBaseButton-segmented_controlActive"],[data-testid="stBaseButton-segmented_controlActive"] * { color:var(--text-secondary)!important; background:var(--surface-2)!important; border-color:var(--border-subtle)!important; } [data-testid="stBaseButton-segmented_controlActive"],[data-testid="stBaseButton-segmented_controlActive"] * { color:var(--text-primary)!important; background:var(--accent-info-soft)!important; border-color:var(--accent-info)!important; }
        .rail-brand { display:flex; align-items:center; gap:.7rem; padding:.55rem .2rem 1.05rem; margin-bottom:.8rem; border-bottom:1px solid var(--border-subtle); }.rail-logo { display:grid; place-items:center; width:2.15rem; height:2.15rem; border-radius:.65rem; background:var(--accent-action); color:var(--text-on-action); box-shadow:0 .55rem 1.5rem color-mix(in srgb,var(--accent-action) 30%,transparent); font-weight:820; }.rail-title { color:var(--text-primary); font-weight:760; letter-spacing:-.02em; }.rail-sub { color:var(--text-muted); font-size:.67rem; }.rail-foot { margin-top:1rem; padding:.8rem; border:1px solid var(--border-subtle); border-radius:.75rem; background:var(--surface-2); color:var(--text-secondary); font-size:.72rem; line-height:1.45; }

        .command-bar { position:fixed; z-index:50; top:.65rem; left:249px; right:clamp(1.2rem,3vw,4rem); min-height:3.15rem; display:flex; align-items:center; gap:.75rem; padding:.4rem .9rem; border:1px solid var(--border-subtle); border-radius:.9rem; background:color-mix(in srgb,var(--surface-1) 91%,transparent); color:var(--text-primary); box-shadow:0 .8rem 2.2rem color-mix(in srgb,var(--shadow-color) 18%,transparent); backdrop-filter:blur(18px); }.command-brand { display:flex; align-items:center; gap:.55rem; margin-right:auto; color:var(--text-primary); font-weight:760; white-space:nowrap; }.command-mark { width:.62rem; height:.62rem; border:2px solid var(--accent-info); transform:rotate(45deg); box-shadow:0 0 .8rem var(--accent-info); }.command-item { display:flex; align-items:center; gap:.4rem; padding:.38rem .56rem; border:1px solid var(--border-subtle); border-radius:.55rem; background:var(--surface-2); color:var(--text-secondary); font-size:.72rem; white-space:nowrap; }.command-item strong { color:var(--text-primary); font-weight:700; }.status-dot { width:.48rem; height:.48rem; border-radius:50%; background:var(--status-success); box-shadow:0 0 .65rem var(--status-success); }.status-dot.warn { background:var(--status-warning); box-shadow:0 0 .65rem var(--status-warning); }.status-dot.off { background:var(--text-muted); box-shadow:none; }

        .page-head { display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin:.3rem 0 1.05rem; }.page-kicker { color:var(--accent-info); font-size:.76rem; font-weight:740; letter-spacing:.035em; }.page-title { margin:.18rem 0; color:var(--text-primary); font-size:clamp(1.55rem,2vw,2.05rem); line-height:1.14; letter-spacing:-.032em; font-weight:780; }.page-copy { max-width:52rem; margin:0; color:var(--text-secondary); font-size:.93rem; line-height:1.5; }.context-chip { padding:.42rem .68rem; border:1px solid var(--border-subtle); border-radius:.55rem; background:var(--surface-2); color:var(--text-secondary); font-size:.72rem; }

        .metric-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.85rem; margin-bottom:1rem; }.metric-card { position:relative; overflow:hidden; padding:.85rem 1rem; border:1px solid var(--border-subtle); border-radius:var(--radius); background:var(--surface-1); box-shadow:0 .85rem 2.1rem color-mix(in srgb,var(--shadow-color) 13%,transparent); }.metric-card::after { content:""; position:absolute; right:-2.2rem; bottom:-2.8rem; width:7rem; height:7rem; border-radius:50%; background:var(--tone); opacity:.12; filter:blur(.25rem); }.metric-top { display:flex; align-items:center; justify-content:space-between; gap:.5rem; }.metric-label { color:var(--text-secondary); font-size:.76rem; font-weight:680; }.metric-icon { display:grid; place-items:center; width:1.8rem; height:1.8rem; border:1px solid var(--tone); border-radius:.52rem; background:color-mix(in srgb,var(--tone) 12%,var(--surface-1)); color:var(--tone); font-size:.8rem; }.metric-value { margin:.42rem 0 .18rem; color:var(--text-primary); font-size:1.65rem; line-height:1; font-weight:790; letter-spacing:-.035em; }.metric-note { color:var(--text-muted); font-size:.72rem; line-height:1.35; }
        .tone-info { --tone:var(--accent-info); }.tone-success { --tone:var(--status-success); }.tone-warning { --tone:var(--status-warning); }.tone-critical { --tone:var(--status-critical); }.tone-review { --tone:var(--status-review); }.tone-muted { --tone:var(--text-muted); }

        .panel { position:relative; overflow:hidden; border:1px solid var(--border-subtle); border-radius:var(--radius); background:var(--surface-1); box-shadow:0 .9rem 2.2rem color-mix(in srgb,var(--shadow-color) 13%,transparent); }.panel-pad { padding:1rem; }.panel-head { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:.75rem; }.panel-title { color:var(--text-primary); font-size:.95rem; font-weight:760; }.panel-sub { margin-top:.13rem; color:var(--text-muted); font-size:.7rem; }.panel-badge { padding:.3rem .52rem; border:1px solid var(--accent-info); border-radius:999px; background:var(--accent-info-soft); color:var(--accent-info); font-size:.64rem; font-weight:700; white-space:nowrap; } [data-testid="stCustomComponentV1"] iframe { border:1px solid var(--border-subtle)!important; border-radius:var(--radius)!important; background:var(--scene-canvas)!important; box-shadow:0 .9rem 2.2rem color-mix(in srgb,var(--shadow-color) 16%,transparent); }

        .radar-body { display:grid; grid-template-columns:7.2rem 1fr; gap:.95rem; align-items:center; }.risk-donut { position:relative; width:7rem; height:7rem; border-radius:50%; background:conic-gradient(var(--status-critical) 0 var(--critical-angle),var(--status-warning) var(--critical-angle) var(--warning-angle),var(--status-review) var(--warning-angle) 100%); box-shadow:inset 0 0 1.3rem color-mix(in srgb,var(--shadow-color) 28%,transparent),0 .75rem 1.6rem color-mix(in srgb,var(--shadow-color) 14%,transparent); }.risk-donut::after { content:""; position:absolute; inset:1.05rem; border:1px solid var(--border-subtle); border-radius:50%; background:var(--surface-inverse); }.risk-center { position:absolute; z-index:2; inset:0; display:grid; place-content:center; color:var(--text-inverse); text-align:center; font-size:1.35rem; font-weight:790; }.risk-center small { display:block; color:var(--text-secondary); font-size:.57rem; font-weight:600; }.risk-list { display:grid; gap:.42rem; }.risk-row { display:flex; justify-content:space-between; gap:.5rem; color:var(--text-secondary); font-size:.7rem; }.risk-row strong { color:var(--text-primary); }.risk-key { display:inline-block; width:.5rem; height:.5rem; margin-right:.38rem; border-radius:.16rem; background:var(--tone); }.category-stack { display:grid; gap:.38rem; margin-top:.85rem; }.category-row { display:grid; grid-template-columns:minmax(0,1fr) 3rem; gap:.55rem; align-items:center; color:var(--text-secondary); font-size:.66rem; }.category-row strong { color:var(--text-primary); }.category-bar { height:.34rem; overflow:hidden; border-radius:999px; background:var(--surface-3); }.category-fill { height:100%; border-radius:inherit; background:var(--accent-info); }

        .audit-feed { display:grid; gap:.48rem; max-height:14rem; overflow:auto; padding-right:.15rem; }.audit-event { position:relative; padding:.6rem .65rem .6rem 1.7rem; border:1px solid var(--border-subtle); border-radius:.62rem; background:var(--surface-2); }.audit-event::before { content:""; position:absolute; left:.7rem; top:.82rem; width:.42rem; height:.42rem; border-radius:50%; background:var(--tone); box-shadow:0 0 .65rem var(--tone); }.audit-event-title { color:var(--text-primary); font-size:.7rem; font-weight:700; }.audit-event-meta { margin-top:.13rem; color:var(--text-muted); font-size:.6rem; }

        .intake-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.85rem; margin-bottom:.7rem; }.source-head { display:flex; align-items:center; gap:.65rem; margin-bottom:-.3rem; padding:.75rem .85rem; border:1px solid var(--border-subtle); border-bottom:0; border-radius:.85rem .85rem 0 0; background:var(--surface-2); }.source-icon { display:grid; place-items:center; width:2rem; height:2rem; border:1px solid var(--accent-info); border-radius:.55rem; background:var(--accent-info-soft); color:var(--accent-info); }.source-name { color:var(--text-primary); font-size:.81rem; font-weight:760; }.source-schema { color:var(--text-muted); font-size:.6rem; }.source-state { margin-left:auto; padding:.25rem .42rem; border:1px solid var(--tone); border-radius:999px; background:color-mix(in srgb,var(--tone) 11%,var(--surface-2)); color:var(--tone); font-size:.6rem; font-weight:700; }
        [data-testid="stFileUploaderDropzone"] { min-height:3.5rem!important; padding:.45rem!important; border:1px dashed var(--border-strong)!important; border-radius:0 0 .85rem .85rem!important; background:var(--surface-2)!important; color:var(--text-primary)!important; } [data-testid="stFileUploaderDropzone"] *,[data-testid="stFileUploaderFile"] * { color:var(--text-primary)!important; } [data-testid="stFileUploaderDropzone"] button { width:fit-content!important; color:var(--text-on-action)!important; background:var(--accent-action)!important; border-color:var(--accent-action)!important; }

        .validation-strip { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.5rem; margin:.7rem 0; }.validation-step { position:relative; padding:.58rem .7rem; border:1px solid var(--border-subtle); border-radius:.7rem; background:var(--surface-1); }.validation-index { color:var(--text-muted); font-size:.58rem; }.validation-name { margin:.16rem 0; color:var(--text-primary); font-size:.71rem; font-weight:710; }.validation-status { color:var(--tone); font-size:.62rem; }.validation-step::after { content:""; position:absolute; right:.7rem; bottom:0; left:.7rem; height:.16rem; border-radius:999px 999px 0 0; background:var(--tone); }

        .sticky-summary { position:sticky; z-index:8; top:4.15rem; display:flex; flex-wrap:wrap; gap:.35rem; margin-bottom:.75rem; padding:.6rem; border:1px solid var(--border-subtle); border-radius:.75rem; background:color-mix(in srgb,var(--surface-1) 94%,transparent); box-shadow:0 .55rem 1.3rem color-mix(in srgb,var(--shadow-color) 11%,transparent); backdrop-filter:blur(14px); }.summary-item { padding:.3rem .5rem; border-right:1px solid var(--border-subtle); color:var(--text-secondary); font-size:.69rem; }.summary-item:last-child { border:0; }.summary-item strong { color:var(--text-primary); }

        .lineage { display:grid; grid-template-columns:1fr 4.3rem 1fr 4.3rem 1fr; align-items:center; margin:.75rem 0 1rem; }.lineage-node { min-height:4.8rem; padding:.72rem; border:1px solid var(--border-strong); border-radius:.8rem; background:var(--surface-2); }.lineage-node.broken { border-color:var(--status-critical); background:var(--status-critical-soft); }.lineage-kind { color:var(--text-muted); font-size:.59rem; letter-spacing:.07em; text-transform:uppercase; }.lineage-id { margin-top:.28rem; color:var(--text-primary); font-size:.8rem; font-weight:740; overflow-wrap:anywhere; }.lineage-state { margin-top:.24rem; color:var(--status-success); font-size:.59rem; }.lineage-node.broken .lineage-state { color:var(--status-critical); }.lineage-link { position:relative; height:.16rem; background:var(--accent-info); }.lineage-link::after { content:"›"; position:absolute; right:-.08rem; top:-.8rem; color:var(--accent-info); font-size:1.3rem; }.lineage-link.broken { background:repeating-linear-gradient(90deg,var(--status-critical) 0 .45rem,transparent .45rem .75rem); }.lineage-link.broken::after { color:var(--status-critical); }

        .decision-card { padding:1rem; border:1px solid var(--border-subtle); border-radius:.85rem; background:var(--surface-1); box-shadow:0 .75rem 1.8rem color-mix(in srgb,var(--shadow-color) 12%,transparent); }.decision-top { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; }.decision-id,.field-label { color:var(--text-muted); font-size:.59rem; letter-spacing:.07em; text-transform:uppercase; }.decision-reason { margin-top:.36rem; color:var(--text-primary); font-size:.91rem; line-height:1.5; }.decision-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.52rem; margin-top:.8rem; }.decision-field { padding:.6rem; border:1px solid var(--border-subtle); border-radius:.62rem; background:var(--surface-2); }.field-value { margin-top:.22rem; color:var(--text-primary); font-size:.74rem; font-weight:700; }.status-pill { display:inline-flex; align-items:center; gap:.3rem; padding:.32rem .52rem; border:1px solid var(--tone); border-radius:999px; background:color-mix(in srgb,var(--tone) 11%,var(--surface-1)); color:var(--tone); font-size:.63rem; font-weight:740; white-space:nowrap; }.status-matched { --tone:var(--status-success); }.status-review { --tone:var(--status-review); }.status-exception { --tone:var(--status-critical); }.ai-boundary { padding:.78rem; border-left:.2rem solid var(--status-review); border-radius:0 .7rem .7rem 0; background:var(--status-review-soft); color:var(--text-secondary); font-size:.73rem; line-height:1.52; }.ai-boundary strong { color:var(--text-primary); }

        .stButton,.stDownloadButton { width:fit-content; }.stButton>button,.stDownloadButton>button { width:fit-content!important; min-width:0!important; padding-inline:.85rem!important; border:1px solid var(--border-subtle); border-radius:.62rem; background:var(--surface-2); color:var(--text-primary); box-shadow:0 .42rem 1.1rem color-mix(in srgb,var(--shadow-color) 12%,transparent); }.stButton>button:hover,.stDownloadButton>button:hover { border-color:var(--focus); background:var(--surface-3); color:var(--text-primary); }.stButton>button[kind="primary"] { border-color:var(--accent-action); background:var(--accent-action); color:var(--text-on-action); }.stButton>button[kind="primary"] * { color:var(--text-on-action); }.stButton>button:focus-visible,.stDownloadButton>button:focus-visible { outline:.18rem solid var(--focus); outline-offset:.16rem; }
        [data-baseweb="select"]>div,[data-baseweb="input"] { border-color:var(--border-subtle)!important; background:var(--surface-1)!important; color:var(--text-primary)!important; }.stTextInput input,.stNumberInput input,[data-baseweb="select"] * { color:var(--text-primary)!important; } [data-baseweb="select"] svg { color:var(--text-secondary)!important; } [data-testid="stWidgetLabel"] p,[data-testid="stWidgetLabel"] span,[data-testid="stWidgetLabel"] label { color:var(--text-primary)!important; } hr { border-color:var(--border-subtle)!important; }
        [data-testid="stDataFrame"],[data-testid="stPlotlyChart"] { overflow:hidden; border:1px solid var(--border-subtle); border-radius:.8rem; background:var(--surface-1); box-shadow:0 .75rem 1.8rem color-mix(in srgb,var(--shadow-color) 10%,transparent); }.stDataFrame *,[data-testid="stDataFrame"] *,[data-testid="stExpander"] summary { color:var(--text-primary)!important; } [data-testid="stExpander"] { border:1px solid var(--border-subtle); border-radius:.7rem; background:var(--surface-1); } [data-testid="stAlert"] { border-radius:.7rem; color:var(--text-primary); }

        @media(max-width:1200px) { .metric-grid { grid-template-columns:repeat(3,minmax(0,1fr)); } .command-item:nth-of-type(3),.command-item:nth-of-type(4) { display:none; } }
        @media(max-width:900px) { [data-testid="stSidebar"],[data-testid="stSidebar"]>div:first-child { width:190px!important; min-width:190px!important; } .command-bar { left:205px; right:.9rem; } .metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } .intake-grid { grid-template-columns:1fr; } .validation-strip { grid-template-columns:1fr 1fr; } .lineage { grid-template-columns:1fr; gap:.38rem; } .lineage-link { width:.16rem; height:1.5rem; margin:auto; } .decision-grid { grid-template-columns:1fr 1fr; } }
        @media(max-width:700px) { .command-bar { left:.7rem; right:.7rem; } .command-item { display:none; } .block-container { padding-right:.85rem; padding-left:.85rem; } .metric-grid { grid-template-columns:1fr 1fr; } .page-head { align-items:flex-start; flex-direction:column; } }
        @media(prefers-reduced-motion:reduce) { *,*::before,*::after { animation:none!important; transition:none!important; scroll-behavior:auto!important; } }
        __MOTION_OVERRIDE__
        </style>
        """
    ).replace("__TOKENS__", declarations).replace("__MOTION_OVERRIDE__", motion_override)
    st.markdown(css, unsafe_allow_html=True)


def rail_brand() -> None:
    st.markdown('<div class="rail-brand"><div class="rail-logo">R</div><div><div class="rail-title">ReconcileAI</div><div class="rail-sub">FINANCE CONTROL</div></div></div>', unsafe_allow_html=True)


def command_bar(batch_id: str | None, source: str, system_status: str, ai_available: bool, last_processed: str) -> None:
    batch = escape(batch_id[:8] if batch_id else "No batch")
    status_class = "warn" if system_status in {"ATTENTION", "IDLE"} else ""
    ai_class = "" if ai_available else "off"
    st.markdown(f'<div class="command-bar"><div class="command-brand"><span class="command-mark"></span>ReconcileAI</div><div class="command-item">Batch <strong>{batch}</strong></div><div class="command-item">Source <strong>{escape(source)}</strong></div><div class="command-item"><span class="status-dot {status_class}"></span>System <strong>{escape(system_status)}</strong></div><div class="command-item"><span class="status-dot {ai_class}"></span>AI <strong>{"AVAILABLE" if ai_available else "FALLBACK"}</strong></div><div class="command-item">Last run <strong>{escape(last_processed)}</strong></div></div>', unsafe_allow_html=True)


def page_heading(kicker: str, title: str, copy: str, context: str | None = None) -> None:
    context_html = f'<div class="context-chip">{escape(context)}</div>' if context else ""
    st.markdown(f'<div class="page-head"><div><div class="page-kicker">{escape(kicker)}</div><div class="page-title">{escape(title)}</div><p class="page-copy">{escape(copy)}</p></div>{context_html}</div>', unsafe_allow_html=True)


def metric_grid(metrics: list[dict]) -> None:
    cards = []
    for item in metrics:
        tone = _tone(item.get("tone"))
        cards.append(f'<div class="metric-card tone-{tone}"><div class="metric-top"><span class="metric-label">{escape(str(item["label"]))}</span><span class="metric-icon">{escape(str(item.get("icon", "◆")))}</span></div><div class="metric-value">{escape(str(item["value"]))}</div><div class="metric-note">{escape(str(item["note"]))}</div></div>')
    st.markdown(f'<div class="metric-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def panel_header(title: str, subtitle: str, badge: str | None = None) -> str:
    badge_html = f'<span class="panel-badge">{escape(badge)}</span>' if badge else ""
    return f'<div class="panel-head"><div><div class="panel-title">{escape(title)}</div><div class="panel-sub">{escape(subtitle)}</div></div>{badge_html}</div>'


def reconciliation_core(counts: dict[str, int], processing: bool = False) -> None:
    """Render a true WebGL scene rather than CSS-implied depth."""
    payload = {name: max(0, int(counts.get(name, 0))) for name in ("orders", "payments", "settlements", "verified", "exceptions")}
    reconciliation_scene(payload, theme_tokens(), st.session_state.get("motion_enabled", True), processing)


def severity_for(classification: str) -> str:
    if classification == "MATCHED":
        return "Matched"
    if classification in {"INVALID_RECORD", "PAYMENT_DUPLICATE", "PAYMENT_CURRENCY_MISMATCH", "SETTLEMENT_CURRENCY_MISMATCH"}:
        return "Critical"
    if classification == "REQUIRES_MANUAL_REVIEW":
        return "Manual review"
    return "Warning"


def exception_radar(results, affected_amount: float) -> None:
    exceptions = results[results.primary_classification != "MATCHED"] if results is not None else None
    total = len(exceptions) if exceptions is not None else 0
    severities = {"Critical": 0, "Warning": 0, "Manual review": 0}
    categories: dict[str, int] = {}
    if exceptions is not None:
        for classification in exceptions.primary_classification:
            severities[severity_for(classification)] += 1
            categories[classification] = categories.get(classification, 0) + 1
    critical_end = 100 * severities["Critical"] / total if total else 0
    warning_end = critical_end + (100 * severities["Warning"] / total if total else 0)
    rows = "".join(f'<div class="risk-row"><span><i class="risk-key tone-{tone}"></i>{label}</span><strong>{severities[label]}</strong></div>' for label, tone in (("Critical", "critical"), ("Warning", "warning"), ("Manual review", "review")))
    category_rows = "".join(f'<div class="category-row"><div><div>{escape(name.replace("_", " ").title())}</div><div class="category-bar"><div class="category-fill" style="width:{(count / max(categories.values()) * 100) if categories else 0:.0f}%"></div></div></div><strong>{count}</strong></div>' for name, count in sorted(categories.items(), key=lambda item: item[1], reverse=True)[:5]) or '<div class="panel-sub">Run reconciliation to populate risk categories.</div>'
    risk_badge = f"₹{affected_amount:,.0f} AT RISK"
    st.markdown(f'<div class="panel panel-pad">{panel_header("Exception radar", "Actual risk distribution in the current batch", risk_badge)}<div class="radar-body"><div class="risk-donut" style="--critical-angle:{critical_end:.1f}%;--warning-angle:{warning_end:.1f}%"><div class="risk-center">{total}<small>EXCEPTIONS</small></div></div><div class="risk-list">{rows}</div></div><div class="category-stack">{category_rows}</div></div>', unsafe_allow_html=True)


def audit_feed(results, limit: int = 7) -> None:
    events = []
    if results is not None:
        for row in results.tail(limit).iloc[::-1].itertuples():
            classification = row.primary_classification
            if classification == "MATCHED":
                title, tone = f"{row.order_id} verified end-to-end", "success"
            elif classification == "PAYMENT_DUPLICATE":
                title, tone = f"Duplicate payment detected · {row.order_id}", "critical"
            elif classification == "REQUIRES_MANUAL_REVIEW":
                title, tone = f"{row.order_id} routed to manual review", "review"
            else:
                title, tone = f"{classification.replace('_', ' ').title()} · {row.order_id}", "warning"
            events.append(f'<div class="audit-event tone-{tone}"><div class="audit-event-title">{escape(title)}</div><div class="audit-event-meta">{escape(row.reason)} · {escape(row.processed_at[11:19])} UTC</div></div>')
    body = "".join(events) or '<div class="panel-sub">No audit events yet. Reconcile a batch to begin the feed.</div>'
    st.markdown(f'<div class="panel panel-pad">{panel_header("Live audit feed", "Most recent real reconciliation decisions", "ACTUAL EVENTS")}<div class="audit-feed">{body}</div></div>', unsafe_allow_html=True)


def source_card_header(name: str, schema: str, state: str) -> None:
    icon = {"Orders": "▤", "Payments": "⇄", "Settlements": "◇"}.get(name, "□")
    tone = "success" if state in {"READY", "STAGED"} else "warning"
    st.markdown(f'<div class="source-head tone-{tone}"><div class="source-icon">{icon}</div><div><div class="source-name">{escape(name)}</div><div class="source-schema">{escape(schema)}</div></div><div class="source-state">{escape(state)}</div></div>', unsafe_allow_html=True)


def validation_sequence(statuses: list[tuple[str, str, str]]) -> None:
    tones = {"Passed": "success", "Warning": "warning", "Failed": "critical", "Pending": "muted"}
    items = "".join(f'<div class="validation-step tone-{tones.get(status, "muted")}"><div class="validation-index">0{index}</div><div class="validation-name">{escape(name)}</div><div class="validation-status">● {escape(status)} · {escape(detail)}</div></div>' for index, (name, status, detail) in enumerate(statuses, 1))
    st.markdown(f'<div class="validation-strip">{items}</div>', unsafe_allow_html=True)


def sticky_summary(items: list[tuple[str, str]]) -> None:
    body = "".join(f'<div class="summary-item">{escape(label)} <strong>{escape(value)}</strong></div>' for label, value in items)
    st.markdown(f'<div class="sticky-summary">{body}</div>', unsafe_allow_html=True)


def decision_card(result: dict) -> None:
    classification = str(result["primary_classification"])
    tone = "matched" if classification == "MATCHED" else "review" if classification == "REQUIRES_MANUAL_REVIEW" else "exception"

    def money(value) -> str:
        return "—" if value is None else f"₹{float(value):,.2f}"

    fields = (("Payment", result.get("payment_id") or "Not linked"), ("Settlement", result.get("settlement_id") or "Not linked"), ("Order amount", money(result.get("order_amount"))), ("Confidence", f'{float(result.get("confidence", 0)):.0%} · rule-based'))
    field_html = "".join(f'<div class="decision-field"><div class="field-label">{escape(label)}</div><div class="field-value">{escape(str(value))}</div></div>' for label, value in fields)
    st.markdown(f'<div class="decision-card"><div class="decision-top"><div><div class="decision-id">Order {escape(str(result["order_id"]))}</div><div class="decision-reason">{escape(str(result["reason"]))}</div></div><span class="status-pill status-{tone}">● {escape(classification.replace("_", " "))}</span></div><div class="decision-grid">{field_html}</div></div>', unsafe_allow_html=True)


def transaction_lineage(result: dict) -> None:
    classification = str(result["primary_classification"])
    payment_broken = classification == "PAYMENT_MISSING"
    settlement_broken = classification == "SETTLEMENT_MISSING"
    payment_warning = classification.startswith("PAYMENT_") and classification not in {"PAYMENT_MISSING", "PAYMENT_FAILED"}
    settlement_warning = classification.startswith("SETTLEMENT_")
    payment_id = result.get("payment_id") or "Connection missing"
    settlement_id = result.get("settlement_id") or "Connection missing"
    payment_state = "Broken here" if payment_broken else "Check failed" if payment_warning or classification == "PAYMENT_FAILED" else "Linked"
    settlement_state = "Broken here" if settlement_broken else "Check failed" if settlement_warning else "Linked" if result.get("settlement_id") else "Not evaluated"
    payment_line = "broken" if payment_broken else ""
    settlement_line = "broken" if settlement_broken else ""
    payment_card = "broken" if payment_broken or payment_warning else ""
    settlement_card = "broken" if settlement_broken or settlement_warning else ""
    st.markdown(f'<div class="lineage"><div class="lineage-node"><div class="lineage-kind">Order</div><div class="lineage-id">{escape(str(result["order_id"]))}</div><div class="lineage-state">● SOURCE</div></div><div class="lineage-link {payment_line}"></div><div class="lineage-node {payment_card}"><div class="lineage-kind">Payment</div><div class="lineage-id">{escape(str(payment_id))}</div><div class="lineage-state">● {escape(payment_state.upper())}</div></div><div class="lineage-link {settlement_line}"></div><div class="lineage-node {settlement_card}"><div class="lineage-kind">Settlement</div><div class="lineage-id">{escape(str(settlement_id))}</div><div class="lineage-state">● {escape(settlement_state.upper())}</div></div></div>', unsafe_allow_html=True)


def ai_boundary() -> None:
    st.markdown('<div class="ai-boundary"><strong>Bounded assistance layer</strong><br>Deterministic classification remains the source of truth. AI receives only the selected computed result and cannot edit records, move money, or resolve an exception.</div>', unsafe_allow_html=True)


def style_chart(figure: go.Figure) -> go.Figure:
    """Apply active semantic tokens to Plotly, which cannot inherit CSS variables."""
    theme = theme_tokens()
    figure.update_layout(template="plotly_white" if st.session_state.get("theme_mode") == "Light" else "plotly_dark", colorway=[theme["accent-info"], theme["status-success"], theme["status-warning"], theme["status-critical"], theme["status-review"]], paper_bgcolor=theme["chart-paper"], plot_bgcolor=theme["chart-paper"], font={"family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", "color": theme["text-secondary"], "size": 11}, title={"font": {"family": "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif", "size": 17, "color": theme["text-primary"]}, "x": .03}, margin={"l": 34, "r": 20, "t": 54, "b": 34}, hoverlabel={"bgcolor": theme["chart-hover"], "bordercolor": theme["border-strong"], "font_color": theme["text-primary"]}, legend={"bgcolor": theme["chart-paper"]})
    figure.update_xaxes(gridcolor=theme["chart-grid"], zerolinecolor=theme["chart-grid"])
    figure.update_yaxes(gridcolor=theme["chart-grid"], zerolinecolor=theme["chart-grid"])
    return figure
