"""
Prototype: Generate 1 diagram of each type (flowchart, SVG curve, HTML table)
and save output to exports/prototype_diagrams.json for rendering test.

Run: python3 scripts/prototype_diagrams.py
Then open the test page: streamlit run web/pages/99_Diagram_Test.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "web"))

import anthropic

API_KEY_PATH = Path.home() / "Desktop" / "Claude Projects" / "Devthorium" / ".env"
def load_api_key():
    for line in API_KEY_PATH.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise ValueError("ANTHROPIC_API_KEY not found")


# ── 3 Hardcoded prototype samples (from diagnostic) ─────────────────────────

SAMPLES = [
    {
        "id": "flowchart_stolper_samuelson",
        "diagram_format": "mermaid",
        "diagram_type": "flow_chart",
        "question": "State and prove the Stolper-Samuelson Theorem in international trade. What is the magnification effect?",
        "diagram_description": """Flow Chart: Stolper-Samuelson Causal Chain

Box 1 [TOP]: 'Trade Liberalization / Tariff Reduction'
↓ Arrow labeled 'changes relative commodity prices'
Box 2: 'Rise in Px (price of labor-intensive good X)'
↓ Arrow labeled 'zero-profit condition + CRS'
Box 3: 'Expansion of sector X → increased demand for Labor'
↓ Arrow (left branch) and ↓ Arrow (right branch)
Box 4a [LEFT]: 'Wage (w) rises MORE than proportionately → ŵ > P̂x' [labeled: MAGNIFICATION EFFECT — winners: Labor]
Box 4b [RIGHT]: 'Rental rate (r) falls absolutely → r̂ < 0 < P̂y' [labeled: MAGNIFICATION EFFECT — losers: Capital]
↓ Both arrows converge to:
Box 5 [BOTTOM]: 'Income Redistribution: Factor Price Equalization tendency; Magnification Ordering: ŵ > P̂x > P̂y > r̂'""",
    },
    {
        "id": "svg_demand_supply",
        "diagram_format": "svg",
        "diagram_type": "demand_supply_curve",
        "question": "Demand function for good X with advertisement outlay. What is the percentage change in demand if advertisement outlay increases by 50%?",
        "diagram_description": """The diagram shows the effect of increased advertisement outlay on demand for good X.
X-axis: Quantity Demanded of good X (Dx).
Y-axis: Price of good X (Px).
Two downward-sloping demand curves: D1 (original demand curve before advertisement increase) and D2 (new demand curve after 50% increase in advertisement outlay, shifted rightward).
At price P0, quantity demanded increases from Q1 (on D1) to Q2 (on D2) — a 20% increase.
Supply curve S is upward-sloping, intersects D1 at E1 (P1, Q1) and D2 at E2 (P2, Q2).
Arrow labeled '+20% ΔDx' marks the horizontal distance between the two curves at P0.
Key labels: X-axis = Quantity of X (Dx); Y-axis = Price (Px); Curves = D1, D2, S; Points = E1, E2.""",
    },
    {
        "id": "html_internal_external_debt",
        "diagram_format": "html",
        "diagram_type": "table",
        "question": "Distinguish between internal and external public debt. Explain the debate on burden of public debt.",
        "diagram_description": """Comparative Table — Internal vs External Public Debt Burden

Columns: [Dimension | Internal Public Debt | External Public Debt]
Rows:
1. Source of funds | Domestic residents, banks, RBI | Foreign governments, multilateral agencies, ECBs
2. Currency denomination | Indian Rupee (₹) | Primarily USD (54.2%), Euro, SDR
3. Nature of burden | Transfer payment (redistribution within nation) | Real resource outflow (genuine burden on national economy)
4. Crowding-out risk | High — competes with private sector for loanable funds | Moderate — adds forex demand pressure
5. Intergenerational burden | Present consumption vs future taxation | Future generations must generate export surplus to repay
6. Sovereignty risk | Nil | High — conditionalities possible (IMF, World Bank)
7. India's share (2025-26) | 96.59% of ₹18,174,284 crore | 3.41% of ₹18,174,284 crore
8. Key instruments | G-Secs, T-Bills, dated securities | ECBs, Masala Bonds, multilateral loans

