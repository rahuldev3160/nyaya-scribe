"""Create cross-paper + CA tables in upsc_gs.db."""

DB = "upsc_gs"


def run(conn):
    conn.executescript("""

    -- Cross-paper concept linking (within upsc_gs.db + cross to upsc.db via Python-merge)
    CREATE TABLE IF NOT EXISTS topic_links (
        link_id         TEXT PRIMARY KEY,
        source_topic_id TEXT NOT NULL,
        source_paper_id TEXT NOT NULL,
        source_exam_id  TEXT NOT NULL DEFAULT 'upsc_gs_mains',
        target_topic_id TEXT NOT NULL,
        target_paper_id TEXT NOT NULL,
        target_exam_id  TEXT NOT NULL DEFAULT 'upsc_gs_mains',
        link_type       TEXT NOT NULL CHECK(link_type IN (
            'historical_origin','constitutional_basis','ethical_dimension',
            'policy_implementation','geo_economic_link','ir_domestic_nexus',
            'centre_state_fiscal','society_to_development','technology_policy'
        )),
        link_strength   REAL NOT NULL DEFAULT 0.5
            CHECK(link_strength >= 0.0 AND link_strength <= 1.0),
        link_note       TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        UNIQUE(source_topic_id, target_topic_id, link_type)
    );

    -- Normalised materialised view for bridge scoring
    CREATE TABLE IF NOT EXISTS bridge_topic_scores (
        topic_id            TEXT PRIMARY KEY,
        inbound_link_count  INTEGER DEFAULT 0,
        avg_link_strength   REAL DEFAULT 0.0,
        is_bridge           INTEGER DEFAULT 0
    );

    -- Current affairs events linked to GS topics
    CREATE TABLE IF NOT EXISTS ca_events (
        event_id            TEXT PRIMARY KEY,
        event_date          TEXT NOT NULL,
        headline            TEXT NOT NULL,
        event_summary       TEXT,
        source              TEXT NOT NULL CHECK(source IN (
            'PIB','Hindu','IE','LiveMint','MEA','RBI','NITI','PRS',
            'MoEFCC','ISRO','SupremeCourt','Mint','ET','Manual'
        )),
        source_url          TEXT,
        event_type          TEXT NOT NULL CHECK(event_type IN (
            'policy','legislation','judgment','international','environment',
            'science_tech','disaster','economic_data','governance','social'
        )),
        affected_gs_topics  TEXT,
        exam_relevance_tier INTEGER DEFAULT 2
            CHECK(exam_relevance_tier IN (1,2,3)),
        staleness_date      TEXT,
        staleness_reason    TEXT,
        is_stale            INTEGER DEFAULT 0,
        added_by            TEXT DEFAULT 'system',
        verified_at         TEXT,
        added_at            TEXT DEFAULT (datetime('now'))
    );

    -- Normalised CA↔topic junction for fast topic-based CA queries
    CREATE TABLE IF NOT EXISTS ca_topic_links (
        link_id         TEXT PRIMARY KEY,
        event_id        TEXT NOT NULL REFERENCES ca_events(event_id) ON DELETE CASCADE,
        paper_id        TEXT NOT NULL,
        topic_id        TEXT NOT NULL,
        relevance_score REAL DEFAULT 1.0,
        link_source     TEXT DEFAULT 'auto' CHECK(link_source IN ('auto','human'))
    );

    """)
    conn.commit()
