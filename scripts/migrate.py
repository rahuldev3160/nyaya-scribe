"""
Pre-start migration runner.
Called before gunicorn on every Railway deploy.

Discovers migration modules in migrations/ by filename order (m001_*, m002_*, …),
checks _migrations table in data/ies.db, and runs any unapplied ones.

To add future content:
  1. Create migrations/mNNN_description.py with a run(conn) function
  2. Commit + push — it auto-applies on next deploy
"""
import importlib.util
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "ies.db"
MIGRATIONS_DIR = ROOT / "migrations"


def _ensure_migrations_table(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _migrations "
        "(name TEXT PRIMARY KEY, applied_at TEXT DEFAULT (datetime('now')))"
    )
    conn.commit()


def _applied(conn) -> set:
    return {r[0] for r in conn.execute("SELECT name FROM _migrations")}


def main() -> None:
    if not DB_PATH.exists():
        print("migrate: data/ies.db absent — skipping (first-boot seed will create it)")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_migrations_table(conn)
        done = _applied(conn)

        migration_files = sorted(MIGRATIONS_DIR.glob("m*.py"))
        if not migration_files:
            print("migrate: no migrations found")
            return

        for path in migration_files:
            name = path.stem
            if name in done:
                print(f"migrate: ~ {name} (already applied)")
                continue

            print(f"migrate: applying {name} …")
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.run(conn)

            conn.execute("INSERT INTO _migrations(name) VALUES (?)", (name,))
            conn.commit()
            print(f"migrate: + {name} done")

    except Exception as exc:
        print(f"migrate: ERROR — {exc}", file=sys.stderr)
        conn.close()
        sys.exit(1)
    else:
        conn.close()


if __name__ == "__main__":
    main()
