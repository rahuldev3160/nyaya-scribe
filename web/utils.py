"""Keyword-based combined search utility for ethics and essay modules."""

KNOWN_CONCEPTS: set[str] = {
    "integrity", "probity", "honesty", "aptitude", "attitude",
    "accountability", "transparency", "emotional intelligence", "corruption",
    "governance", "constitutional morality", "conflict of interest", "conscience",
    "gender", "environmental ethics", "digital ethics", "social media ethics",
    "whistleblowing", "rti", "laws", "ethics", "code of conduct",
    "international relations", "good governance", "civil service values",
    "dedication", "impartiality", "objectivity", "empathy", "compassion",
    "tolerance", "perseverance", "public service", "moral philosophy",
    "virtue ethics", "utilitarianism", "karma yoga", "duty",
    "foundational values", "human values",
}

KNOWN_THINKERS: set[str] = {
    "gandhi", "vivekananda", "kalam", "aristotle", "socrates", "kant",
    "lincoln", "dalai lama", "thiruvalluvar", "ambedkar", "chanakya",
    "buddha", "guru nanak", "mahavira", "tagore", "iqbal", "goleman",
    "rawls", "plato", "mill", "bentham", "emerson", "sun tzu",
}

KNOWN_SCENARIOS: set[str] = {
    "hierarchical pressure", "corruption", "whistleblowing", "duty",
    "compassion", "gender discrimination", "private sector",
    "development environment", "disaster", "conflict of interest",
    "international", "child labour", "law enforcement",
}

ESSAY_THEMES: set[str] = {
    "values ethics", "technology", "gender justice", "education", "economy",
    "governance", "nature environment", "philosophy", "democracy", "geopolitics",
    "strategic autonomy", "development inequality", "media democracy",
    "science aspiration", "social justice", "digital inequality", "federalism",
}

# Multi-word phrases matched before single-token lookup, longest first.
_MULTI_WORD_PHRASES: list[tuple[str, str, str]] = sorted(
    [
        # (phrase_lower, field, value)
        ("section a",              "section",      "A"),
        ("section b",              "section",      "B"),
        ("high priority",          "high_priority", True),
        ("past year",              "content_type", "pyq"),
        ("emotional intelligence", "concept",      "emotional intelligence"),
        ("conflict of interest",   "concept",      "conflict of interest"),
        ("constitutional morality","concept",      "constitutional morality"),
        ("environmental ethics",   "concept",      "environmental ethics"),
        ("digital ethics",         "concept",      "digital ethics"),
        ("social media ethics",    "concept",      "social media ethics"),
        ("civil service values",   "concept",      "civil service values"),
        ("good governance",        "concept",      "good governance"),
        ("moral philosophy",       "concept",      "moral philosophy"),
        ("virtue ethics",          "concept",      "virtue ethics"),
        ("karma yoga",             "concept",      "karma yoga"),
        ("foundational values",    "concept",      "foundational values"),
        ("human values",           "concept",      "human values"),
        ("public service",         "concept",      "public service"),
        ("code of conduct",        "concept",      "code of conduct"),
        ("international relations","concept",      "international relations"),
        ("gender discrimination",  "scenario",     "gender discrimination"),
        ("hierarchical pressure",  "scenario",     "hierarchical pressure"),
        ("private sector",         "scenario",     "private sector"),
        ("development environment","scenario",     "development environment"),
        ("conflict of interest",   "scenario",     "conflict of interest"),
        ("child labour",           "scenario",     "child labour"),
        ("law enforcement",        "scenario",     "law enforcement"),
        ("dalai lama",             "thinker",      "dalai lama"),
        ("guru nanak",             "thinker",      "guru nanak"),
        ("sun tzu",                "thinker",      "sun tzu"),
        ("values ethics",          "theme",        "values ethics"),
        ("gender justice",         "theme",        "gender justice"),
        ("nature environment",     "theme",        "nature environment"),
        ("strategic autonomy",     "theme",        "strategic autonomy"),
        ("development inequality", "theme",        "development inequality"),
        ("media democracy",        "theme",        "media democracy"),
        ("science aspiration",     "theme",        "science aspiration"),
        ("social justice",         "theme",        "social justice"),
        ("digital inequality",     "theme",        "digital inequality"),
    ],
    key=lambda t: len(t[0]),
    reverse=True,
)


