"""
Generate podcast RSS feed for IES 2026 General Economics audio series.
Reads MP3 files from data/audio/ and produces a valid podcast RSS XML
that can be submitted to Spotify for Podcasters, Apple Podcasts, etc.

Usage:
    python3 scripts/generate_podcast_rss.py \
        --base-url https://github.com/<user>/<repo>/releases/download/ies-2026-audio \
        --output docs/podcast.xml
"""
import argparse
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

PODCAST_TITLE = "IES 2026 General Economics — AI Study Podcast"
PODCAST_AUTHOR = "IES 2026 Prep"
PODCAST_DESCRIPTION = (
    "Comprehensive audio revision for IES General Economics papers GE-01 to GE-04. "
    "Each episode covers one topic cluster at DSE/JNU masters level, using past "
    "IES questions as anchors. AI-generated deep-dive discussions optimised for "
    "exam preparation."
)
PODCAST_LANGUAGE = "en"
PODCAST_CATEGORY = "Education"
PODCAST_SUBCATEGORY = "Courses"
PODCAST_IMAGE_URL = ""  # set after uploading cover art

EPISODE_META = {
    "GE01_A1_consumers_demand_utility_indifference": {
        "title": "GE-01 | A1 | Consumer Demand — Utility & Indifference",
        "description": (
            "Cardinal vs ordinal utility, indifference curves, Slutsky theorem, "
            "duality theory, revealed preference, Roy's identity, demand elasticities. "
            "IES GE-01 revision at DSE masters level."
        ),
        "season": 1, "episode": 1,
    },
    "GE01_A2_consumers_demand_risk_asymmetric_information": {
        "title": "GE-01 | A2 | Consumer Demand — Risk & Asymmetric Info",
        "description": (
            "Von Neumann-Morgenstern expected utility, Arrow-Pratt risk aversion, "
            "Akerlof's market for lemons, moral hazard, Spence signalling, "
            "separating vs pooling equilibrium."
        ),
        "season": 1, "episode": 2,
    },
    "GE01_A3_theory_of_value_market_structures_game_theory": {
        "title": "GE-01 | A3 | Theory of Value — Market Structures & Game Theory",
        "description": (
            "Perfect competition, monopoly pricing and price discrimination, "
            "Cournot/Bertrand/Stackelberg oligopoly, Nash equilibrium, peak-load pricing, "
            "natural monopoly regulation."
        ),
        "season": 1, "episode": 3,
    },
    "GE01_A4_theory_production_distribution_mathematical_methods": {
        "title": "GE-01 | A4 | Production, Distribution & Math Methods",
        "description": (
            "Cobb-Douglas/CES production functions, cost duality, Euler's theorem, "
            "marginal productivity theory, Kaldor/Kalecki/Ricardo distribution, "
            "linear programming, Leontief input-output model."
        ),
        "season": 1, "episode": 4,
    },
    "GE01_A5_statistical_econometric_welfare": {
        "title": "GE-01 | A5 | Econometrics & Welfare Economics",
        "description": (
            "OLS assumptions, Gauss-Markov, heteroscedasticity/autocorrelation/multicollinearity, "
            "IV estimation, unit roots, Pareto optimality, Arrow's impossibility theorem, "
            "Coase theorem, public goods."
        ),
        "season": 1, "episode": 5,
    },
    "GE02_A1_growth_classical_neoclassical_endogenous": {
        "title": "GE-02 | A1 | Growth Theory — Classical, Solow & Endogenous",
        "description": (
            "Harrod-Domar knife-edge instability, Solow steady state and golden rule, "
            "convergence hypothesis, Solow residual, Romer's endogenous growth, "
            "Lucas human capital model."
        ),
        "season": 2, "episode": 1,
    },
    "GE02_A2_development_theories_measurement_capability": {
        "title": "GE-02 | A2 | Development Theories — Big Push to Sen's Capability",
        "description": (
            "Rostow stages, Rosenstein-Rodan Big Push, Nurkse vicious circle, "
            "Lewis dual economy, Dependency school, HDI methodology, "
            "Sen's capability approach and development as freedom."
        ),
        "season": 2, "episode": 2,
    },
    "GE02_A3_employment_output_inflation_money_NIA": {
        "title": "GE-02 | A3 | IS-LM, Inflation & National Accounts",
        "description": (
            "Keynesian effective demand, IS-LM derivation and policy, AD-AS, "
            "Phillips curve and NAIRU, quantity theory of money, "
            "Keynes vs Friedman, GDP measurement methods."
        ),
        "season": 2, "episode": 3,
    },
    "GE02_A4_international_economics_trade_thought_finance": {
        "title": "GE-02 | A4 | Trade Theory, Economic Thought & Capital Markets",
        "description": (
            "Heckscher-Ohlin, Stolper-Samuelson, Rybczynski, new trade theory, "
            "Quesnay to Friedman history of thought, EMH forms, "
            "financial crises 1997/2008."
        ),
        "season": 2, "episode": 4,
    },
    "GE02_A5_balance_of_payments_open_economy_global_institutions": {
        "title": "GE-02 | A5 | BOP, Mundell-Fleming & Global Institutions",
        "description": (
            "Marshall-Lerner condition, J-curve, absorption approach, IS-LM-BP model, "
            "Mundell-Fleming with perfect capital mobility, IMF/World Bank/WTO mandates."
        ),
        "season": 2, "episode": 5,
    },
    "GE03_A1_environmental_economics": {
        "title": "GE-03 | A1 | Environmental Economics — Pigou to Hotelling",
        "description": (
            "Pigouvian tax vs cap-and-trade, environmental valuation (CVM, hedonic, travel cost), "
            "Hotelling's rule for exhaustible resources, tragedy of the commons, "
            "Ostrom, carbon pricing, green GDP."
        ),
        "season": 3, "episode": 1,
    },
    "GE03_A2_industrial_economics_market_structure_policy": {
        "title": "GE-03 | A2 | Industrial Economics — SCP, Regulation & Policy",
        "description": (
            "Structure-conduct-performance paradigm, HHI and Lerner index, "
            "limit pricing, Ramsey pricing for natural monopoly, "
            "Schumpeter hypothesis on R&D, antitrust and merger policy."
        ),
        "season": 3, "episode": 2,
    },
    "GE03_A3_public_finance_taxation_expenditure": {
        "title": "GE-03 | A3 | Public Finance — Taxation, Debt & Fiscal Federalism",
        "description": (
            "Excess burden of taxation, Ramsey inverse elasticity rule, "
            "Wagner's Law, Ricardian equivalence, Tiebout model, "
            "public goods Samuelson condition, Laffer curve."
        ),
        "season": 3, "episode": 3,
    },
    "GE03_A4_state_market_planning_reform": {
        "title": "GE-03 | A4 | State, Market & Planning",
        "description": (
            "Hayek's knowledge problem, Lange-Lerner market socialism debate, "
            "Washington Consensus and its critique, import substitution vs export-led growth, "
            "developmental state theory (Johnson, Amsden)."
        ),
        "season": 3, "episode": 4,
    },
    "GE04_A1_agriculture_rural_poverty_labour_urbanisation": {
        "title": "GE-04 | A1 | Agriculture, Poverty, Labour & Urbanisation",
        "description": (
            "MSP and WTO Green/Amber Box, MGNREGA design and multiplier, "
            "FGT poverty indices, Alkire-Foster MPI, Labour Codes consolidation, "
            "Harris-Todaro migration model, Smart Cities."
        ),
        "season": 4, "episode": 1,
    },
    "GE04_A2_money_banking_inflation_india": {
        "title": "GE-04 | A2 | Money, Banking & Inflation in India",
        "description": (
            "RBI monetary policy framework, MPC and inflation targeting, "
            "repo/CRR/SLR/OMO mechanics, NPA crisis and IBC 2016, "
            "WPI vs CPI comparison, demonetisation 2016, UPI and financial inclusion."
        ),
        "season": 4, "episode": 2,
    },
    "GE04_A3_fiscal_federal_finance_india": {
        "title": "GE-04 | A3 | Fiscal Policy, GST & Federal Finance",
        "description": (
            "FRBM Act and escape clauses, Union Budget structure, "
            "GST dual structure and IGST, 15th Finance Commission devolution criteria, "
            "cooperative federalism vs states fiscal autonomy."
        ),
        "season": 4, "episode": 3,
    },
    "GE04_A4_foreign_trade_development_planning_industry_india": {
        "title": "GE-04 | A4 | Trade, Planning History & Industry",
        "description": (
            "1991 BOP crisis and LPG reforms, Mahalanobis model, licence-permit raj, "
            "PLI scheme as vertical industrial policy, India-WTO obligations (TRIPS, GATS), "
            "Viksit Bharat 2047."
        ),
        "season": 4, "episode": 4,
    },
    "GE04_A5_synthesis_exam_strategy": {
        "title": "GE-04 | A5 | GE-04 Synthesis — Exam Traps & 2026 Predictions",
        "description": (
            "Inter-topic causal chains (agricultural distress → Harris-Todaro → poverty), "
            "known IES exam traps (GST angles, Finance Commission vs NITI Aayog), "
            "high-probability 2026 question predictions: 16th FC, PLI, UPI, IBC."
        ),
        "season": 4, "episode": 5,
    },
}


