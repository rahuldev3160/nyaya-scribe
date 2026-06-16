"""Feature gating tables for freemium monetisation (nyaya.db)."""
DB = "nyaya"


def run(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS feature_gates (
            gate_id TEXT PRIMARY KEY,
            feature_name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_enabled_for_free INTEGER NOT NULL DEFAULT 0,
            is_enabled_for_pro INTEGER NOT NULL DEFAULT 1,
            quota_free INTEGER,
            quota_pro INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_feature_overrides (
            override_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            gate_id TEXT NOT NULL REFERENCES feature_gates(gate_id) ON DELETE CASCADE,
            granted_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT,
            reason TEXT,
            UNIQUE(user_id, gate_id)
        );

        CREATE TABLE IF NOT EXISTS user_feature_usage (
            user_id TEXT NOT NULL,
            gate_id TEXT NOT NULL,
            period TEXT NOT NULL,
            usage_count INTEGER NOT NULL DEFAULT 0,
            last_used_at TEXT,
            PRIMARY KEY (user_id, gate_id, period)
        );
    """)

    # Seed initial feature gates
    gates = [
        ("ai_scoring", "AI-powered answer evaluation", 1, 1, 15, None),
        ("model_answers_full", "Full PYQ library (pre-2022)", 0, 1, None, None),
        ("rubric_breakdown", "5-dimension rubric breakdown", 0, 1, None, None),
        ("photo_eval", "Handwritten answer photo evaluation", 0, 1, None, None),
        ("analytics", "Progress analytics and readiness score", 1, 1, None, None),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO feature_gates"
        " (gate_id, feature_name, is_enabled_for_free, is_enabled_for_pro, quota_free, quota_pro)"
        " VALUES (?,?,?,?,?,?)",
        gates,
    )
    conn.commit()
