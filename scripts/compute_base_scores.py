"""
Stage 8: Compute topic base priority scores from PYQ data.
Run: python3 scripts/compute_base_scores.py [--exam ies_2026|upsc_eco_opt]

Computes w1 (recurrence), w2 (recency), w3 (persistence), w5 (syllabus weight).
Stores in topic_base_scores. Skips w4 (CA relevance) and w6 (graph centrality)
which require additional data sources.
"""
import argparse
import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path

EXAM_DB_MAP = {
    "ies_2026": "ies.db",
    "upsc_eco_opt": "upsc.db",
}
CURRENT_YEAR = date.today().year


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def normalize(values: dict) -> dict:
    if not values:
        return values
    max_v = max(values.values())
    min_v = min(values.values())
    spread = max_v - min_v
    if spread == 0:
        return {k: 0.5 for k in values}
    return {k: (v - min_v) / spread for k, v in values.items()}


def compute_scores(conn: sqlite3.Connection, exam_id: str) -> list[dict]:
    # Load exam config
    cfg = conn.execute(
        "SELECT pyq_decay_factor, w5_syllabus_weight FROM exam_configurations WHERE exam_id=?",
        (exam_id,)
    ).fetchone()
    decay_factor = cfg[0] if cfg else 0.9

    # Load all PYQ questions with topic + year
    rows = conn.execute("""
        SELECT q.topic_id, q.paper_id, q.year, t.syllabus_weight
        FROM pyq_questions q
        JOIN topics t ON q.topic_id = t.topic_id AND q.exam_id = t.exam_id
        WHERE q.exam_id = ? AND t.topic_level = 'topic'
    """, (exam_id,)).fetchall()

    # Bucket by topic
    topic_years = defaultdict(list)
    topic_paper = {}
    topic_syllabus_weight = {}
    for r in rows:
        tid, pid, yr, sw = r
        topic_years[tid].append(yr)
        topic_paper[tid] = pid
        topic_syllabus_weight[tid] = sw

    # Load all topics (some may have 0 PYQs)
    all_topics = conn.execute("""
        SELECT topic_id, paper_id, syllabus_weight FROM topics
        WHERE exam_id=? AND topic_level='topic'
    """, (exam_id,)).fetchall()

    for tid, pid, sw in all_topics:
        topic_paper[tid] = pid
        topic_syllabus_weight[tid] = sw
        if tid not in topic_years:
            topic_years[tid] = []

    total_questions = sum(len(yrs) for yrs in topic_years.values())
    all_years = set(yr for yrs in topic_years.values() for yr in yrs)
    year_span = max(all_years) - min(all_years) + 1 if all_years else 1

    raw_scores = {}
    for tid, years in topic_years.items():
        pyq_count = len(years)
        distinct_years = len(set(years))

        # w1: recurrence — questions as fraction of total
        w1 = pyq_count / total_questions if total_questions else 0

        # w2: recency — exponential decay from most recent year
        w2 = sum(
            decay_factor ** (CURRENT_YEAR - yr) for yr in years
        )

        # w3: concept_persistence — distinct years present
        w3 = distinct_years / year_span if year_span else 0

        # w5: syllabus weight (already 0-1 from JSON, but may need normalization)
        w5 = topic_syllabus_weight.get(tid, 1.0)

        raw_scores[tid] = {
            "w1_raw": w1,
            "w2_raw": w2,
            "w3_raw": w3,
            "w5_raw": w5,
            "pyq_count": pyq_count,
            "distinct_years": distinct_years,
        }

    # Normalize w1, w2, w3 to 0-1 range
    w1_raw = {tid: v["w1_raw"] for tid, v in raw_scores.items()}
    w2_raw = {tid: v["w2_raw"] for tid, v in raw_scores.items()}
    w3_raw = {tid: v["w3_raw"] for tid, v in raw_scores.items()}

    w1_norm = normalize(w1_raw)
    w2_norm = normalize(w2_raw)
    w3_norm = normalize(w3_raw)
    # w5: normalize syllabus weights within each paper
    paper_sw = defaultdict(dict)
    for tid in raw_scores:
        paper_sw[topic_paper.get(tid, "")][tid] = topic_syllabus_weight.get(tid, 1.0)
    w5_norm = {}
    for paper, tid_sw in paper_sw.items():
        normed = normalize(tid_sw)
        w5_norm.update(normed)

    # Fetch weights from exam_configurations
    wrow = conn.execute("""
        SELECT w1_pyq_recurrence, w2_pyq_recency, w3_concept_persistence, w5_syllabus_weight
        FROM exam_configurations WHERE exam_id=?
    """, (exam_id,)).fetchone()
    W1, W2, W3, W5 = wrow if wrow else (0.22, 0.20, 0.10, 0.12)

    results = []
    for tid, scores in raw_scores.items():
        w1 = w1_norm.get(tid, 0)
        w2 = w2_norm.get(tid, 0)
        w3 = w3_norm.get(tid, 0)
        w5 = w5_norm.get(tid, 0)

        # Base priority using available weights (w4=0, w6=0 not yet computed)
        base = W1 * w1 + W2 * w2 + W3 * w3 + W5 * w5

        results.append({
            "topic_id": tid,
            "paper_id": topic_paper.get(tid, ""),
            "pyq_count": scores["pyq_count"],
            "distinct_years": scores["distinct_years"],
            "pyq_recurrence_score": round(w1, 4),
            "pyq_recency_score": round(w2, 4),
            "concept_persistence_score": round(w3, 4),
            "ca_relevance_score": 0.0,
            "graph_centrality_score": 0.0,
            "base_priority_score": round(base, 4),
        })

    return results


