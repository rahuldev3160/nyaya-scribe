"""Thin HTTP client to Nyaya Recall's internal API, used when RBI_CONTENT_SOURCE=recall
(PLAN-008 §3, §4). Scribe is the RECALL_CLIENT caller here (opposite direction from
internal_api_bp.py, where Scribe is the callee for Arena) -- registers as SCRIBE_RBI.

Recall's contract deliberately does not return an answer key at fetch time (Arena's
Contract 1 -- see Nyaya-Arena/docs/API_CONTRACTS.md). This is a real behavior difference
from the 'local' path, which has always fetched correct_option/explanation alongside the
question and compared client-side at submit -- see the two-step fetch-then-score flow
below, and score_rbi_attempt(), which callers must use instead of local comparison.
"""
import os

import requests

RECALL_API_URL = os.environ.get("RECALL_API_URL", "http://localhost:8000")
RECALL_API_KEY = os.environ.get("INTERNAL_API_KEY_SCRIBE_RBI", "")
_TIMEOUT = 10

_RBI_MARKING_SCHEME = {"correct": 1, "wrong": -0.25, "unattempted": 0}


class RecallUnavailable(Exception):
    """Raised on any network/auth/shape failure talking to Recall -- callers should
    fail loudly (surface an error), never silently fall back to stale/empty content."""


def _headers() -> dict:
    return {"X-Internal-Api-Key": RECALL_API_KEY}


def _adapt_question(q: dict) -> dict:
    """Recall's {question_id, question_text, options:{A,B,C,D}, ...} -> the shape
    rbi_prep.html / _load_buckets already expect (id, question, option_a..d, ...).
    correct_option/explanation are intentionally None -- not known until scored."""
    opts = q.get("options", {})
    return {
        "id": q["question_id"],
        "question": q["question_text"],
        "option_a": opts.get("A", ""),
        "option_b": opts.get("B", ""),
        "option_c": opts.get("C", ""),
        "option_d": opts.get("D", ""),
        "topic": q.get("topic"),
        "subject": q.get("subject"),
        "difficulty": q.get("difficulty"),
        "is_trap": False,   # not tracked in Recall's migrated schema yet -- documented gap
        "priority_weight": 0,
        "correct_option": None,
        "explanation": None,
    }


def count_rbi_questions(tier: int | None = None) -> int:
    """Approximate total-question count for a tier, for display stats only (e.g.
    rbi_dashboard_bp's 'answered X of Y'). Bounded by Recall's own max count=200 per
    Contract 1 -- exact as long as the tier has <=200 rows (true today: 321 total
    across both tiers), but this is an approximation, not a real COUNT(*), and would
    silently under-report if that ever changes. Do not use for anything score-affecting."""
    return len(fetch_rbi_questions(count=200, tier=tier))


def fetch_rbi_questions(count: int, tier: int | None = None, subject: str | None = None,
                         topic: str | None = None) -> list[dict]:
    params: dict = {"exam_source": "rbi_grade_b", "count": count}
    if tier in (1, 2):
        params["tags"] = f"rbi_tier_{tier}"
    if subject and subject != "all":
        params["subject"] = subject
    if topic and topic != "all":
        params["topic"] = topic
    try:
        resp = requests.get(f"{RECALL_API_URL}/internal/v1/questions", params=params,
                             headers=_headers(), timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise RecallUnavailable(f"Recall fetch failed: {exc}") from exc
    if "questions" not in data:
        raise RecallUnavailable(f"Unexpected Recall response shape: {data}")
    return [_adapt_question(q) for q in data["questions"]]


def score_rbi_attempt(answers: list[dict]) -> dict:
    """answers: [{question_id, selected_option}, ...].
    Returns {question_id: {is_correct, correct_option, marks_awarded, explanation}}."""
    payload = {"answers": answers, "marking_scheme": _RBI_MARKING_SCHEME}
    try:
        resp = requests.post(f"{RECALL_API_URL}/internal/v1/score-attempt", json=payload,
                              headers=_headers(), timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise RecallUnavailable(f"Recall score-attempt failed: {exc}") from exc
    if "results" not in data:
        raise RecallUnavailable(f"Unexpected Recall response shape: {data}")
    return {r["question_id"]: r for r in data["results"]}