def parse_search(q: str, module: str) -> dict:
    """Classify raw search string into filter dict for ethics or essay module."""
    text = q.lower().strip()
    filters: dict = {
        "year": None,
        "section": None,
        "concepts": [],
        "thinkers": [],
        "scenarios": [],
        "themes": [],
        "marks": None,
        "content_type": None,
        "high_priority": False,
        "fts_fallback": None,
    }

    consumed: set[int] = set()

    def _consume(start: int, length: int) -> None:
        for i in range(start, start + length):
            consumed.add(i)

    # Step 1 — multi-word phrases (longest first, character-position scan)
    for phrase, field, value in _MULTI_WORD_PHRASES:
        idx = text.find(phrase)
        while idx != -1:
            span = set(range(idx, idx + len(phrase)))
            if not span & consumed:
                _consume(idx, len(phrase))
                if field == "section":
                    filters["section"] = value
                elif field == "high_priority":
                    filters["high_priority"] = True
                elif field == "content_type":
                    filters["content_type"] = value
                elif field == "concept":
                    if value not in filters["concepts"]:
                        filters["concepts"].append(value)
                elif field == "scenario":
                    if value not in filters["scenarios"]:
                        filters["scenarios"].append(value)
                elif field == "thinker":
                    if value not in filters["thinkers"]:
                        filters["thinkers"].append(value)
                elif field == "theme":
                    if value not in filters["themes"]:
                        filters["themes"].append(value)
            idx = text.find(phrase, idx + 1)

    # Rebuild remaining text from unconsumed characters
    remaining = "".join(
        ch for i, ch in enumerate(text) if i not in consumed
    ).strip()

    tokens = remaining.split()
    leftover: list[str] = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        # Step 2 — year
        if tok.isdigit() and len(tok) == 4 and 2013 <= int(tok) <= 2026:
            filters["year"] = int(tok)
            i += 1
            continue

        # Step 3 — marks: "10marks" or "10 marks"
        marks_candidate = tok.rstrip("marks").strip()
        if marks_candidate.isdigit():
            if tok.endswith("marks") or (
                i + 1 < len(tokens) and tokens[i + 1] == "marks"
            ):
                filters["marks"] = int(marks_candidate)
                if i + 1 < len(tokens) and tokens[i + 1] == "marks":
                    i += 2
                else:
                    i += 1
                continue

        # Step 4 — content type
        if tok == "pyq":
            filters["content_type"] = "pyq"
            i += 1
            continue
        if tok == "practice":
            filters["content_type"] = "practice"
            i += 1
            continue

        # Step 5 — section (standalone single letter only)
        if tok == "a" and filters["section"] is None:
            filters["section"] = "A"
            i += 1
            continue
        if tok == "b" and filters["section"] is None:
            filters["section"] = "B"
            i += 1
            continue

        # Step 6 — single-word concept / thinker / scenario / theme
        if tok in KNOWN_CONCEPTS:
            if tok not in filters["concepts"]:
                filters["concepts"].append(tok)
            i += 1
            continue
        if tok in KNOWN_THINKERS:
            if tok not in filters["thinkers"]:
                filters["thinkers"].append(tok)
            i += 1
            continue
        if tok in KNOWN_SCENARIOS:
            if tok not in filters["scenarios"]:
                filters["scenarios"].append(tok)
            i += 1
            continue
        if tok in ESSAY_THEMES:
            if tok not in filters["themes"]:
                filters["themes"].append(tok)
            i += 1
            continue

        leftover.append(tok)
        i += 1

    if leftover:
        filters["fts_fallback"] = " ".join(leftover)

    return filters


