"""Shared Gemini-inspired CSS — call apply_theme() once per page."""
import streamlit as st

_CSS = """
<style>
/* ── Global reset ────────────────────────────────────── */
* { box-sizing: border-box !important; }
body, .main, .block-container { overflow-x: hidden !important; max-width: 100% !important; }

/* ── Layout ──────────────────────────────────────────── */
.block-container { padding-top: 1.2rem !important; padding-bottom: 2rem !important; }
[data-testid="stSidebar"] { background-color: #1C1C1E; border-right: 1px solid #3A3A3C; }
[data-testid="stSidebar"] .block-container { padding-top: 1rem !important; }

/* ── Cards ───────────────────────────────────────────── */
.gem-card {
    background: #2C2C2E;
    border: 1px solid #3A3A3C;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    word-break: break-word;
    overflow-wrap: anywhere;
    max-width: 100%;
}
.gem-card-sm {
    background: #2C2C2E;
    border: 1px solid #3A3A3C;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    word-break: break-word;
    overflow-wrap: anywhere;
    max-width: 100%;
}
.gem-card-accent {
    background: linear-gradient(135deg, rgba(138,180,248,0.08) 0%, rgba(192,132,252,0.08) 100%);
    border: 1px solid rgba(138,180,248,0.3);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    word-break: break-word;
    overflow-wrap: anywhere;
    max-width: 100%;
}

/* ── State badges ────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.badge-unvisited { background: rgba(154,160,166,0.15); color: #9AA0A6; border: 1px solid #3A3A3C; }
.badge-in_study  { background: rgba(253,214,99,0.12);  color: #FDD663; border: 1px solid rgba(253,214,99,0.4); }
.badge-flagged   { background: rgba(138,180,248,0.12); color: #8AB4F8; border: 1px solid rgba(138,180,248,0.4); }
.badge-partial   { background: rgba(129,201,149,0.12); color: #81C995; border: 1px solid rgba(129,201,149,0.4); }
.badge-verified  { background: rgba(129,201,149,0.2);  color: #81C995; border: 1px solid rgba(129,201,149,0.5); }
.badge-decaying  { background: rgba(242,139,130,0.12); color: #F28B82; border: 1px solid rgba(242,139,130,0.4); }

/* ── Answer sections ─────────────────────────────────── */
.answer-section {
    border-left: 3px solid #8AB4F8;
    padding: 12px 16px;
    margin: 12px 0;
    background: rgba(138,180,248,0.04);
    border-radius: 0 8px 8px 0;
    word-break: break-word;
    overflow-wrap: anywhere;
    max-width: 100%;
}
.answer-section-body  { border-left-color: #C084FC; background: rgba(192,132,252,0.04); }
.answer-section-conc  { border-left-color: #81C995; background: rgba(129,201,149,0.04); }

/* ── Score display ───────────────────────────────────── */
.score-card {
    text-align: center;
    padding: 16px;
    border-radius: 12px;
    border: 1px solid #3A3A3C;
}
.score-num { font-size: 2.4rem; font-weight: 700; line-height: 1; }
.score-label { font-size: 0.75rem; color: #9AA0A6; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
.score-green { color: #81C995; border-color: rgba(129,201,149,0.3); background: rgba(129,201,149,0.06); }
.score-amber { color: #FDD663; border-color: rgba(253,214,99,0.3); background: rgba(253,214,99,0.06); }
.score-red   { color: #F28B82; border-color: rgba(242,139,130,0.3); background: rgba(242,139,130,0.06); }

/* ── Chips / key terms ───────────────────────────────── */
.chip {
    display: inline-block;
    background: rgba(138,180,248,0.12);
    color: #8AB4F8;
    border: 1px solid rgba(138,180,248,0.25);
    border-radius: 16px;
    padding: 2px 10px;
    font-size: 0.78rem;
    margin: 2px 3px;
}
.chip-purple {
    background: rgba(192,132,252,0.12);
    color: #C084FC;
    border-color: rgba(192,132,252,0.25);
}
.chip-green {
    background: rgba(129,201,149,0.12);
    color: #81C995;
    border-color: rgba(129,201,149,0.25);
}

/* ── Progress bar ────────────────────────────────────── */
.prog-bar-bg {
    background: #3A3A3C;
    border-radius: 4px;
    height: 5px;
    margin-top: 6px;
    overflow: hidden;
}
.prog-bar-fill {
    background: linear-gradient(90deg, #8AB4F8, #C084FC);
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
}

/* ── Today's Focus cards ─────────────────────────────── */
.focus-card {
    background: linear-gradient(135deg, rgba(138,180,248,0.07) 0%, rgba(192,132,252,0.07) 100%);
    border: 1px solid rgba(138,180,248,0.2);
    border-radius: 14px;
    padding: 18px;
    height: 100%;
    word-break: break-word;
    overflow-wrap: anywhere;
    max-width: 100%;
}
.focus-card h4 { margin: 6px 0 4px; font-size: 0.95rem; color: #E8EAED; }
.focus-card .meta { font-size: 0.78rem; color: #9AA0A6; }

/* ── Section headers ─────────────────────────────────── */
.section-header {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #9AA0A6;
    margin-bottom: 8px;
}

/* ── Info / callout boxes ────────────────────────────── */
[data-testid="stInfo"] {
    background: rgba(138,180,248,0.06) !important;
    border: 1px solid rgba(138,180,248,0.2) !important;
    border-radius: 10px !important;
    color: #E8EAED !important;
}

/* ── Metrics ─────────────────────────────────────────── */
[data-testid="stMetric"] { background: #2C2C2E; border-radius: 10px; padding: 12px; }
[data-testid="stMetricLabel"] { font-size: 0.72rem !important; color: #9AA0A6 !important; }
[data-testid="stMetricValue"] { font-size: 1.5rem !important; color: #E8EAED !important; }

/* ── Tabs ────────────────────────────────────────────── */
[data-testid="stTab"] button { font-size: 0.85rem; }

/* ── Buttons ─────────────────────────────────────────── */
.stButton > button {
    border-radius: 8px !important;
    font-size: 0.82rem !important;
}

/* ── Divider ─────────────────────────────────────────── */
hr { border-color: #3A3A3C !important; margin: 1rem 0 !important; }
</style>
"""