def upsert_scores(conn: sqlite3.Connection, scores: list[dict], exam_id: str) -> None:
    for s in scores:
        conn.execute("""
            INSERT OR REPLACE INTO topic_base_scores
                (topic_id, exam_id, paper_id, pyq_count, distinct_years,
                 pyq_recurrence_score, pyq_recency_score, concept_persistence_score,
                 ca_relevance_score, graph_centrality_score, base_priority_score,
                 computed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
        """, (
            s["topic_id"], exam_id, s["paper_id"],
            s["pyq_count"], s["distinct_years"],
            s["pyq_recurrence_score"], s["pyq_recency_score"],
            s["concept_persistence_score"],
            s["ca_relevance_score"], s["graph_centrality_score"],
            s["base_priority_score"],
        ))
    conn.commit()


def verify(conn: sqlite3.Connection, scores: list[dict], exam_id: str) -> None:
    by_paper = {}
    for s in sorted(scores, key=lambda x: -x["base_priority_score"]):
        pid = s["paper_id"]
        if pid not in by_paper:
            by_paper[pid] = []
        by_paper[pid].append(s)

    print("\n── Stage 8 Sense Check — Base Priority Scores ─────")

    for pid in sorted(by_paper.keys()):
        print(f"\n  {pid.upper()} (ranked by priority):")
        print(f"  {'topic_id':<42} {'pyq':>5} {'yrs':>5} {'score':>8}")
        print(f"  {'─'*42} {'─'*5} {'─'*5} {'─'*8}")
        for s in by_paper[pid]:
            print(
                f"  {s['topic_id']:<42} {s['pyq_count']:>5} "
                f"{s['distinct_years']:>5} {s['base_priority_score']:>8.4f}"
            )

    total = conn.execute(
        "SELECT COUNT(*) FROM topic_base_scores WHERE exam_id=?", (exam_id,)
    ).fetchone()[0]
    top3 = sorted(scores, key=lambda x: -x["base_priority_score"])[:3]
    n_topics = len(scores)
    print(f"\nTotal scored topics : {total}/{n_topics}")
    print(f"Top 3 by priority   : {', '.join(s['topic_id'] for s in top3)}")
    assert total == n_topics, f"Expected {n_topics} scored topics, got {total}"
    print("\n✓ Base scores computed")
    print("──────────────────────────────────────────────────\n")


def main():
    parser = argparse.ArgumentParser(description="Compute topic base priority scores")
    parser.add_argument(
        "--exam",
        default="ies_2026",
        choices=list(EXAM_DB_MAP.keys()),
        help="Exam ID to compute scores for (default: ies_2026)",
    )
    args = parser.parse_args()

    exam_id = args.exam
    db_filename = EXAM_DB_MAP[exam_id]
    db_path = Path(__file__).parent.parent / "data" / db_filename

    if not db_path.exists():
        print(f"DB not found: {db_path}")
        raise SystemExit(1)

    conn = get_connection(db_path)
    print(f"Computing base priority scores for {exam_id} ({db_filename})...")
    scores = compute_scores(conn, exam_id)
    upsert_scores(conn, scores, exam_id)
    verify(conn, scores, exam_id)
    conn.close()


if __name__ == "__main__":
    main()
