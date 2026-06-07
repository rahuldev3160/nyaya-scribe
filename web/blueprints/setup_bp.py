import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, redirect, render_template, request, url_for
from auth import login_required
from db import get_conn, get_nyaya_conn, get_study_path, get_study_plan_template, load_api_key, log_event, save_onboarding, track_page_time
from resources import AI_TOOLS, YOUTUBE, resources_summary

setup_bp = Blueprint("setup", __name__)

EXAM_LABELS = {
    "ies": "IES 2026 · 19-21 June",
    "rbi": "RBI DEPR · 14 June",
    "upsc": "UPSC Eco Optional · ~Aug 2026",
}
PREP_LABELS = {
    "fresh": "Starting fresh — building from basics",
    "revision": "Revision mode — filling gaps and drilling",
}
MODE_LABELS = {
    "answers_only": "Model answers + answer writing (understand exam patterns)",
    "full_prep": "Full prep — theory → practice → revision",
}

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


def _authoritative_resources(exam_focus: list[str]) -> list[dict]:
    resources = []
    seen: set[str] = set()
    for exam in exam_focus:
        for r in YOUTUBE.get(exam, []):
            if r["title"] not in seen:
                seen.add(r["title"])
                resources.append({"title": r["title"], "channel": r["channel"],
                                   "url": r["url"], "when_to_use": r["note"]})
    return resources


def _rule_based_plan(exam_focus, days_to_exam, prep_level, study_mode):
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
    return {
        "summary": f"You're preparing for {exams} with {days_to_exam} days to your primary exam. We've built a study path based on your profile — follow the phases below and let the app's gap analysis guide your daily topic selection.",
        "current_phase": phase,
        "insight": "Always study your weakest topics first — the app's gap analysis shows you exactly which ones.",
        "phases": [{"name": phase, "duration": f"Days 1–{min(days_to_exam, 30)}",
                    "focus": "Use My Progress to identify your weakest topics daily. Study those first.",
                    "app_features": features, "daily_action": "My Progress → pick top gap topic → Study Brief → Return Quiz."}],
        "today_action": today,
        "ai_tip": AI_TOOLS["theory_check"],
    }


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


def generate_plan(conn, exam_focus, days_to_exam, prep_level, study_mode):
    template = get_study_plan_template(conn, exam_focus, days_to_exam, prep_level, study_mode)
    if template is not None:
        template["resources"] = _authoritative_resources(exam_focus)
        return template
    try:
        import anthropic
        import json as _json
        client = anthropic.Anthropic(api_key=load_api_key())
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1800,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _plan_prompt(exam_focus, days_to_exam, prep_level, study_mode, resources_summary(exam_focus))}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        plan = _json.loads(raw)
    except Exception:
        plan = _rule_based_plan(exam_focus, days_to_exam, prep_level, study_mode)
    plan["resources"] = _authoritative_resources(exam_focus)
    return plan


@setup_bp.route("/setup", methods=["GET", "POST"])
@login_required
def setup_page():
    conn = get_conn()
    user_id = g.user_id
    track_page_time(conn, "My Setup")

    if request.method == "POST":
        exam_focus = []
        if request.form.get("ies"):
            exam_focus.append("ies")
        if request.form.get("rbi"):
            exam_focus.append("rbi")
        if request.form.get("upsc"):
            exam_focus.append("upsc")
        exam_date_str = request.form.get("exam_date", "")
        prep_level = request.form.get("prep_level", "revision")
        study_mode = request.form.get("study_mode", "full_prep")

        if not exam_focus:
            exam_focus = ["ies"]
        try:
            exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
        except ValueError:
            exam_date = date.today()
            exam_date_str = exam_date.isoformat()
        days_to_exam = max(1, (exam_date - date.today()).days)

        nyaya_conn = get_nyaya_conn()
        old_row = nyaya_conn.execute(
            "SELECT exam_focus, exam_date, prep_level, study_mode FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        old_exam_focus = json.loads(old_row["exam_focus"]) if old_row and old_row["exam_focus"] else None
        old_exam_date = old_row["exam_date"] if old_row else None
        old_prep_level = old_row["prep_level"] if old_row else None
        old_study_mode = old_row["study_mode"] if old_row else None

        plan = generate_plan(conn, exam_focus, days_to_exam, prep_level, study_mode)
        save_onboarding(conn, user_id, exam_focus=exam_focus, exam_date=exam_date_str,
                        prep_level=prep_level, study_mode=study_mode, study_path=plan)

        try:
            if sorted(exam_focus) != sorted(old_exam_focus or []):
                log_event("config_changed", payload={"field": "exam_focus", "old_value": old_exam_focus, "new_value": exam_focus})
            if exam_date_str != old_exam_date:
                log_event("config_changed", payload={"field": "exam_date", "old_value": old_exam_date, "new_value": exam_date_str})
            if prep_level != old_prep_level:
                log_event("config_changed", payload={"field": "prep_level", "old_value": old_prep_level, "new_value": prep_level})
            if study_mode != old_study_mode:
                log_event("config_changed", payload={"field": "study_mode", "old_value": old_study_mode, "new_value": study_mode})
        except Exception:
            pass

        return redirect(url_for("setup.setup_page"))

    existing = get_study_path(conn, user_id)
    redo = request.args.get("redo") == "1"

    return render_template(
        "setup.html",
        active_page="setup",
        plan=existing,
        show_form=(not existing or redo),
        exam_labels=EXAM_LABELS,
    )
