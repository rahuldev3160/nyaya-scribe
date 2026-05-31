"""
Export IES PYQ + model answers from SQLite to clean plain text per paper.
Output goes to sources/<paper_id>/IES_PYQ_Answers_<paper>.txt
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "ies.db"
OUT = Path(__file__).parent.parent / "sources"

PAPER_NAMES = {
    "ge_01": "GE-01: General Economics I — Micro & Macro",
    "ge_02": "GE-02: General Economics II — Growth, Trade & Money",
    "ge_03": "GE-03: General Economics III — Indian Economy",
    "ge_04": "GE-04: General Economics IV — Economic Policy",
}

TOPIC_DISPLAY = {
    "consumers_demand": "Theory of Consumer's Demand",
    "theory_of_production": "Theory of Production",
    "theory_of_value": "Theory of Value",
    "theory_of_distribution": "Theory of Distribution",
    "welfare_economics": "Welfare Economics",
    "mathematical_methods": "Mathematical Methods in Economics",
    "statistical_econometric_methods": "Statistical and Econometric Methods",
    "economic_growth_development": "Economic Growth and Development",
    "employment_output_inflation_money": "Employment, Output, Inflation and Money",
    "financial_capital_market": "Financial and Capital Markets",
    "international_economics": "International Economics",
    "balance_of_payments": "Balance of Payments",
    "economic_thought": "History of Economic Thought",
    "national_income_accounting": "National Income Accounting",
    "global_institutions": "Global Institutions",
    "environmental_economics": "Environmental and Natural Resource Economics",
    "industrial_economics": "Industrial Economics",
    "public_finance": "Public Finance",
    "state_market_planning": "State, Market and Planning",
    "agriculture_rural_development": "Agriculture and Rural Development",
    "poverty_unemployment_hd": "Poverty, Unemployment and Human Development",
    "money_banking_india": "Money and Banking in India",
    "budgeting_fiscal_policy_india": "Budgeting and Fiscal Policy in India",
    "foreign_trade_india": "Foreign Trade and Balance of Payments",
    "industry_india": "Industry and Services",
    "development_planning_history": "Development Planning and Economic History",
    "labour_india": "Labour and Employment",
    "inflation_india": "Inflation in India",
    "federal_finance": "Federal Finance",
    "urbanisation_migration": "Urbanisation and Migration",
}

def clean(text: str) -> str:
    if not text:
        return ""
    return text.strip()

def export_paper(conn: sqlite3.Connection, paper_id: str):
    paper_name = PAPER_NAMES[paper_id]
    out_path = OUT / paper_id / f"IES_PYQ_Answers_{paper_id.upper()}.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = conn.execute("""
        SELECT
            q.year, q.topic_id, q.subtopic_id, q.marks,
            q.question_text, q.key_concepts,
            a.intro_text, a.body_text, a.conclusion_text,
            a.key_terms_used, a.diagram_description
        FROM pyq_questions q
        JOIN model_answers a ON q.question_id = a.question_id AND q.exam_id = a.exam_id
        WHERE q.paper_id = ? AND q.exam_id = 'ies_2026'
        ORDER BY q.topic_id, q.year
    """, (paper_id,)).fetchall()

    lines = []
    lines.append(f"IES GENERAL ECONOMICS — {paper_name}")
    lines.append(f"Past Year Questions with Model Answers (2010-2025)")
    lines.append(f"Total Questions: {len(rows)}")
    lines.append("=" * 70)
    lines.append("")

    current_topic = None
    for row in rows:
        year, topic_id, subtopic_id, marks, q_text, key_concepts, \
            intro, body, conclusion, key_terms, diagram_desc = row

        topic_display = TOPIC_DISPLAY.get(topic_id, topic_id.replace("_", " ").title())

        if topic_id != current_topic:
            current_topic = topic_id
            lines.append("")
            lines.append(f"TOPIC: {topic_display}")
            lines.append("-" * 50)
            lines.append("")

        lines.append(f"[IES {year} | {marks} marks]")
        lines.append(f"Question: {clean(q_text)}")
        lines.append("")
        lines.append("Model Answer:")
        if clean(intro):
            lines.append(f"Introduction: {clean(intro)}")
        if clean(body):
            lines.append(f"Body: {clean(body)}")
        if clean(conclusion):
            lines.append(f"Conclusion: {clean(conclusion)}")
        if clean(diagram_desc):
            lines.append(f"Diagram: {clean(diagram_desc)}")
        if clean(key_terms):
            lines.append(f"Key Terms: {clean(key_terms)}")
        lines.append("")
        lines.append("---")
        lines.append("")

    content = "\n".join(lines)
    out_path.write_text(content, encoding="utf-8")

    size_kb = out_path.stat().st_size // 1024
    print(f"  {paper_id.upper()}: {len(rows)} questions → {out_path.name} ({size_kb} KB)")
    return len(rows)

def main():
    conn = sqlite3.connect(DB)
    print("Exporting IES PYQ + model answers for NotebookLM upload...\n")
    total = 0
    for paper_id in ["ge_01", "ge_02", "ge_03", "ge_04"]:
        total += export_paper(conn, paper_id)
    conn.close()
    print(f"\nDone. {total} questions exported across 4 papers.")
    print(f"Files saved to: sources/<paper>/IES_PYQ_Answers_<PAPER>.txt")

if __name__ == "__main__":
    main()
