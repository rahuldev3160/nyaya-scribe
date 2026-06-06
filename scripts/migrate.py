"""
Pre-start migration runner. Multi-DB support.
Each migration file declares DB = "ies" | "rbi" | "upsc" (defaults to "ies").
Called before gunicorn on every Railway deploy.

To add future content:
  1. Create migrations/mNNN_description.py with DB = "<target>" and run(conn)
  2. Commit + push — it auto-applies on next deploy
"""
import importlib.util
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATHS = {
    "ies":  ROOT / "data" / "ies.db",
    "rbi":  ROOT / "data" / "rbi.db",
    "upsc": ROOT / "data" / "upsc.db",
}
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
    migration_files = sorted(MIGRATIONS_DIR.glob("m*.py"))
    if not migration_files:
        print("migrate: no migrations found")
        return

    conns: dict = {}
    done: dict = {}

    try:
        for path in migration_files:
            name = path.stem
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            db_key = getattr(mod, "DB", "ies")
            if db_key not in DB_PATHS:
                print(f"migrate: ERROR unknown DB '{db_key}' in {name}", file=sys.stderr)
                sys.exit(1)

            if db_key not in conns:
                db_path = DB_PATHS[db_key]
                if not db_path.exists():
                    print(f"migrate: {db_path.name} absent — skipping {db_key} migrations")
                    conns[db_key] = None
                else:
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    _ensure_migrations_table(conn)
                    conns[db_key] = conn
                    done[db_key] = _applied(conn)

            conn = conns[db_key]
            if conn is None:
                print(f"migrate: ~ {name} (DB absent)")
                continue

            if name in done[db_key]:
                print(f"migrate: ~ {name}")
                continue

            print(f"migrate: applying {name} ({db_key}) …")
            mod.run(conn)
            conn.execute("INSERT INTO _migrations(name) VALUES (?)", (name,))
            conn.commit()
            done[db_key].add(name)
            print(f"migrate: + {name} done")

    except Exception as exc:
        print(f"migrate: ERROR — {exc}", file=sys.stderr)
        for c in conns.values():
            if c:
                c.close()
        sys.exit(1)

    for c in conns.values():
        if c:
            c.close()


if __name__ == "__main__":
    main()