Footer note: 'Classical economists treated internal debt as no burden (intra-national transfer); external debt always constitutes real burden. Modern debate (Ricardian Equivalence, Domar's sustainability condition g>r) qualifies both positions.'""",
    },
]


MERMAID_PROMPT = """You are a Mermaid diagram code generator for an economics study web app (dark theme).
Convert the diagram description into valid Mermaid flowchart code.

Rules:
- Use `flowchart TD` (top-down) syntax
- Node labels max 12 words — split long labels across lines using <br/> inside quotes
- For left/right splits use subgraph or parallel branches
- Escape special characters: use plain ASCII for arrows/labels
- No external links, no click events
- Return ONLY the raw Mermaid code — no markdown fence, no explanation

Diagram description:
{description}"""


SVG_PROMPT = """You are an SVG diagram generator for an economics textbook (dark web theme, background #1C1C1E).
Create a clean SVG diagram based on this description.

Technical requirements:
- viewBox="0 0 520 380"
- Background rect fill="#1C1C1E"
- Axes: white lines, arrows at tips, labeled at ends (font: Arial 13px, fill white)
- Downward-sloping demand curves: smooth quadratic bezier, stroke="#8AB4F8" (blue), strokeWidth 2.5
- Upward-sloping supply curve: stroke="#81C995" (green), strokeWidth 2.5
- Shifted curves (D2, S2): same color but stroke-dasharray="6,3" for dashed lines
- Intersection points: white filled circles radius 5
- Labels for all curves, points, axes: white text, 12px, positioned clearly so they don't overlap
- Horizontal/vertical dotted reference lines: stroke rgba(255,255,255,0.25), dasharray 4,4
- A small legend box in top-right corner listing all curves

Return ONLY the SVG element (start with <svg, end with </svg>). No explanation, no markdown.

Diagram description:
{description}"""


HTML_TABLE_PROMPT = """You are an HTML table generator for an economics study app (dark Gemini theme).
Convert this table description into a clean, styled HTML table.

Requirements:
- Self-contained <table> element with inline styles only (no external CSS)
- Dark theme: table background transparent, header row background #2d2f31, alternating row shading rgba(255,255,255,0.04)
- First column (Dimension) background #1e2022, bold, color #8AB4F8
- Header row: color #E8EAED, font-weight 700, border-bottom 2px solid rgba(138,180,248,0.4)
- Cell padding 10px 14px, font-size 0.88rem, color #C9CACE
- Outer border: 1px solid rgba(255,255,255,0.12), border-radius 8px, overflow hidden — wrap in a div
- Add a <tfoot> row spanning all columns for any footer/analytical note, italic, color #9AA0A6
- Numbers/percentages: color #FDD663 (yellow)
- Return ONLY the outer <div>...</div> wrapping the table. No explanation, no markdown.

Table description:
{description}"""


def generate_diagram_code(client: anthropic.Anthropic, sample: dict) -> dict:
    fmt = sample["diagram_format"]
    desc = sample["diagram_description"]

    if fmt == "mermaid":
        prompt = MERMAID_PROMPT.format(description=desc)
    elif fmt == "svg":
        prompt = SVG_PROMPT.format(description=desc)
    else:  # html
        prompt = HTML_TABLE_PROMPT.format(description=desc)

    print(f"  Generating {fmt} for: {sample['id']} ...", end="", flush=True)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    code = response.content[0].text.strip()

    # Strip accidental markdown fences if model added them
    if fmt == "mermaid" and code.startswith("```"):
        lines = code.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        code = "\n".join(lines).strip()

    print(f" done ({len(code)} chars)")

    return {
        "id": sample["id"],
        "question": sample["question"],
        "diagram_format": fmt,
        "diagram_type": sample["diagram_type"],
        "diagram_description": sample["diagram_description"],
        "generated_code": code,
    }


if __name__ == "__main__":
    client = anthropic.Anthropic(api_key=load_api_key())
    results = []

    print("Generating prototype diagrams (3 total)...")
    for sample in SAMPLES:
        result = generate_diagram_code(client, sample)
        results.append(result)

    out_path = Path(__file__).parent.parent / "exports" / "prototype_diagrams.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nSaved to {out_path}")
    print("Now run:  /Users/rahulsingh/Library/Python/3.9/bin/streamlit run web/pages/99_Diagram_Test.py")
