"""Onboarding wizard + study path manager. Fires on first login; accessible anytime via sidebar."""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from auth import require_user
from db import get_conn, get_study_path, get_study_plan_template, load_api_key, save_onboarding, track_page_time
from resources import AI_TOOLS, YOUTUBE, resources_summary
from styles import apply_theme

st.set_page_config(page_title="My Setup · Exam Prep", layout="centered", page_icon="⚙️")
apply_theme()

conn = get_conn()
user_id = require_user(conn)
track_page_time(conn, "My Setup")

# ── Labels ─────────────────────────────────────────────────────────────────────
EXAM_LABELS = {
    "ies":  "IES 2026 · 19-21 June",
    "rbi":  "RBI DEPR · 14 June",
    "upsc": "UPSC Eco Optional · ~Aug 2026",
}
PREP_LABELS = {
    "fresh":    "Starting fresh — building from basics",
    "revision": "Revision mode — filling gaps and drilling",
}
MODE_LABELS = {
    "answers_only": "Model answers + answer writing (understand exam patterns)",
    "full_prep":    "Full prep — theory → practice → revision",
}

# ─────────────────────────────────────────────────────────────────────────────
# AI plan generation
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM = """You are an expert study advisor for Indian competitive economics exams (IES, RBI DEPR, UPSC Economics Optional). Generate a personalised study plan.

Return ONLY a valid JSON object with this exact schema — no markdown, no extra text:
{
  "summary": "2-3 sentence personalised message addressing the user directly",
  "current_phase": "name of their starting phase",
  "insight": "the single most important insight for this specific user (1 sentence)",
  "phases": [
    {
      "name": "phase name",
      "duration": "e.g. Days 1-20",
      "focus": "what to focus on in 1-2 sentences",
      "app_features": ["feature name"],
      "daily_action": "specific thing to do each day in this phase"
    }
  ],
  "today_action": "the single most important thing to do today (specific, actionable) — refer to app features by name only, do not include URLs or hyperlinks",
  "ai_tip": "one specific tip on how to use Gemini or Claude in their prep — no URLs"
}

Important: do NOT include a resources field — resources are injected separately. Do NOT put any URLs or hyperlinks anywhere in the JSON."""


def _plan_prompt(exam_focus, days_to_exam, prep_level, study_mode, res_text):
    exams = ", ".join(EXAM_LABELS.get(e, e) for e in exam_focus)
    return f"""Generate a study plan for this user:

Exams preparing for: {exams}
Days until primary exam: {days_to_exam}
Current preparation level: {PREP_LABELS.get(prep_level, prep_level)}
Primary goal: {MODE_LABELS.get(study_mode, study_mode)}

Available features in the Descriptive Exams app:
- Study Brief: AI topic summaries for IES/UPSC topics
- Model Answers: 1219 IES PYQs + 908 UPSC model answers with examiner rubrics
- Return Quiz: Topic MCQ practice with mastery tracking and gap analysis
- Phase 1 Drill: 303 RBI MCQs (IS-LM, Mundell-Fleming etc.) with smart weighted serving
- Tier 2 Quiz: 54 RBI current-affairs questions across 9 buckets
- My Progress: Gap analysis dashboard showing mastery % per topic

YouTube resources available:
{res_text}

For AI tools: Gemini and Claude are available.

Write a plan that is honest and specific — not generic motivational text."""


