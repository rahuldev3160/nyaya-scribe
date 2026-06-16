#!/usr/bin/env python3
"""Batch compute inferred_state for all gap_states rows."""
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "ies.db"
EXAM_ID = "ies_2026"
REFRESH_DAYS = 14


def infer_state(cnt: int, avg_score: float | None, last_at: str | None, cutoff: datetime) -> str:
    if cnt == 0:
        return "UNVISITED"
    score = avg_score if avg_score is not None else 0.0
    last = None
    if last_at:
        try:
            last = datetime.fromisoformat(last_at)
        except ValueError:
            pass
    recent = last is not None and last >= cutoff
    if score >= 7.0 and recent:
        return "VERIFIED"
    if score >= 5.0 and not recent:
        return "DECAYING"
    if score >= 4.0:
        return "IN_STUDY"
    return "FLAGGED"


def compute():
    t0 = time.monotonic()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    gap_rows = conn.execute(
        "SELECT user_id, topic_id FROM gap_states WHERE exam_id = ?",
        (EXAM_ID,),
    ).fetchall()

    stats_rows = conn.execute(
        """
        SELECT
            da.user_id,
            pq.topic_id,
            COUNT(*) AS cnt,
            AVG(COALESCE(da.weighted_score,
                CASE da.self_rating
                    WHEN 'got_it'  THEN 8.0
                    WHEN 'partial' THEN 5.0
                    WHEN 'missed'  THEN 2.0
                    ELSE NULL END
            )) AS avg_score,
            MAX(da.created_at) AS last_at
        FROM descriptive_attempts da
        JOIN pyq_questions pq
            ON pq.question_id = da.question_id AND pq.exam_id = da.exam_id
        WHERE da.exam_id = ?
        GROUP BY da.user_id, pq.topic_id
        """,
        (EXAM_ID,),
    ).fetchall()

    stats: dict[tuple[str, str], dict] = {}
    for r in stats_rows:
        stats[(r["user_id"], r["topic_id"])] = {
            "cnt": r["cnt"],
            "avg_score": r["avg_score"],
            "last_at": r["last_at"],
        }

    cutoff = datetime.utcnow() - timedelta(days=REFRESH_DAYS)
    now_iso = datetime.utcnow().isoformat(timespec="seconds")

    updates: list[tuple[str, str, str, str, str]] = []
    breakdown: dict[str, int] = {"UNVISITED": 0, "FLAGGED": 0, "IN_STUDY": 0, "VERIFIED": 0, "DECAYING": 0}

    for row in gap_rows:
        key = (row["user_id"], row["topic_id"])
        s = stats.get(key)
        if s:
            state = infer_state(s["cnt"], s["avg_score"], s["last_at"], cutoff)
        else:
            state = "UNVISITED"
        breakdown[state] += 1
        updates.append((state, now_iso, row["user_id"], row["topic_id"], EXAM_ID))

    conn.executemany(
        "UPDATE gap_states SET inferred_state = ?, inferred_at = ? "
        "WHERE user_id = ? AND topic_id = ? AND exam_id = ?",
        updates,
    )
    conn.commit()
    conn.close()

    elapsed = time.monotonic() - t0
    user_count = len({r["user_id"] for r in gap_rows})
    topic_count = len({r["topic_id"] for r in gap_rows})
    total = len(updates)

    print(f"Computing inferred states for ies.db...")
    print(f"Topics scanned: {user_count} users × {topic_count} topics = {total} rows")
    print(f"Updated: {total} rows")
    print(
        f"Breakdown: UNVISITED={breakdown['UNVISITED']}, FLAGGED={breakdown['FLAGGED']}, "
        f"IN_STUDY={breakdown['IN_STUDY']}, VERIFIED={breakdown['VERIFIED']}, DECAYING={breakdown['DECAYING']}"
    )
    print(f"Done in {elapsed:.2f}s")


if __name__ == "__main__":
    compute()
