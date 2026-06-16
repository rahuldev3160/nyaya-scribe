"""Create GS3 auxiliary tables: perishable economic data, environment, security frameworks."""

DB = "upsc_gs"


def run(conn):
    conn.executescript("""

    -- Perishable Budget numbers — stale after next Budget presentation
    CREATE TABLE IF NOT EXISTS budget_snapshots (
        snapshot_id     TEXT PRIMARY KEY,
        budget_year     INTEGER NOT NULL,
        line_item       TEXT NOT NULL,
        value           TEXT NOT NULL,
        gs3_topic_id    TEXT,
        source_doc      TEXT,
        updated_at      TEXT DEFAULT (datetime('now'))
    );

    -- Live economic indicators — triggers model answer staleness warnings
    CREATE TABLE IF NOT EXISTS economic_indicators (
        indicator_id    TEXT PRIMARY KEY,
        indicator_name  TEXT NOT NULL,
        current_value   TEXT,
        target_value    TEXT,
        as_of_date      TEXT,
        source          TEXT,
        gs3_topic_id    TEXT,
        is_stale        INTEGER DEFAULT 0,
        placeholder_token TEXT
    );

    -- Environmental conventions (permanent, but COPs update outcomes)
    CREATE TABLE IF NOT EXISTS env_conventions (
        convention_id   TEXT PRIMARY KEY,
        full_name       TEXT NOT NULL,
        year_adopted    INTEGER,
        india_signatory INTEGER DEFAULT 1,
        key_provisions  TEXT,
        india_commitments TEXT,
        last_cop        TEXT,
        cop_outcomes    TEXT,
        upsc_frequency  TEXT DEFAULT 'medium' CHECK(upsc_frequency IN ('high','medium','low')),
        ca_sensitivity  TEXT DEFAULT 'medium' CHECK(ca_sensitivity IN ('static','ca_light','ca_heavy')),
        updated_at      TEXT DEFAULT (datetime('now'))
    );

    -- Protected areas and biodiversity hotspots (GS3 Environment)
    CREATE TABLE IF NOT EXISTS protected_areas (
        pa_id           TEXT PRIMARY KEY,
        pa_name         TEXT NOT NULL,
        pa_type         TEXT CHECK(pa_type IN ('national_park','wildlife_sanctuary','biosphere_reserve',
                                               'tiger_reserve','ramsar_site','world_heritage')),
        state           TEXT,
        hotspot         TEXT,
        area_sqkm       REAL,
        key_species     TEXT,
        gs3_relevance   TEXT DEFAULT 'medium',
        upsc_asked      INTEGER DEFAULT 0
    );

    -- S&T topic version tracking — for fast-moving tech (AI, Space, Bio)
    CREATE TABLE IF NOT EXISTS tech_topic_versions (
        version_id      TEXT PRIMARY KEY,
        topic_id        TEXT NOT NULL,
        version_date    TEXT NOT NULL,
        tech_snapshot   TEXT NOT NULL,
        is_superseded   INTEGER DEFAULT 0,
        superseded_by   TEXT
    );

    -- Internal security legislative frameworks
    CREATE TABLE IF NOT EXISTS security_frameworks (
        framework_id        TEXT PRIMARY KEY,
        full_name           TEXT NOT NULL,
        enacted_year        INTEGER,
        key_provisions      TEXT,
        nodal_agency        TEXT,
        current_status      TEXT CHECK(current_status IN ('in_force','amended','repealed','proposed')),
        lwe_relevance       INTEGER DEFAULT 0,
        cyber_relevance     INTEGER DEFAULT 0,
        border_relevance    INTEGER DEFAULT 0,
        upsc_frequency      TEXT DEFAULT 'medium' CHECK(upsc_frequency IN ('high','medium','low')),
        last_updated        TEXT DEFAULT (datetime('now'))
    );

    """)
    conn.commit()