def _rule_based_plan(exam_focus, days_to_exam, prep_level, study_mode):
    """Fallback plan when API key is absent."""
    exams = ", ".join(EXAM_LABELS.get(e, e) for e in exam_focus)

    if days_to_exam <= 15:
        phase = "Crunch Mode"
    elif days_to_exam <= 30 or prep_level == "revision":
        phase = "Intensive Practice"
    elif prep_level == "fresh":
        phase = "Theory Building"
    else:
        phase = "Practice & Application"

    if "rbi" in exam_focus and days_to_exam <= 20:
        today = "Open Phase 1 Drill → Smart Serve (20 questions). IS-LM loads first — highest exam weight."
        features = ["Phase 1 Drill", "Tier 2 Quiz", "My Progress"]
    elif study_mode == "answers_only":
        today = "Open Model Answers → Paper I → start with the first topic. Read the rubric tab for each answer."
        features = ["Model Answers", "Study Brief"]
    elif prep_level == "fresh":
        today = "Open Study Brief → read IS-LM Framework. After reading, watch the @rahuldev0108 audio episode on the same topic."
        features = ["Study Brief", "Model Answers", "Return Quiz"]
    else:
        today = "Open My Progress → find your top gap topic → Return Quiz on that topic (10 questions)."
        features = ["Return Quiz", "My Progress", "Study Brief"]

    resources = []
    seen = set()
    for exam in exam_focus:
        for r in YOUTUBE.get(exam, []):
            if r["title"] not in seen:
                seen.add(r["title"])
                resources.append({"title": r["title"], "channel": r["channel"],
                                  "url": r["url"], "when_to_use": r["note"]})

    return {
        "summary": (
            f"You're preparing for {exams} with {days_to_exam} days to your primary exam. "
            "We've built a study path based on your profile — follow the phases below and "
            "let the app's gap analysis guide your daily topic selection."
        ),
        "current_phase": phase,
        "insight": "Always study your weakest topics first — the app's gap analysis shows you exactly which ones.",
        "phases": [{
            "name": phase,
            "duration": f"Days 1–{min(days_to_exam, 30)}",
            "focus": "Use My Progress to identify your weakest topics daily. Study those first.",
            "app_features": features,
            "daily_action": "My Progress → pick top gap topic → Study Brief → Return Quiz.",
        }],
        "resources": resources,
        "today_action": today,
        "ai_tip": AI_TOOLS["theory_check"],
    }


def _authoritative_resources(exam_focus: list[str]) -> list[dict]:
    """Always return resources from resources.py — never trust AI-generated URLs."""
    resources = []
    seen: set[str] = set()
    for exam in exam_focus:
        for r in YOUTUBE.get(exam, []):
            if r["title"] not in seen:
                seen.add(r["title"])
                resources.append({
                    "title": r["title"],
                    "channel": r["channel"],
                    "url": r["url"],
                    "when_to_use": r["note"],
                })
    return resources


def generate_plan(exam_focus, days_to_exam, prep_level, study_mode):
    template = get_study_plan_template(conn, exam_focus, days_to_exam, prep_level, study_mode)
    if template is not None:
        st.info("✓ Plan loaded instantly")
        template["resources"] = _authoritative_resources(exam_focus)
        return template

    res_text = resources_summary(exam_focus)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=load_api_key())
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1800,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _plan_prompt(
                exam_focus, days_to_exam, prep_level, study_mode, res_text
            )}],
        )
        raw = resp.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        plan = json.loads(raw)
    except Exception:
        plan = _rule_based_plan(exam_focus, days_to_exam, prep_level, study_mode)
    # Always override resources with authoritative URLs from resources.py
    plan["resources"] = _authoritative_resources(exam_focus)
    return plan


# ─────────────────────────────────────────────────────────────────────────────
# Render plan
# ─────────────────────────────────────────────────────────────────────────────