def file_size_bytes(path: Path) -> int:
    return path.stat().st_size


def sha256_guid(stem: str) -> str:
    return hashlib.sha256(stem.encode()).hexdigest()[:32]


def build_rss(audio_dir: Path, base_url: str, podcast_image_url: str) -> str:
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    items = []
    for mp3_path in sorted(audio_dir.rglob("*.mp3")):
        stem = mp3_path.stem
        meta = EPISODE_META.get(stem)
        if not meta:
            print(f"  WARN: no metadata for {stem}, skipping")
            continue

        file_url = f"{base_url.rstrip('/')}/{mp3_path.name}"
        size = file_size_bytes(mp3_path)
        guid = sha256_guid(stem)
        pub_date = now  # all episodes published same date for initial release

        items.append(f"""
    <item>
      <title>{meta['title']}</title>
      <description><![CDATA[{meta['description']}]]></description>
      <enclosure url="{file_url}" length="{size}" type="audio/mpeg"/>
      <guid isPermaLink="false">{guid}</guid>
      <pubDate>{pub_date}</pubDate>
      <itunes:title>{meta['title']}</itunes:title>
      <itunes:summary><![CDATA[{meta['description']}]]></itunes:summary>
      <itunes:duration>1200</itunes:duration>
      <itunes:season>{meta['season']}</itunes:season>
      <itunes:episode>{meta['episode']}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
    </item>""")

    image_block = ""
    if podcast_image_url:
        image_block = f"""
  <image>
    <url>{podcast_image_url}</url>
    <title>{PODCAST_TITLE}</title>
    <link>{base_url}</link>
  </image>
  <itunes:image href="{podcast_image_url}"/>"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{PODCAST_TITLE}</title>
    <link>{base_url}</link>
    <language>{PODCAST_LANGUAGE}</language>
    <description><![CDATA[{PODCAST_DESCRIPTION}]]></description>
    <author>{PODCAST_AUTHOR}</author>
    <managingEditor>{PODCAST_AUTHOR}</managingEditor>
    <pubDate>{now}</pubDate>
    <lastBuildDate>{now}</lastBuildDate>
    <itunes:author>{PODCAST_AUTHOR}</itunes:author>
    <itunes:summary><![CDATA[{PODCAST_DESCRIPTION}]]></itunes:summary>
    <itunes:category text="{PODCAST_CATEGORY}">
      <itunes:category text="{PODCAST_SUBCATEGORY}"/>
    </itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>serial</itunes:type>{image_block}
{"".join(items)}
  </channel>
</rss>"""
    return rss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True,
                        help="Public base URL where MP3 files are hosted")
    parser.add_argument("--audio-dir", default="data/audio",
                        help="Local directory containing MP3 files (searched recursively)")
    parser.add_argument("--output", default="docs/podcast.xml",
                        help="Output path for RSS XML")
    parser.add_argument("--image-url", default="",
                        help="Public URL to podcast cover art (3000x3000 JPG)")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    audio_dir = project_root / args.audio_dir
    out_path = project_root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Scanning {audio_dir} for MP3 files...")
    rss = build_rss(audio_dir, args.base_url, args.image_url)
    out_path.write_text(rss, encoding="utf-8")
    print(f"RSS feed written to {out_path}")
    print(f"Episodes: {rss.count('<item>')}")


if __name__ == "__main__":
    main()
