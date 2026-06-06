#!/usr/bin/env python3
"""Pull user feedback from production Railway → data/feedback_snapshot.json.

Run before any feedback review session:
    python3 scripts/pull_feedback.py
"""
import json
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).parent.parent / "data" / "feedback_snapshot.json"

# Tries nyaya.db (post-m015) and ies.db (pre-migration) — merges deduplicated by feedback_id
_REMOTE = """python3 -c "
import sqlite3, json
results = {}
for path in ['/app/data/nyaya.db', '/app/data/ies.db']:
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute('SELECT * FROM user_feedback ORDER BY created_at DESC').fetchall()
        for r in rows:
            d = dict(r)
            results[d['feedback_id']] = d
        conn.close()
    except Exception:
        pass
data = sorted(results.values(), key=lambda x: x.get('created_at',''), reverse=True)
print(json.dumps(data, indent=2))
" """

_CAT_ICONS = {"bug": "🐛", "feature": "✨", "issue": "⚠️", "other": "💬"}
_STATUS_ICONS = {"open": "🔴", "acknowledged": "🟡", "resolved": "✅"}


def main():
    print("Connecting to Railway production…")
    result = subprocess.run(
        ["railway", "ssh", _REMOTE],
        capture_output=True, text=True, timeout=45
    )
    if result.returncode != 0:
        print(f"SSH error:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    stdout = result.stdout
    start = stdout.find("[")
    if start == -1:
        print(f"No JSON found in output:\n{stdout}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(stdout[start:])
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    print(f"\n✓ {len(data)} feedback items saved to {OUT.name}\n")
    for item in data:
        cat = _CAT_ICONS.get(item.get("category", ""), "?")
        status = _STATUS_ICONS.get(item.get("status", "open"), "?")
        title = (item.get("title") or "")[:65]
        print(f"  {status} {cat}  {title}")


if __name__ == "__main__":
    main()
