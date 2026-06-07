"""INSERT OR REPLACE english_question_types so content changes in the Python seed propagate to existing DBs."""
DB = "ies"

_EXAM_ID = "english_practice"

_SEED_DATA = [
    ("essay",   "Essay",                  "Extended analytical prose on a given topic.",                                                                          '{"intro":"Introduction","body":"Body","conclusion":"Conclusion"}', '{"intro":0.15,"body":0.70,"conclusion":0.15}', "essay",  1),
    ("précis",  "Précis Writing",         "Compress a passage to 1/3 length. Title in Intro, précis text in Body. Third person, no lifted phrases.",               '{"intro":"Title","body":"Précis","conclusion":""}',               '{"intro":0.10,"body":0.85,"conclusion":0.05}', "précis", 2),
    ("rc",      "Reading Comprehension",  "Answer a question based on the passage. Direct answer first. Passage content only — no external knowledge.",            '{"intro":"Answer","body":"Evidence","conclusion":"Inference"}',    '{"intro":0.20,"body":0.60,"conclusion":0.20}', "rc",     3),
    ("letter",  "Letter Writing",         "Formal letter: salutation, body paragraphs, proper closing. One of three options.",                                     '{"intro":"Opening","body":"Body","conclusion":"Closing"}',         '{"intro":0.15,"body":0.70,"conclusion":0.15}', "letter", 4),
    ("report",  "Report Writing",         "Official report: To/From/Date/Subject header, factual body, clear recommendations. Concise, no personal opinion.",      '{"intro":"Header","body":"Body","conclusion":"Recommendations"}',   '{"intro":0.15,"body":0.70,"conclusion":0.15}', "report", 5),
]


def run(conn):
    # INSERT OR REPLACE so content changes in the Python seed propagate to existing DBs
    conn.executemany(
        "INSERT OR REPLACE INTO english_question_types "
        "(type_id, type_name, description, section_labels_json, section_weights_json, rubric_type, sort_order, exam_id) "
        "VALUES (?,?,?,?,?,?,?,?)",
        [(*row, _EXAM_ID) for row in _SEED_DATA],
    )
    conn.commit()
