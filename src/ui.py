"""Reusable presentation helpers for the ReconcileAI Streamlit interface."""

from html import escape
from textwrap import dedent

import plotly.graph_objects as go
import streamlit as st


PALETTE = ["#6ee7f9", "#8b5cf6", "#34d399", "#fbbf24", "#fb7185", "#60a5fa"]


def inject_theme() -> None:
    """Apply the app's self-contained visual system without external assets."""
    st.markdown(
        dedent(
            """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

            :root {
                --ink: #eef6ff;
                --muted: #9bb0c8;
                --panel: rgba(12, 24, 43, .72);
                --line: rgba(150, 190, 230, .16);
                --cyan: #6ee7f9;
                --violet: #8b5cf6;
                --green: #34d399;
                --amber: #fbbf24;
                --rose: #fb7185;
            }

            html, body, [class*="css"] { font-family: "DM Sans", sans-serif; }
            h1, h2, h3, [data-testid="stMetricValue"] { font-family: "Space Grotesk", sans-serif; }
            .stApp {
                color: var(--ink);
                background:
                    radial-gradient(circle at 12% 8%, rgba(110,231,249,.14), transparent 25rem),
                    radial-gradient(circle at 88% 22%, rgba(139,92,246,.18), transparent 29rem),
                    radial-gradient(circle at 50% 100%, rgba(52,211,153,.08), transparent 30rem),
                    linear-gradient(145deg, #050a13 0%, #091426 46%, #050913 100%);
            }
            .stApp::before {
                content: ""; position: fixed; inset: 0; pointer-events: none; opacity: .16;
                background-image: linear-gradient(rgba(110,231,249,.12) 1px, transparent 1px),
                                  linear-gradient(90deg, rgba(110,231,249,.12) 1px, transparent 1px);
                background-size: 48px 48px; mask-image: linear-gradient(to bottom, black, transparent 82%);
                transform: perspective(600px) rotateX(63deg) scale(1.7) translateY(20%);
                transform-origin: bottom center;
            }
            [data-testid="stHeader"] { background: transparent; }
            [data-testid="stAppViewContainer"] > .main { position: relative; z-index: 1; }
            .block-container { max-width: 1440px; padding-top: 1.25rem; padding-bottom: 4rem; }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, rgba(7,15,28,.97), rgba(10,22,39,.94));
                border-right: 1px solid var(--line); box-shadow: 18px 0 70px rgba(0,0,0,.28);
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--muted); }

            .hero-scene {
                position: relative; overflow: hidden; min-height: 330px; padding: 3.1rem 3.2rem;
                display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(300px, .65fr); gap: 2rem;
                align-items: center; border: 1px solid rgba(160,205,245,.18); border-radius: 30px;
                background: linear-gradient(135deg, rgba(16,34,59,.94), rgba(8,18,34,.78));
                box-shadow: 0 38px 100px rgba(0,0,0,.44), inset 0 1px rgba(255,255,255,.08);
                transform-style: preserve-3d; perspective: 1000px;
            }
            .hero-scene::after {
                content: ""; position: absolute; width: 430px; height: 430px; right: -110px; top: -150px;
                border-radius: 50%; background: radial-gradient(circle, rgba(110,231,249,.22), rgba(139,92,246,.09) 42%, transparent 70%);
                filter: blur(4px); animation: ambientPulse 7s ease-in-out infinite;
            }
            .hero-copy { position: relative; z-index: 3; transform: translateZ(50px); }
            .eyebrow { display: inline-flex; gap: .55rem; align-items: center; padding: .48rem .82rem;
                border: 1px solid rgba(110,231,249,.28); border-radius: 999px; color: var(--cyan);
                background: rgba(110,231,249,.07); font-size: .76rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
            .eyebrow-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); box-shadow: 0 0 16px var(--green); }
            .hero-title { margin: 1.25rem 0 .7rem; font: 700 clamp(2.7rem, 6vw, 5.4rem)/.95 "Space Grotesk", sans-serif;
                letter-spacing: -.065em; color: #f7fbff; text-shadow: 0 14px 50px rgba(110,231,249,.15); }
            .hero-title span { background: linear-gradient(100deg, var(--cyan), #b8a1ff 58%, var(--green));
                -webkit-background-clip: text; color: transparent; }
            .hero-subtitle { max-width: 720px; color: #b6c7da; font-size: 1.04rem; line-height: 1.7; }
            .hero-tags { display: flex; flex-wrap: wrap; gap: .65rem; margin-top: 1.35rem; }
            .hero-tag { padding: .52rem .75rem; border-radius: 12px; color: #c8d8e9; font-size: .82rem;
                background: rgba(255,255,255,.045); border: 1px solid rgba(255,255,255,.08); box-shadow: inset 0 1px rgba(255,255,255,.05); }

            .hero-visual { position: relative; min-height: 235px; z-index: 2; transform-style: preserve-3d; perspective: 900px; }
            .ledger-card { position: absolute; width: 235px; height: 142px; right: 12%; top: 42px; padding: 1.15rem;
                border-radius: 20px; border: 1px solid rgba(255,255,255,.18); backdrop-filter: blur(15px);
                background: linear-gradient(135deg, rgba(22,49,76,.92), rgba(13,28,50,.72));
                box-shadow: 0 30px 50px rgba(0,0,0,.42), inset 0 1px rgba(255,255,255,.15);
                transform: rotateY(-18deg) rotateX(9deg) translateZ(40px); animation: floatCard 5.8s ease-in-out infinite;
            }
            .ledger-card.back { right: 2%; top: 13px; opacity: .5; transform: rotateY(-18deg) rotateX(9deg) translateZ(-40px) translateX(20px); animation-delay: -1.8s; }
            .ledger-card.mid { right: 7%; top: 28px; opacity: .7; transform: rotateY(-18deg) rotateX(9deg) translateZ(0); animation-delay: -.9s; }
            .card-label { color: var(--muted); font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; }
            .card-value { margin-top: .45rem; font: 700 1.75rem "Space Grotesk", sans-serif; color: #fff; }
            .card-line { height: 5px; margin-top: .75rem; border-radius: 9px; background: linear-gradient(90deg, var(--cyan) 72%, rgba(255,255,255,.08) 72%); }
            .card-status { margin-top: .72rem; color: var(--green); font-size: .75rem; font-weight: 700; }

            .workflow-rail { margin: 1.2rem 0 1.8rem; padding: .85rem 1rem; display: grid; grid-template-columns: repeat(5, 1fr);
                border: 1px solid var(--line); border-radius: 18px; background: rgba(7,17,31,.62); box-shadow: 0 18px 48px rgba(0,0,0,.22); }
            .workflow-step { position: relative; text-align: center; color: var(--muted); font-size: .78rem; font-weight: 600; }
            .workflow-step::after { content: ""; position: absolute; top: 11px; left: 62%; width: 76%; height: 1px;
                background: linear-gradient(90deg, rgba(110,231,249,.7), rgba(139,92,246,.2)); }
            .workflow-step:last-child::after { display: none; }
            .step-dot { display: block; width: 22px; height: 22px; margin: 0 auto .42rem; border-radius: 7px;
                background: linear-gradient(145deg, var(--cyan), var(--violet)); box-shadow: 0 5px 18px rgba(110,231,249,.28); transform: rotate(45deg); }

            div[data-testid="stMetric"] { position: relative; overflow: hidden; min-height: 126px; padding: 1.15rem 1.2rem;
                border: 1px solid var(--line); border-radius: 19px; background: linear-gradient(145deg, rgba(18,37,62,.86), rgba(8,19,35,.78));
                box-shadow: 0 22px 46px rgba(0,0,0,.24), inset 0 1px rgba(255,255,255,.07); transition: .28s ease; transform-style: preserve-3d; }
            div[data-testid="stMetric"]::before { content: ""; position: absolute; width: 90px; height: 90px; right: -35px; top: -40px;
                border-radius: 50%; background: rgba(110,231,249,.14); filter: blur(5px); }
            div[data-testid="stMetric"]:hover { transform: translateY(-5px) rotateX(2deg); border-color: rgba(110,231,249,.34); box-shadow: 0 30px 60px rgba(0,0,0,.35); }
            [data-testid="stMetricLabel"] { color: var(--muted); }
            [data-testid="stMetricValue"] { color: #f5fbff; letter-spacing: -.035em; }

            .section-kicker { margin-top: 1rem; color: var(--cyan); font-size: .72rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
            .section-title { margin: .15rem 0 .15rem; color: #f4f9ff; font: 650 1.65rem "Space Grotesk", sans-serif; letter-spacing: -.035em; }
            .section-copy { margin: 0 0 1rem; color: var(--muted); font-size: .9rem; }

            .decision-card { position: relative; padding: 1.35rem 1.45rem; margin-bottom: 1rem; border-radius: 20px;
                border: 1px solid var(--line); background: linear-gradient(145deg, rgba(17,35,58,.9), rgba(8,18,33,.78));
                box-shadow: 0 25px 58px rgba(0,0,0,.28), inset 0 1px rgba(255,255,255,.07); }
            .decision-top { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; }
            .decision-id { color: var(--muted); font-size: .75rem; letter-spacing: .1em; text-transform: uppercase; }
            .decision-reason { margin-top: .7rem; color: #d9e6f3; font-size: 1rem; line-height: 1.55; }
            .decision-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: .7rem; margin-top: 1rem; }
            .decision-field { padding: .75rem; border: 1px solid rgba(255,255,255,.07); border-radius: 13px; background: rgba(255,255,255,.035); }
            .field-label { color: var(--muted); font-size: .68rem; text-transform: uppercase; letter-spacing: .08em; }
            .field-value { margin-top: .25rem; color: #f0f7ff; font-weight: 700; }
            .status-pill { display: inline-flex; padding: .42rem .7rem; border-radius: 999px; font-size: .72rem; font-weight: 800; letter-spacing: .04em; }
            .status-matched { color: #8ff7cd; background: rgba(52,211,153,.12); border: 1px solid rgba(52,211,153,.28); }
            .status-review { color: #ffe29a; background: rgba(251,191,36,.12); border: 1px solid rgba(251,191,36,.3); }
            .status-exception { color: #ffb0bd; background: rgba(251,113,133,.12); border: 1px solid rgba(251,113,133,.3); }

            .stButton > button, .stDownloadButton > button { border: 1px solid rgba(110,231,249,.28); border-radius: 13px;
                color: #ecfaff; background: linear-gradient(135deg, rgba(28,64,91,.96), rgba(58,42,108,.92));
                box-shadow: 0 12px 28px rgba(0,0,0,.3), inset 0 1px rgba(255,255,255,.12); transition: .22s ease; }
            .stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--cyan); color: white; transform: translateY(-2px); box-shadow: 0 17px 36px rgba(38,163,197,.2); }
            [data-testid="stFileUploaderDropzone"], [data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {
                border: 1px solid var(--line); border-radius: 17px; background: rgba(8,18,33,.62); box-shadow: 0 20px 42px rgba(0,0,0,.2); overflow: hidden; }
            [data-baseweb="tab-list"] { gap: .45rem; padding: .4rem; border-radius: 15px; background: rgba(7,16,30,.68); border: 1px solid var(--line); }
            [data-baseweb="tab"] { border-radius: 11px; color: var(--muted); padding: .65rem .9rem; }
            [aria-selected="true"][data-baseweb="tab"] { color: #fff; background: linear-gradient(135deg, rgba(110,231,249,.14), rgba(139,92,246,.18)); }
            [data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 15px; background: rgba(8,18,33,.5); }
            [data-testid="stAlert"] { border-radius: 14px; backdrop-filter: blur(12px); }

            @keyframes floatCard { 0%,100% { transform: rotateY(-18deg) rotateX(9deg) translateY(0) translateZ(40px); } 50% { transform: rotateY(-13deg) rotateX(6deg) translateY(-12px) translateZ(55px); } }
            @keyframes ambientPulse { 0%,100% { transform: scale(.9); opacity: .65; } 50% { transform: scale(1.08); opacity: 1; } }
            @media (max-width: 900px) { .hero-scene { grid-template-columns: 1fr; padding: 2rem; } .hero-visual { display: none; } .decision-grid { grid-template-columns: repeat(2,1fr); } }
            @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: .001ms !important; animation-iteration-count: 1 !important; transition-duration: .001ms !important; } }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        dedent(
            """
            <div class="hero-scene">
              <div class="hero-copy">
                <div class="eyebrow"><span class="eyebrow-dot"></span> Razorpay AI Buildathon 2026</div>
                <div class="hero-title">Reconcile<span>AI</span></div>
                <div class="hero-subtitle">A dimensional finance-control workspace that turns fragmented orders, payments, and settlements into one explainable audit story.</div>
                <div class="hero-tags">
                  <span class="hero-tag">Deterministic source of truth</span>
                  <span class="hero-tag">Synthetic-data safe</span>
                  <span class="hero-tag">Audited AI assistance</span>
                </div>
              </div>
              <div class="hero-visual" aria-hidden="true">
                <div class="ledger-card back"></div><div class="ledger-card mid"></div>
                <div class="ledger-card"><div class="card-label">Reconciliation signal</div><div class="card-value">₹ 1.79M</div><div class="card-line"></div><div class="card-status">● VERIFIED PIPELINE</div></div>
              </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_workflow() -> None:
    steps = "".join(f'<div class="workflow-step"><span class="step-dot"></span>{name}</div>' for name in ("Load", "Validate", "Match", "Review", "Export"))
    st.markdown(f'<div class="workflow-rail">{steps}</div>', unsafe_allow_html=True)


def section_header(kicker: str, title: str, copy: str) -> None:
    st.markdown(
        f'<div class="section-kicker">{escape(kicker)}</div><div class="section-title">{escape(title)}</div><p class="section-copy">{escape(copy)}</p>',
        unsafe_allow_html=True,
    )


def decision_card(result: dict) -> None:
    classification = str(result["primary_classification"])
    tone = "matched" if classification == "MATCHED" else "review" if classification == "REQUIRES_MANUAL_REVIEW" else "exception"

    def money(value) -> str:
        return "—" if value is None else f"₹{float(value):,.2f}"

    fields = (
        ("Payment", result.get("payment_id") or "Not linked"),
        ("Settlement", result.get("settlement_id") or "Not linked"),
        ("Order amount", money(result.get("order_amount"))),
        ("Confidence", f'{float(result.get("confidence", 0)):.0%} · rule-based'),
    )
    field_html = "".join(
        f'<div class="decision-field"><div class="field-label">{escape(label)}</div><div class="field-value">{escape(str(value))}</div></div>'
        for label, value in fields
    )
    st.markdown(
        f'<div class="decision-card"><div class="decision-top"><div><div class="decision-id">Order {escape(str(result["order_id"]))}</div>'
        f'<div class="decision-reason">{escape(str(result["reason"]))}</div></div><span class="status-pill status-{tone}">{escape(classification.replace("_", " "))}</span></div>'
        f'<div class="decision-grid">{field_html}</div></div>',
        unsafe_allow_html=True,
    )


def style_chart(figure: go.Figure) -> go.Figure:
    """Give every Plotly figure a consistent translucent finance-console finish."""
    figure.update_layout(
        template="plotly_dark",
        colorway=PALETTE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(5,12,24,.28)",
        font={"family": "DM Sans", "color": "#c4d5e7"},
        title={"font": {"family": "Space Grotesk", "size": 20, "color": "#f1f7ff"}, "x": 0.03},
        margin={"l": 35, "r": 24, "t": 62, "b": 38},
        hoverlabel={"bgcolor": "#10243c", "bordercolor": "#6ee7f9", "font_color": "#f4f9ff"},
        legend={"bgcolor": "rgba(0,0,0,0)"},
    )
    figure.update_xaxes(gridcolor="rgba(155,176,200,.10)", zerolinecolor="rgba(155,176,200,.12)")
    figure.update_yaxes(gridcolor="rgba(155,176,200,.10)", zerolinecolor="rgba(155,176,200,.12)")
    return figure

