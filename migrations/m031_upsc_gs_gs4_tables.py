"""Create GS4 Ethics tables: concepts, keywords, thinkers, case study templates."""

DB = "upsc_gs"


def run(conn):
    conn.executescript("""

    -- Core ethics concepts (42 total at full seed)
    CREATE TABLE IF NOT EXISTS gs4_concepts (
        concept_id              TEXT PRIMARY KEY,
        concept_name            TEXT NOT NULL,
        concept_category        TEXT NOT NULL CHECK(concept_category IN (
            'theory','value','principle','cognitive','governance','social'
        )),
        formal_definition       TEXT,
        upsc_usage_pattern      TEXT,
        typical_question_angle  TEXT,
        prerequisite_concept_ids TEXT,
        related_thinker_ids     TEXT,
        cross_paper_topic_ids   TEXT,
        keyword_tags            TEXT,
        ask_frequency           TEXT DEFAULT 'medium' CHECK(ask_frequency IN ('high','medium','low')),
        centrality_score        REAL DEFAULT 0.5,
        is_foundational         INTEGER DEFAULT 0
    );

    -- Ethics keyword canonical forms (handles probity=integrity=uprightness)
    CREATE TABLE IF NOT EXISTS gs4_keywords (
        keyword_id      TEXT PRIMARY KEY,
        keyword_text    TEXT NOT NULL UNIQUE,
        canonical_form  TEXT NOT NULL,
        synonyms        TEXT,
        keyword_category TEXT CHECK(keyword_category IN (
            'value','virtue','principle','governance','psychological','philosophical','governance_term'
        )),
        concept_ids     TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    );

    -- Synonym resolution table
    CREATE TABLE IF NOT EXISTS gs4_keyword_synonyms (
        synonym_id          TEXT PRIMARY KEY,
        keyword_text        TEXT NOT NULL,
        canonical_keyword_id TEXT NOT NULL REFERENCES gs4_keywords(keyword_id),
        source              TEXT DEFAULT 'auto' CHECK(source IN ('auto','human'))
    );

    -- Junction: PYQ question ↔ GS4 keyword
    CREATE TABLE IF NOT EXISTS gs4_question_keywords (
        question_id     TEXT NOT NULL,
        keyword_id      TEXT NOT NULL REFERENCES gs4_keywords(keyword_id),
        relevance_score REAL DEFAULT 1.0,
        is_primary      INTEGER DEFAULT 0,
        PRIMARY KEY (question_id, keyword_id)
    );

    -- Top ethical thinkers with UPSC-specific angles
    CREATE TABLE IF NOT EXISTS gs4_thinkers (
        thinker_id                  TEXT PRIMARY KEY,
        name                        TEXT NOT NULL,
        era                         TEXT,
        school_of_thought           TEXT,
        key_works                   TEXT,
        core_concepts               TEXT,
        upsc_relevance_score        REAL DEFAULT 0.5,
        most_cited_quote            TEXT,
        typical_question_angle      TEXT,
        years_appeared              TEXT,
        concept_links               TEXT,
        indian_governance_application TEXT,
        common_mistake              TEXT
    );

    -- Case study scenario templates (10 types by UPSC frequency)
    CREATE TABLE IF NOT EXISTS gs4_case_study_templates (
        template_id             TEXT PRIMARY KEY,
        scenario_type           TEXT NOT NULL,
        scenario_description    TEXT NOT NULL,
        core_ethical_conflict   TEXT NOT NULL,
        recommended_frameworks  TEXT,
        answer_structure        TEXT,
        stakeholder_type_list   TEXT,
        common_dilemma_patterns TEXT,
        word_target             INTEGER DEFAULT 250,
        difficulty              TEXT DEFAULT 'medium' CHECK(difficulty IN ('easy','medium','hard')),
        upsc_frequency          INTEGER DEFAULT 0,
        last_appeared_year      INTEGER
    );

    -- Ethical reasoning frameworks (Consequentialism, Deontology, Virtue, etc.)
    CREATE TABLE IF NOT EXISTS gs4_ethical_frameworks (
        framework_id        TEXT PRIMARY KEY,
        framework_name      TEXT NOT NULL,
        framework_short     TEXT,
        key_principle       TEXT NOT NULL,
        upsc_usage_pattern  TEXT,
        answer_trigger      TEXT,
        thinker_ids         TEXT,
        upsc_relevance_score REAL DEFAULT 0.5,
        typical_question_type TEXT,
        common_pitfalls     TEXT
    );

    -- AI-generated practice case studies (5 per template × 10 templates = 50 at seed)
    CREATE TABLE IF NOT EXISTS practice_cases (
        case_id         TEXT PRIMARY KEY,
        case_source     TEXT DEFAULT 'ai_generated',
        template_id     TEXT NOT NULL REFERENCES gs4_case_study_templates(template_id),
        scenario_text   TEXT NOT NULL,
        word_count      INTEGER,
        question_parts  TEXT,
        concept_tags    TEXT,
        keyword_ids     TEXT,
        difficulty      TEXT DEFAULT 'medium',
        generation_model TEXT,
        model_answer    TEXT,
        rubric_json     TEXT,
        human_reviewed  INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now'))
    );

    """)

    # Seed core ethical frameworks
    frameworks = [
        ("ef_consequentialism", "Consequentialism / Utilitarianism", "Conseq.",
         "An act is right if it maximises overall happiness or welfare.",
         "Evaluate outcomes of policy decisions; justify trade-offs.",
         "When asked to compare benefits vs. harms; welfare schemes; cost-benefit analysis.",
         '["thinker_bentham","thinker_mill","thinker_singer"]', 0.90,
         "policy_evaluation", "Ignores rights of minorities; can justify harmful acts if aggregate good is high."),
        ("ef_deontology", "Deontological Ethics (Kantian)", "Deontology",
         "Act only according to the maxim you could will to become universal law.",
         "Duties, rights, and rules in governance; constitutional obligations.",
         "When asked about duty vs. outcome; Rights-based arguments; fundamental rights cases.",
         '["thinker_kant"]', 0.90,
         "duty_conflict", "Can be rigid; ignores consequences; difficult when duties conflict."),
        ("ef_virtue", "Virtue Ethics", "Virtue",
         "Focus on character and virtues (honesty, courage, justice) rather than rules or outcomes.",
         "Characterising a good civil servant; integrity-based evaluation.",
         "When asked what a person of good character would do; role model questions.",
         '["thinker_aristotle","thinker_gandhi"]', 0.85,
         "character_assessment", "Vague on specific actions; culturally relative virtues."),
        ("ef_care_ethics", "Ethics of Care", "Care",
         "Moral decisions should emphasise relationships, empathy, and context.",
         "Women, family, vulnerable groups; balancing duty with compassion.",
         "When empathy/compassion is explicitly asked; case studies involving personal obligations.",
         '[]', 0.65,
         "relational_dilemma", "Can be subjective; difficult to scale to policy level."),
        ("ef_rawls", "Rawlsian Justice (Veil of Ignorance)", "Rawls",
         "Just institutions are those chosen from behind a veil of ignorance about one's position.",
         "Reservation policy; welfare for the least advantaged; constitutional justice.",
         "When asked to design fair policies; evaluate social justice schemes.",
         '["thinker_rawls"]', 0.80,
         "distributive_justice", "Original position is hypothetical; may conflict with meritocracy."),
        ("ef_gandhian", "Gandhian Ethics", "Gandhian",
         "Truth (Satya) and non-violence (Ahimsa) are means and ends inseparably linked.",
         "Civil service values; peaceful protest; trusteeship of public resources.",
         "When asked about means vs. ends; corruption; civil service values; public trust.",
         '["thinker_gandhi"]', 0.95,
         "means_ends", "Idealistic in adversarial situations; may not address systemic issues."),
    ]

    for (fid, fname, fshort, key_principle, usage, trigger, thinkers, score, qtype, pitfalls) in frameworks:
        conn.execute("""
            INSERT OR IGNORE INTO gs4_ethical_frameworks
            (framework_id, framework_name, framework_short, key_principle, upsc_usage_pattern,
             answer_trigger, thinker_ids, upsc_relevance_score, typical_question_type, common_pitfalls)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (fid, fname, fshort, key_principle, usage, trigger, thinkers, score, qtype, pitfalls))

    conn.commit()
