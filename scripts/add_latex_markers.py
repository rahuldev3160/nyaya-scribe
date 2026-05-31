"""
One-time script: Add LaTeX $...$ markers to GE-02 model answers.
Stores results in intro_tex / body_tex / conclusion_tex columns.

Usage:
    python3 scripts/add_latex_markers.py --paper ge_02          # pilot run
    python3 scripts/add_latex_markers.py --paper all            # full run

- Skips answers that already have intro_tex (safe to re-run)
- Saves after each answer — interrupt anytime and re-run to continue
"""
import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"
API_KEY_PATH = Path.home() / "Desktop" / "Claude Projects" / "Devthorium" / ".env"


def load_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    for line in API_KEY_PATH.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise ValueError("Set ANTHROPIC_API_KEY env var or place it in Devthorium/.env")


LATEX_PROMPT = """You are processing an economics model answer written in markdown.

Your ONLY task: add LaTeX markers around mathematical expressions.

Rules:
- Use $...$ for inline math: variables, formulas, Greek letters, fractions
- Use $$...$$ for display equations that stand alone on their own line
- Convert Unicode math to proper LaTeX: Δ→\\Delta, θ→\\theta, α→\\alpha, β→\\beta, ∂→\\partial, π→\\pi, σ→\\sigma, λ→\\lambda, μ→\\mu, ∈→\\in, ≥→\\geq, ≤→\\leq, ≠→\\neq, ∞→\\infty, Σ→\\sum, ∫→\\int, etc.
- Convert subscript/superscript Unicode (₀₁₂ / ⁰¹²) to LaTeX subscripts/superscripts: p₀ → $p_0$
- Wrap ratio/fraction notation: ΔC/ΔY → $\frac{\Delta C}{\Delta Y}$
- Keep all words, markdown formatting (**bold**, - bullets, headers), and structure EXACTLY the same
- Do NOT add, remove, or rewrite any content — only add/modify LaTeX markers
- Return ONLY the modified text. No preamble, no explanation, no markdown fences.

Text:
{text}"""


def get_pending(conn: sqlite3.Connection, paper_filter: str) -> list[dict]:
    if paper_filter == "all":
        rows = conn.execute("""
            SELECT ma.answer_id, ma.intro_text, ma.body_text, ma.conclusion_text
            FROM model_answers ma
            WHERE ma.intro_tex IS NULL
            ORDER BY ma.answer_id
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT ma.answer_id, ma.intro_text, ma.body_text, ma.conclusion_text
            FROM model_answers ma
            JOIN pyq_questions q ON ma.question_id = q.question_id
            WHERE q.paper_id = ?
              AND ma.intro_tex IS NULL
            ORDER BY ma.answer_id
        """, (paper_filter,)).fetchall()
    return [dict(r) for r in rows]


def mark_latex(client, text: str) -> str:
    if not text or not text.strip():
        return text
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": LATEX_PROMPT.replace("{text}", text)}],
    )
    return resp.content[0].text.strip()


def store_tex(conn: sqlite3.Connection, answer_id: str, intro: str, body: str, conc: str) -> None:
    conn.execute(
        "UPDATE model_answers SET intro_tex=?, body_tex=?, conclusion_tex=? WHERE answer_id=?",
        (intro, body, conc, answer_id),
    )
    conn.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", default="ge_02",
                        help="Paper ID to process (ge_01/ge_02/ge_03/ge_04/all)")
    args = parser.parse_args()

    import anthropic
    client = anthropic.Anthropic(api_key=load_api_key())

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    pending = get_pending(conn, args.paper)
    total = len(pending)

    if total == 0:
        print(f"✅ All answers for '{args.paper}' already processed — nothing to do.")
        conn.close()
        sys.exit(0)

    done = conn.execute(
        "SELECT COUNT(*) FROM model_answers WHERE intro_tex IS NOT NULL"
    ).fetchone()[0]
    print(f"Adding LaTeX markers to {total} answers for paper='{args.paper}' ({done} already done)")
    print("Processes intro+body+conclusion per answer. Saves after each.")
    print("Safe to interrupt (Ctrl+C) and re-run to continue.\n")

    errors = []
    for i, row in enumerate(pending):
        print(f"[{i+1}/{total}] {row['answer_id']} ...", end="", flush=True)
        try:
            intro_tex = mark_latex(client, row["intro_text"])
            body_tex = mark_latex(client, row["body_text"])
            conc_tex = mark_latex(client, row["conclusion_text"])
            store_tex(conn, row["answer_id"], intro_tex, body_tex, conc_tex)
            print(" done")
            if i < total - 1:
                time.sleep(0.3)
        except KeyboardInterrupt:
            print("\n\nInterrupted — progress saved. Re-run to continue.")
            conn.close()
            sys.exit(0)
        except Exception as e:
            print(f" ERROR: {e}")
            errors.append((row["answer_id"], str(e)))
            time.sleep(1)

    conn.close()
    success = total - len(errors)
    print(f"\n{'✅' if not errors else '⚠️'} Done: {success}/{total} processed")
    if errors:
        print(f"\n{len(errors)} failed:")
        for aid, err in errors:
            print(f"  {aid}: {err}")
        print("\nRe-run this script to retry the failed ones.")
    else:
        print("LaTeX markers added. Restart Streamlit to see math rendered.")