def build_query(filters: dict, module: str) -> tuple[str, list]:
    """Assemble parameterized SQL query and params list from filter dict."""
    params: list = []

    if module == "ethics":
        joins: list[str] = []
        wheres: list[str] = []

        for idx, concept in enumerate(filters.get("concepts", [])):
            alias = f"ecl{idx}"
            joins.append(
                f"JOIN ethics_concept_links {alias} "
                f"ON {alias}.question_id = eq.question_id AND {alias}.concept_tag = ?"
            )
            params.append(concept)

        for idx, thinker in enumerate(filters.get("thinkers", [])):
            alias = f"etl{idx}"
            joins.append(
                f"JOIN ethics_thinker_links {alias} "
                f"ON {alias}.question_id = eq.question_id AND {alias}.thinker_id = ?"
            )
            params.append(thinker)

        for idx, scenario in enumerate(filters.get("scenarios", [])):
            alias = f"esl{idx}"
            joins.append(
                f"JOIN ethics_scenario_links {alias} "
                f"ON {alias}.question_id = eq.question_id AND {alias}.scenario_type = ?"
            )
            params.append(scenario)

        if filters.get("fts_fallback"):
            joins.append(
                "JOIN ethics_fts ON ethics_fts.question_id = eq.question_id"
            )
            wheres.append("ethics_fts MATCH ?")
            params.append(filters["fts_fallback"])

        if filters.get("year") is not None:
            wheres.append("eq.paper_year = ?")
            params.append(filters["year"])

        if filters.get("section") is not None:
            wheres.append("eq.section = ?")
            params.append(filters["section"])

        if filters.get("marks") is not None:
            wheres.append("eq.marks = ?")
            params.append(filters["marks"])

        if filters.get("content_type") is not None:
            wheres.append("eq.content_type = ?")
            params.append(filters["content_type"])

        sql = "SELECT eq.* FROM ethics_questions eq"
        if joins:
            sql += "\n" + "\n".join(joins)
        if wheres:
            sql += "\nWHERE " + " AND ".join(wheres)
        sql += "\nORDER BY eq.paper_year DESC, eq.section, eq.sequence_order"

        return sql, params

    # module == "essay"
    joins = []
    wheres = []
    theme_wheres: list[str] = []

    for idx, thinker in enumerate(filters.get("thinkers", [])):
        alias = f"etl{idx}"
        joins.append(
            f"JOIN essay_thinker_links {alias} "
            f"ON {alias}.essay_id = eq.essay_id AND {alias}.thinker_id = ?"
        )
        params.append(thinker)

    if filters.get("fts_fallback"):
        joins.append("JOIN essay_fts ON essay_fts.essay_id = eq.essay_id")
        wheres.append("essay_fts MATCH ?")
        params.append(filters["fts_fallback"])

    if filters.get("year") is not None:
        wheres.append("eq.year_appeared = ?")
        params.append(filters["year"])

    if filters.get("section") is not None:
        wheres.append("eq.section = ?")
        params.append(filters["section"])

    if filters.get("content_type") is not None:
        wheres.append("eq.content_type = ?")
        params.append(filters["content_type"])

    if filters.get("high_priority"):
        wheres.append("eq.is_high_probability = 1")

    # Themes use OR logic among themselves, AND with everything else
    for theme in filters.get("themes", []):
        theme_wheres.append("eq.theme_tag = ?")
        params.append(theme)

    sql = "SELECT eq.* FROM essay_questions eq"
    if joins:
        sql += "\n" + "\n".join(joins)

    all_wheres = list(wheres)
    if theme_wheres:
        all_wheres.append("(" + " OR ".join(theme_wheres) + ")")

    if all_wheres:
        sql += "\nWHERE " + " AND ".join(all_wheres)

    sql += "\nORDER BY eq.year_appeared DESC NULLS LAST, eq.section, eq.essay_id"

    return sql, params