def apply_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


def card(content_html: str, accent: bool = False) -> str:
    cls = "gem-card-accent" if accent else "gem-card"
    return f'<div class="{cls}">{content_html}</div>'


def badge(state: str) -> str:
    emoji_map = {
        "UNVISITED": "○",
        "IN_STUDY":  "◑",
        "FLAGGED":   "⚑",
        "PARTIAL":   "◕",
        "VERIFIED":  "✓",
        "DECAYING":  "↓",
    }
    e = emoji_map.get(state, "?")
    cls = f"badge badge-{state.lower()}"
    return f'<span class="{cls}">{e} {state.replace("_", " ").title()}</span>'


def chip(text: str, variant: str = "") -> str:
    cls = f"chip chip-{variant}" if variant else "chip"
    return f'<span class="{cls}">{text}</span>'


def score_color(score: float) -> str:
    if score >= 7:
        return "score-green"
    elif score >= 5:
        return "score-amber"
    return "score-red"


def score_card_html(label: str, score, denom: int = 10) -> str:
    if score is None:
        color_cls = "score-amber"
        display = "—"
    else:
        color_cls = score_color(float(score))
        display = str(score)
    return f"""<div class="score-card {color_cls}">
  <div class="score-num">{display}</div>
  <div class="score-label">{label}<br><span style="font-size:0.65rem;opacity:0.6;">/ {denom}</span></div>
</div>"""


def progress_bar(value: float, max_val: float = 1.0) -> str:
    pct = min(100, int(100 * value / max_val)) if max_val else 0
    return f"""<div class="prog-bar-bg"><div class="prog-bar-fill" style="width:{pct}%"></div></div>"""
