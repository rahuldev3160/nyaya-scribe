"""Ethics module core tables: questions, practice papers, concept/scenario analysis, junction tables, FTS5."""

DB = "upsc_gs"


def run(conn):
    conn.executescript("""

    CREATE TABLE IF NOT EXISTS ethics_questions (
        question_id     TEXT PRIMARY KEY,
        paper_year      INTEGER,
        paper_id        TEXT,
        section         TEXT NOT NULL CHECK(section IN ('A','B')),
        question_type   TEXT NOT NULL CHECK(question_type IN ('definition','short','medium','analytical','case_study')),
        question_text   TEXT NOT NULL,
        case_preamble   TEXT,
        sub_part        TEXT,
        marks           INTEGER NOT NULL,
        content_type    TEXT NOT NULL DEFAULT 'pyq' CHECK(content_type IN ('pyq','practice')),
        concept_tags    TEXT,
        thinker_tags    TEXT,
        framework_hint  TEXT CHECK(framework_hint IN ('IDEA-U','STAKE','IDEA-U-extended')),
        sequence_order  INTEGER,
        created_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS ethics_practice_papers (
        paper_id        TEXT PRIMARY KEY,
        paper_title     TEXT NOT NULL,
        generation_year INTEGER NOT NULL,
        section_a_marks INTEGER DEFAULT 125,
        section_b_marks INTEGER DEFAULT 125,
        total_marks     INTEGER DEFAULT 250,
        time_minutes    INTEGER DEFAULT 180,
        difficulty      TEXT CHECK(difficulty IN ('easy','medium','hard')),
        theme_focus     TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS ethics_concept_analysis (
        concept_tag         TEXT PRIMARY KEY,
        concept_label       TEXT NOT NULL,
        frequency_count     INTEGER NOT NULL,
        section_preference  TEXT,
        year_appearances    TEXT,
        typical_marks       TEXT,
        linked_thinkers     TEXT,
        linked_frameworks   TEXT,
        example_question    TEXT,
        fy26_probability    TEXT CHECK(fy26_probability IN ('high','medium','low')),
        trend               TEXT CHECK(trend IN ('rising','stable','declining')),
        last_updated        TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS ethics_scenario_analysis (
        scenario_type           TEXT PRIMARY KEY,
        scenario_label          TEXT NOT NULL,
        frequency_count         INTEGER NOT NULL,
        year_appearances        TEXT,
        typical_role            TEXT,
        core_dilemma_type       TEXT,
        recommended_framework   TEXT,
        fy26_probability        TEXT CHECK(fy26_probability IN ('high','medium','low')),
        example_preamble        TEXT,
        last_updated            TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS ethics_concept_links (
        link_id     TEXT PRIMARY KEY,
        question_id TEXT NOT NULL REFERENCES ethics_questions(question_id) ON DELETE CASCADE,
        concept_tag TEXT NOT NULL REFERENCES ethics_concept_analysis(concept_tag),
        is_primary  INTEGER DEFAULT 1,
        UNIQUE(question_id, concept_tag)
    );

    CREATE TABLE IF NOT EXISTS ethics_thinker_links (
        link_id     TEXT PRIMARY KEY,
        question_id TEXT NOT NULL REFERENCES ethics_questions(question_id) ON DELETE CASCADE,
        thinker_id  TEXT NOT NULL REFERENCES gs4_thinkers(thinker_id),
        usage_type  TEXT CHECK(usage_type IN ('cited','quoted','implicit')),
        UNIQUE(question_id, thinker_id)
    );

    CREATE TABLE IF NOT EXISTS ethics_scenario_links (
        link_id       TEXT PRIMARY KEY,
        question_id   TEXT NOT NULL REFERENCES ethics_questions(question_id) ON DELETE CASCADE,
        scenario_type TEXT NOT NULL REFERENCES ethics_scenario_analysis(scenario_type),
        is_primary    INTEGER DEFAULT 1,
        UNIQUE(question_id, scenario_type)
    );

    CREATE INDEX IF NOT EXISTS idx_ethics_year    ON ethics_questions(paper_year);
    CREATE INDEX IF NOT EXISTS idx_ethics_section ON ethics_questions(section);
    CREATE INDEX IF NOT EXISTS idx_ethics_type    ON ethics_questions(question_type);
    CREATE INDEX IF NOT EXISTS idx_ethics_paper   ON ethics_questions(paper_id, sequence_order);
    CREATE INDEX IF NOT EXISTS idx_ethics_content ON ethics_questions(content_type, paper_year);
    CREATE INDEX IF NOT EXISTS idx_ethics_subpart ON ethics_questions(paper_id, section, sub_part);

    CREATE VIRTUAL TABLE IF NOT EXISTS ethics_fts USING fts5(
        question_id UNINDEXED,
        question_text,
        case_preamble,
        content='ethics_questions',
        content_rowid='rowid'
    );

    """)

    conn.commit()
