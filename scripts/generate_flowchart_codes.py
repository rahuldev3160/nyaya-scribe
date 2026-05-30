"""
One-time script: Generate Mermaid flowchart code for all 347 flow_chart questions.
Saves to the diagram_code column in model_answers.

Run: python3 scripts/generate_flowchart_codes.py

- Skips questions that already have diagram_code (safe to re-run)
- Saves after each question — interrupt anytime and re-run to continue
- Shows progress as it goes
"""
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


MERMAID_PROMPT = """Convert this economics diagram description into valid Mermaid flowchart code.

Rules:
- Use `flowchart TD` (top-down) syntax
- Node labels max 12 words — split long text with <br/> inside quotes
- Use subgraph blocks for parallel left/right branches
- Use plain ASCII — no Unicode arrows inside the code
- Return ONLY the raw Mermaid code, no markdown fences (no ```) and no explanation

Diagram description:
{description}"""


def get_pending(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("""
        SELECT answer_id, question_id, diagram_description
        FROM model_answers
        WHERE diagram_type = 'flow_chart'
          AND diagram_mode = 'described'
          AND (diagram_code IS NULL OR diagram_code = '')
          AND diagram_description IS NOT NULL
          AND diagram_description != ''
        ORDER BY answer_id
    """).fetchall()
    return [dict(r) for r in rows]


def store_code(conn: sqlite3.Connection, answer_id: str, code: str) -> None:
    conn.execute(
        "UPDATE model_answers SET diagram_code=?, diagram_format='mermaid' WHERE answer_id=?",
        (code, answer_id),
    )
    conn.commit()


def strip_fences(code: str) -> str:
    if code.startswith("```"):
        lines = [l for l in code.split("\n") if not l.strip().startswith("```")]
        return "\n".join(lines).strip()
    return code


if __name__ == "__main__":
    import anthropic

    client = anthropic.Anthropic(api_key=load_api_key())

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    pending = get_pending(conn)
    total = len(pending)

    if total == 0:
        print("✅ All flowchart codes already generated — nothing to do.")
        conn.close()
        sys.exit(0)

    # Count how many are already done
    done_count = conn.execute(
        "SELECT COUNT(*) FROM model_answers WHERE diagram_type='flow_chart' AND diagram_code IS NOT NULL"
    ).fetchone()[0]
    print(f"Generating Mermaid code for {total} pending flowchart questions ({done_count} already done)")
    print("Saves after each one — safe to interrupt (Ctrl+C) and re-run to continue\n")

    errors = []
    for i, row in enumerate(pending):
        print(f"[{i+1}/{total}] {row['answer_id']} ...", end="", flush=True)

        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": MERMAID_PROMPT.format(description=row["diagram_description"]),
                }],
            )
            code = strip_fences(resp.content[0].text.strip())
            store_code(conn, row["answer_id"], code)
            print(f" done ({len(code)} chars)")

            # Polite delay to avoid rate limits
            if i < total - 1:
                time.sleep(0.4)

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
    print(f"\n{'✅' if not errors else '⚠️'} Done: {success}/{total} generated")
    if errors:
        print(f"\n{len(errors)} failed:")
        for aid, err in errors:
            print(f"  {aid}: {err}")
        print("\nRe-run this script to retry the failed ones.")
    else:
        print("All flowchart codes stored. The Model Answers page will now render them.")
