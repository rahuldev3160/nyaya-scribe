"""
Pre-generate study plan templates for all key exam/bucket/level/mode combinations.

Run: python scripts/generate_study_plan_templates.py

Safe to re-run — skips any template_key that already exists in the DB.
Uses the same prompt and model as 8_My_Setup.py so templates are indistinguishable
from live-generated plans.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "web"))

import sqlite3

DB_PATH = ROOT / "data" / "ies.db"

# ── Mirror the label maps from 8_My_Setup.py ──────────────────────────────────

EXAM_LABELS = {"ies": "IES 2026", "rbi": "RBI DEPR", "upsc": "UPSC Eco Optional"}

PREP_LABELS = {
    "fresh":      "Starting fresh — building from basics",
    "foundation": "Some foundation — read material, need practice",
    "revision":   "Revision mode — filling gaps and drilling",
}

MODE_LABELS = {
    "answers_only": "Model answers + answer writing (understand exam patterns)",
    "full_prep":    "Full prep — theory → practice → revision",
    "mcq_drill":    "MCQ drill + quick practice (time-constrained)",
    "mixed":        "Mixed (theory + answers + MCQ)",
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


def _res_text_for(exam_focus: list[str]) -> str:
    try:
        from resources import YOUTUBE
        lines = []
        seen: set[str] = set()
        for exam in exam_focus:
            for r in YOUTUBE.get(exam, []):
                if r["title"] not in seen:
                    seen.add(r["title"])
                    lines.append(f'- {r["title"]} ({r["channel"]}): {r["note"]}')
        return "\n".join(lines) if lines else "No YouTube resources available."
    except Exception:
        return "No YouTube resources available."


def _plan_prompt(exam_focus: list[str], days_to_exam: int, prep_level: str, study_mode: str) -> str:
    exams = ", ".join(EXAM_LABELS.get(e, e) for e in exam_focus)
    res_text = _res_text_for(exam_focus)
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


# ── Key helpers (mirror db.py logic) ─────────────────────────────────────────

def _days_bucket(days_to_exam: int) -> str:
    if days_to_exam <= 15:
        return "crunch"
    if days_to_exam <= 30:
        return "intensive"
    return "standard"


def _template_key(exam_list: list[str], days_to_exam: int, prep_level: str, study_mode: str) -> str:
    exam_part = "_".join(sorted(exam_list))
    bucket = _days_bucket(days_to_exam)
    return f"{exam_part}__{bucket}__{prep_level}__{study_mode}"


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS study_plan_templates (
            template_key    TEXT PRIMARY KEY,
            exam_focus      TEXT NOT NULL,
            days_bucket     TEXT NOT NULL CHECK (days_bucket IN ('crunch','intensive','standard')),
            prep_level      TEXT NOT NULL,
            study_mode      TEXT NOT NULL,
            plan_json       TEXT NOT NULL,
            generated_at    TEXT DEFAULT (datetime('now')),
            version         INTEGER DEFAULT 1
        )
    """)
    conn.commit()


def already_exists(conn: sqlite3.Connection, key: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM study_plan_templates WHERE template_key = ?", (key,)
    ).fetchone()
    return row is not None


def insert_template(
    conn: sqlite3.Connection,
    key: str,
    exam_focus: list[str],
    days_to_exam: int,
    prep_level: str,
    study_mode: str,
    plan: dict,
) -> None:
    conn.execute(
        """INSERT INTO study_plan_templates
               (template_key, exam_focus, days_bucket, prep_level, study_mode, plan_json)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            key,
            json.dumps(sorted(exam_focus)),
            _days_bucket(days_to_exam),
            prep_level,
            study_mode,
            json.dumps(plan),
        ),
    )
    conn.commit()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import anthropic

    EXAM_SUBSETS = [
        ["ies"],
        ["rbi"],
        ["upsc"],
        ["ies", "rbi"],
    ]
    # Representative days_to_exam for each bucket
    BUCKET_DAYS = {
        "crunch":    10,
        "intensive": 21,
        "standard":  60,
    }
    PREP_LEVELS = ["fresh", "foundation", "revision"]
    STUDY_MODES = ["answers_only", "full_prep", "mcq_drill", "mixed"]

    combos = [
        (exams, days, prep, mode)
        for exams in EXAM_SUBSETS
        for days in BUCKET_DAYS.values()
        for prep in PREP_LEVELS
        for mode in STUDY_MODES
    ]

    total = len(combos)
    print(f"Total combinations: {total}")

    conn = get_conn()
    ensure_table(conn)

    client = anthropic.Anthropic()

    inserted = 0
    skipped = 0

    for idx, (exam_focus, days_to_exam, prep_level, study_mode) in enumerate(combos, start=1):
        key = _template_key(exam_focus, days_to_exam, prep_level, study_mode)

        if already_exists(conn, key):
            print(f"[{idx:3}/{total}] {key}  (skipped)")
            skipped += 1
            continue

        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1800,
                system=_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": _plan_prompt(exam_focus, days_to_exam, prep_level, study_mode),
                }],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            plan = json.loads(raw)
        except Exception as e:
            print(f"[{idx:3}/{total}] {key}  ERROR: {e}", file=sys.stderr)
            time.sleep(1)
            continue

        insert_template(conn, key, exam_focus, days_to_exam, prep_level, study_mode, plan)
        print(f"[{idx:3}/{total}] {key}  ✓")
        inserted += 1

        time.sleep(0.5)

    conn.close()
    print(f"\nDone — inserted: {inserted}, skipped: {skipped}, errors: {total - inserted - skipped}")