def _render_plan(plan: dict):
    st.markdown(
        f'<div style="background:#1E3A2F;border:1px solid #81C99533;border-radius:10px;'
        f'padding:16px 20px;margin-bottom:20px">'
        f'<div style="color:#81C995;font-weight:700;font-size:0.82rem;text-transform:uppercase;'
        f'letter-spacing:.08em;margin-bottom:6px">Your Study Path</div>'
        f'<div style="color:#E8EAED;font-size:0.95rem">{plan.get("summary","")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div style="background:#1C2B3A;border:1px solid #8AB4F833;border-radius:8px;'
            f'padding:12px 16px">'
            f'<div style="color:#8AB4F8;font-size:0.75rem;text-transform:uppercase;'
            f'font-weight:600;letter-spacing:.07em">Starting Phase</div>'
            f'<div style="color:#E8EAED;font-weight:700;font-size:1.1rem;margin-top:4px">'
            f'{plan.get("current_phase","")}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div style="background:#1C2B3A;border:1px solid #FDD66333;border-radius:8px;'
            f'padding:12px 16px">'
            f'<div style="color:#FDD663;font-size:0.75rem;text-transform:uppercase;'
            f'font-weight:600;letter-spacing:.07em">Key Insight</div>'
            f'<div style="color:#E8EAED;font-size:0.88rem;margin-top:4px">'
            f'{plan.get("insight","")}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Today's action
    st.markdown(
        f'<div style="background:#2A1F3D;border:1px solid #C084FC33;border-radius:8px;'
        f'padding:12px 16px;margin-bottom:20px">'
        f'<span style="color:#C084FC;font-weight:700;font-size:0.8rem;text-transform:uppercase;'
        f'letter-spacing:.07em">🎯 Start Today</span><br>'
        f'<span style="color:#E8EAED;font-size:0.92rem">{plan.get("today_action","")}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Phases
    phases = plan.get("phases", [])
    if phases:
        with st.expander("📅 Study Phases", expanded=True):
            for ph in phases:
                feats = " · ".join(ph.get("app_features", []))
                st.markdown(
                    f'**{ph.get("name","")}** &nbsp;'
                    f'<span style="color:#9AA0A6;font-size:0.8rem">{ph.get("duration","")}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(f'{ph.get("focus","")}')
                if feats:
                    st.markdown(
                        f'<span style="color:#8AB4F8;font-size:0.8rem">App: {feats}</span>',
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f'<span style="color:#9AA0A6;font-size:0.82rem">Daily: {ph.get("daily_action","")}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("---")

    # Resources
    resources = plan.get("resources", [])
    if resources:
        with st.expander("📺 Recommended Resources"):
            for r in resources:
                url = r.get("url", "")
                title = r.get("title", "")
                channel = r.get("channel", "")
                note = r.get("when_to_use", "")
                if url:
                    st.markdown(f'**[{title}]({url})** — {channel}')
                else:
                    st.markdown(f'**{title}** — {channel}')
                st.markdown(f'<span style="color:#9AA0A6;font-size:0.82rem">{note}</span>',
                            unsafe_allow_html=True)

    # AI tip
    ai_tip = plan.get("ai_tip", "")
    if ai_tip:
        st.info(f"💡 **AI tip:** {ai_tip}")


# ─────────────────────────────────────────────────────────────────────────────
# Page layout
# ─────────────────────────────────────────────────────────────────────────────

existing = get_study_path(conn, user_id)
is_update = bool(existing) and not st.session_state.get("_redo_setup")

if is_update:
    st.markdown("## ⚙️ My Study Setup")
    st.markdown(
        '<div style="color:#9AA0A6;font-size:0.88rem;margin-bottom:1.5rem">'
        'Your current study plan is shown below. Update your answers to regenerate it.</div>',
        unsafe_allow_html=True,
    )
    _render_plan(existing)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Update my preferences & regenerate plan"):
        st.session_state._redo_setup = True
        st.rerun()
    conn.close()
    st.stop()

# ── Setup form ─────────────────────────────────────────────────────────────────
st.markdown("## ⚙️ Set Up Your Study Path")
st.markdown(
    '<div style="color:#9AA0A6;font-size:0.88rem;margin-bottom:1.5rem">'
    'Answer 4 quick questions and we\'ll build a personalised study plan with '
    'recommended resources and a daily action for today.</div>',
    unsafe_allow_html=True,
)

with st.form("setup_form"):
    st.markdown("**Which exams are you preparing for?**")
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        ies_on  = st.checkbox("IES 2026 · 19-21 June",      value=True)
    with col_e2:
        rbi_on  = st.checkbox("RBI DEPR · 14 June",          value=False)
    with col_e3:
        upsc_on = st.checkbox("UPSC Eco Optional · ~Aug 2026", value=False)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**When is your primary exam?**")
    exam_date_val = st.date_input(
        "Exam date",
        value=date.today() + timedelta(days=30),
        min_value=date.today(),
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    prep_level_val = st.radio(
        "**Where are you in your preparation?**",
        options=list(PREP_LABELS.keys()),
        format_func=lambda k: PREP_LABELS[k],
        index=1,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    study_mode_val = st.radio(
        "**What do you mainly want from this app?**",
        options=list(MODE_LABELS.keys()),
        format_func=lambda k: MODE_LABELS[k],
        index=3,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    submitted = st.form_submit_button(
        "Generate My Study Plan →",
        use_container_width=True,
        type="primary",
    )

if submitted:
    exam_focus = [e for e, on in [("ies", ies_on), ("rbi", rbi_on), ("upsc", upsc_on)] if on]
    if not exam_focus:
        st.error("Please select at least one exam.")
    else:
        days_to_exam = max(1, (exam_date_val - date.today()).days)
        with st.spinner("Generating your personalised study plan…"):
            plan = generate_plan(exam_focus, days_to_exam, prep_level_val, study_mode_val)
        save_onboarding(
            conn, user_id,
            exam_focus=exam_focus,
            exam_date=exam_date_val.isoformat(),
            prep_level=prep_level_val,
            study_mode=study_mode_val,
            study_path=plan,
        )
        st.session_state._redo_setup = False
        st.success("Your study plan is ready!")
        st.markdown("<br>", unsafe_allow_html=True)
        _render_plan(plan)
        st.markdown("<br>", unsafe_allow_html=True)
        st.page_link("app.py", label="→ Go to Dashboard", use_container_width=True)

conn.close()
