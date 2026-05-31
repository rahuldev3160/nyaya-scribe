"""
Upload IES 2026 General Economics audio episodes to YouTube.
ffmpeg wraps each MP3 in a static-thumbnail MP4 for YouTube.
After upload, the YouTube thumbnail API sets the custom thumbnail.

Setup (one-time):
  1. Google Cloud Console → enable YouTube Data API v3
  2. OAuth 2.0 Desktop credentials → save to config/youtube_client_secret.json
  3. First run opens browser for auth → token saved to config/youtube_token.json

Usage:
  python3.11 scripts/upload_to_youtube.py --paper ge01
  python3.11 scripts/upload_to_youtube.py --all
  python3.11 scripts/upload_to_youtube.py --file data/audio/ge01/GE-01_A1_*.mp3
"""
import argparse
import json
import re
import subprocess
import time
from pathlib import Path

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR   = PROJECT_ROOT / "config"
CLIENT_SECRET  = CONFIG_DIR / "youtube_client_secret.json"
TOKEN_FILE     = CONFIG_DIR / "youtube_token.json"
THUMBNAIL_DIR  = PROJECT_ROOT / "data" / "thumbnails"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",  # needed for delete + thumbnail set
]

# ── Episode metadata ────────────────────────────────────────────────────────
# key format: ge01_a1, ge03_a1a, etc. (matches data/thumbnails/{key}.jpg)
# Produced by: stem_to_key(mp3_path.stem)
EPISODES = {
    # ── GE-01 Microeconomics ──────────────────────────────────────────────
    "ge01_a1": {
        "yt_title": "IES 2026 GE-01 | A1: Consumer Demand — Utility & Indifference | Audio Lecture",
        "topics": [
            "Cardinal vs. Ordinal Utility",
            "Indifference curves & budget constraint",
            "Income & substitution effect decomposition",
            "Revealed Preference Theory",
            "Hicksian vs. Marshallian demand",
        ],
        "tags": ["utility theory", "indifference curves", "income substitution effect",
                 "revealed preference", "consumer demand", "microeconomics"],
    },
    "ge01_a2": {
        "yt_title": "IES 2026 GE-01 | A2: Consumer Demand — Risk & Asymmetric Information | Audio",
        "topics": [
            "VNM Expected Utility framework",
            "Risk aversion & risk premium",
            "Adverse selection & moral hazard",
            "Spence signalling model",
            "Akerlof lemons problem",
        ],
        "tags": ["VNM utility", "adverse selection", "moral hazard", "asymmetric information",
                 "signalling model", "information economics"],
    },
    "ge01_a3": {
        "yt_title": "IES 2026 GE-01 | A3: Market Structures & Game Theory | Audio Lecture",
        "topics": [
            "Perfect competition vs. monopoly vs. oligopoly",
            "Price discrimination (1st/2nd/3rd degree)",
            "Cournot & Stackelberg duopoly",
            "Nash equilibrium & dominant strategies",
            "Entry deterrence & limit pricing",
        ],
        "tags": ["market structures", "Cournot duopoly", "Nash equilibrium", "game theory",
                 "monopoly pricing", "oligopoly", "price discrimination"],
    },
    "ge01_a4": {
        "yt_title": "IES 2026 GE-01 | A4: Production, Distribution & Mathematical Methods | Audio",
        "topics": [
            "Production functions: Cobb-Douglas & CES",
            "Euler theorem & returns to scale",
            "Factor distribution theory",
            "Linear programming & duality",
            "Input-output analysis (Leontief)",
        ],
        "tags": ["production function", "Cobb-Douglas", "Euler theorem", "factor distribution",
                 "linear programming", "Leontief", "mathematical economics"],
    },
    "ge01_a5": {
        "yt_title": "IES 2026 GE-01 | A5: Econometrics & Welfare Economics | Audio Lecture",
        "topics": [
            "OLS, BLUE, Gauss-Markov theorem",
            "Heteroscedasticity & multicollinearity",
            "Arrow impossibility theorem",
            "Coase theorem & externalities",
            "Social welfare functions",
        ],
        "tags": ["econometrics", "OLS regression", "Arrow impossibility", "Coase theorem",
                 "welfare economics", "social welfare function", "Gauss-Markov"],
    },
    # ── GE-02 Macroeconomics ──────────────────────────────────────────────
    "ge02_a1": {
        "yt_title": "IES 2026 GE-02 | A1: Growth Theory — Classical, Solow & Endogenous | Audio",
        "topics": [
            "Harrod-Domar model: warranted vs. natural rate",
            "Solow model: steady state & golden rule",
            "Convergence hypothesis (absolute vs. conditional)",
            "Romer & Lucas endogenous growth",
            "AK model, human capital & knowledge spillovers",
        ],
        "tags": ["Solow model", "Harrod-Domar", "endogenous growth", "Romer model",
                 "golden rule", "growth theory", "economic growth"],
    },
    "ge02_a2": {
        "yt_title": "IES 2026 GE-02 | A2: Development Theories — Big Push to Sen | Audio Lecture",
        "topics": [
            "Lewis dual-sector model",
            "Big Push & coordination failures (Rosenstein-Rodan)",
            "Dependency theory & Prebisch-Singer hypothesis",
            "Human Development Index (HDI) methodology",
            "Amartya Sen's capability approach",
        ],
        "tags": ["Lewis model", "Big Push model", "dependency theory", "Prebisch-Singer",
                 "human development", "HDI", "Sen capability approach", "development economics"],
    },
    "ge02_a3": {
        "yt_title": "IES 2026 GE-02 | A3: IS-LM, Inflation & National Income Accounting | Audio",
        "topics": [
            "IS-LM framework (closed economy)",
            "Quantity theory of money & Fisher equation",
            "Phillips curve: short-run vs. long-run",
            "National Income Accounting: GDP, GNP, NNP",
            "Keynesian multiplier & fiscal policy effectiveness",
        ],
        "tags": ["IS-LM model", "Phillips curve", "quantity theory of money",
                 "national income accounting", "GDP", "Keynesian multiplier", "macroeconomics"],
    },
    "ge02_a4": {
        "yt_title": "IES 2026 GE-02 | A4: Trade Theory & History of Economic Thought | Audio",
        "topics": [
            "Heckscher-Ohlin theorem & factor endowments",
            "Stolper-Samuelson & Rybczynski theorems",
            "New trade theory (Krugman, economies of scale)",
            "History of thought: Classical, Marxian, Keynesian",
            "Efficient Market Hypothesis & financial economics",
        ],
        "tags": ["Heckscher-Ohlin", "Stolper-Samuelson", "Rybczynski", "new trade theory",
                 "history of economic thought", "EMH", "classical economics", "Keynesian"],
    },
    "ge02_a5": {
        "yt_title": "IES 2026 GE-02 | A5: BOP, Mundell-Fleming & Global Institutions | Audio",
        "topics": [
            "Balance of Payments: current, capital & financial accounts",
            "Mundell-Fleming model: IS-LM-BP",
            "Marshall-Lerner condition & J-curve",
            "Exchange rate systems: fixed vs. floating",
            "IMF, World Bank, WTO — roles & critiques",
        ],
        "tags": ["balance of payments", "Mundell-Fleming", "Marshall-Lerner", "J-curve",
                 "exchange rate", "IMF", "WTO", "open economy macroeconomics"],
    },
    # ── GE-03 Public & Environmental Economics ────────────────────────────
    "ge03_a1a": {
        "yt_title": "IES 2026 GE-03 | A1a: Pigouvian Tax, Cap-and-Trade & Environmental Policy",
        "topics": [
            "Negative externalities & social cost vs. private cost",
            "Pigouvian tax — design & limitations",
            "Coasian bargaining vs. command-and-control",
            "Emissions trading & permit markets",
            "Carbon pricing — tax vs. cap-and-trade comparison",
        ],
        "tags": ["Pigouvian tax", "cap and trade", "carbon pricing", "environmental economics",
                 "externalities", "emissions trading", "Coase theorem", "GE-03"],
    },
    "ge03_a1b": {
        "yt_title": "IES 2026 GE-03 | A1b: Environmental Valuation & Natural Resource Economics",
        "topics": [
            "Contingent valuation method (CVM)",
            "Hedonic pricing & travel cost methods",
            "Hotelling's rule for exhaustible resources",
            "Sustainable development & Brundtland definition",
            "Paris Agreement & carbon budget",
        ],
        "tags": ["contingent valuation", "hedonic pricing", "Hotelling rule",
                 "natural resource economics", "sustainability", "climate economics", "GE-03"],
    },
    "ge03_a2a": {
        "yt_title": "IES 2026 GE-03 | A2a: SCP Framework, Market Concentration & Entry Barriers",
        "topics": [
            "Structure-Conduct-Performance (SCP) paradigm",
            "HHI & market concentration measurement",
            "Barriers to entry: structural vs. strategic",
            "Predatory pricing & limit pricing",
            "Cartel formation & stability",
        ],
        "tags": ["SCP framework", "industrial organisation", "HHI", "barriers to entry",
                 "predatory pricing", "cartel", "market concentration", "GE-03"],
    },
    "ge03_a2b": {
        "yt_title": "IES 2026 GE-03 | A2b: Competition Policy, Regulation & Innovation | Audio",
        "topics": [
            "Antitrust law — CCI & Competition Act 2002",
            "Regulatory capture theory (Stigler)",
            "Natural monopoly regulation: price-cap vs. rate-of-return",
            "Network effects & platform economics",
            "Schumpeterian innovation & creative destruction",
        ],
        "tags": ["antitrust", "CCI", "Competition Act", "regulatory capture", "natural monopoly",
                 "network effects", "Schumpeter", "innovation economics", "GE-03"],
    },
    "ge03_a3a": {
        "yt_title": "IES 2026 GE-03 | A3a: Public Goods, Club Goods & Optimal Taxation | Audio",
        "topics": [
            "Samuelson condition for public good provision",
            "Club goods & the Tiebout hypothesis",
            "Ramsey pricing & inverse elasticity rule",
            "Diamond-Mirrlees optimal commodity tax",
            "Optimal income tax (Mirrlees)",
        ],
        "tags": ["public goods", "Samuelson condition", "optimal taxation", "Ramsey pricing",
                 "club goods", "Tiebout", "Mirrlees", "public finance", "GE-03"],
    },
    "ge03_a3b": {
        "yt_title": "IES 2026 GE-03 | A3b: Government Debt, Fiscal Federalism & Expenditure",
        "topics": [
            "Ricardian Equivalence — logic & critique",
            "Public debt sustainability: debt-to-GDP dynamics",
            "Musgrave's principles of fiscal federalism",
            "Wagner's Law & public expenditure growth",
            "FRBM & fiscal consolidation in India",
        ],
        "tags": ["Ricardian equivalence", "fiscal federalism", "Wagner law",
                 "public debt", "FRBM", "Musgrave", "government expenditure", "GE-03"],
    },
    "ge03_a4": {
        "yt_title": "IES 2026 GE-03 | A4: State vs. Market, Planning & Development Strategy",
        "topics": [
            "Market failures: public goods, externalities, information",
            "Government failures & public choice theory",
            "Washington Consensus — prescriptions & critique",
            "Industrial policy debate (neutral vs. targeted)",
            "Planning vs. market: historical & theoretical perspective",
        ],
        "tags": ["market failure", "government failure", "Washington Consensus",
                 "industrial policy", "public choice", "development planning", "GE-03"],
    },
    # ── GE-04 Indian Economy ──────────────────────────────────────────────
    "ge04_a1a": {
        "yt_title": "IES 2026 GE-04 | A1a: Indian Agriculture — MSP, Farm Reforms & Rural Policy",
        "topics": [
            "Green Revolution: achievements & limitations",
            "Minimum Support Price (MSP) policy & procurement",
            "Agricultural credit — NABARD, Kisan Credit Card",
            "Farm Acts 2020 — controversy & withdrawal",
            "PM-KISAN & direct benefit transfers",
        ],
        "tags": ["Indian agriculture", "MSP policy", "green revolution", "NABARD",
                 "farm reforms", "rural economy", "agricultural credit", "GE-04"],
    },
    "ge04_a1b": {
        "yt_title": "IES 2026 GE-04 | A1b: Poverty, Inequality & Human Development in India",
        "topics": [
            "Poverty measurement: Tendulkar vs. Rangarajan lines",
            "Multidimensional Poverty Index (MPI) — India data",
            "Gini coefficient & income inequality trends",
            "MGNREGS — design, outcomes & criticisms",
            "India's SDG progress: SDG 1, 2, 8, 10",
        ],
        "tags": ["poverty in India", "Tendulkar committee", "MPI", "Gini coefficient",
                 "MGNREGS", "human development", "SDG India", "inequality", "GE-04"],
    },
    "ge04_a1c": {
        "yt_title": "IES 2026 GE-04 | A1c: Labour Markets, Employment & Urbanisation in India",
        "topics": [
            "Formal vs. informal sector segmentation",
            "Harris-Todaro model of rural-urban migration",
            "PLFS data — LFPR, WPR, UR trends",
            "Labour Codes 2020 — consolidation & implications",
            "Smart Cities Mission & urban development",
        ],
        "tags": ["Indian labour market", "Harris-Todaro", "informal sector",
                 "PLFS", "labour codes 2020", "urbanisation", "employment India", "GE-04"],
    },
    "ge04_a2": {
        "yt_title": "IES 2026 GE-04 | A2: Money, Banking, Inflation & Monetary Policy in India",
        "topics": [
            "RBI Monetary Policy Committee & inflation targeting",
            "CPI target (4%) — Flexible Inflation Targeting framework",
            "NPA crisis — causes, IBC resolution mechanism",
            "Financial inclusion: Jan Dhan, UPI, MUDRA",
            "Transmission mechanism of monetary policy",
        ],
        "tags": ["RBI monetary policy", "inflation targeting", "NPA", "IBC",
                 "Jan Dhan Yojana", "financial inclusion", "UPI", "monetary transmission", "GE-04"],
    },
    "ge04_a3": {
        "yt_title": "IES 2026 GE-04 | A3: Fiscal Policy, GST & Fiscal Federalism in India",
        "topics": [
            "GST design: CGST, SGST, IGST structure",
            "Finance Commission — horizontal & vertical devolution",
            "15th Finance Commission: new criteria & equity critique",
            "FRBM Act — fiscal deficit targets & COVID escape clause",
            "Centre-State financial relations & grants",
        ],
        "tags": ["GST India", "fiscal federalism", "Finance Commission", "FRBM",
                 "Centre-State relations", "fiscal deficit", "direct taxes", "GE-04"],
    },
    "ge04_a4": {
        "yt_title": "IES 2026 GE-04 | A4: Trade Policy, 1991 Reforms & Industrial Policy in India",
        "topics": [
            "1991 BOP crisis: causes & IMF programme",
            "LPG reforms — liberalisation, privatisation, globalisation",
            "Make in India & PLI scheme — design & outcomes",
            "WTO obligations: TRIPS, GATS, agricultural subsidies",
            "Viksit Bharat 2047 — pillars & feasibility",
        ],
        "tags": ["1991 reforms", "LPG reforms", "Make in India", "PLI scheme",
                 "WTO India", "TRIPS", "industrial policy India", "Viksit Bharat", "GE-04"],
    },
    "ge04_a5": {
        "yt_title": "IES 2026 GE-04 | A5: Synthesis — Connections, Exam Traps & 2026 Predictions",
        "topics": [
            "Agricultural distress → rural-urban migration → poverty chain",
            "Fiscal deficit → inflation → RBI monetary response chain",
            "GST trap: fiscal federalism vs. tax reform angle",
            "Finance Commission vs. NITI Aayog — roles & powers",
            "High-probability 2026 question predictions & answer frameworks",
        ],
        "tags": ["IES 2026 revision", "exam strategy", "Indian economy connections",
                 "GE-04 exam traps", "IES predictions 2026", "GE-04 synthesis"],
    },
}

SERIES_OVERVIEW = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 COMPLETE SERIES — IES 2026 General Economics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GE-01 | Microeconomics (5 episodes)
  A1 — Consumer Demand: Utility & Indifference
  A2 — Consumer Demand: Risk & Asymmetric Info
  A3 — Market Structures & Game Theory
  A4 — Production, Distribution & Math Methods
  A5 — Econometrics & Welfare Economics

GE-02 | Macroeconomics & Development (5 episodes)
  A1 — Growth Theory: Classical, Solow & Endogenous
  A2 — Development Theories: Big Push to Sen
  A3 — IS-LM, Inflation & National Accounts
  A4 — Trade Theory & Economic Thought
  A5 — BOP, Mundell-Fleming & Global Institutions

GE-03 | Public, Environmental & Industrial Economics (7 episodes)
  A1a — Pigouvian Tax & Cap-and-Trade
  A1b — Environmental Valuation & Resource Economics
  A2a — SCP Framework & Market Concentration
  A2b — Competition Policy, Regulation & Innovation
  A3a — Public Goods & Optimal Taxation
  A3b — Debt, Fiscal Federalism & Public Expenditure
  A4  — State, Market & Development Planning

GE-04 | Indian Economy (7 episodes)
  A1a — Agriculture & Rural Economy
  A1b — Poverty, Inequality & Human Development
  A1c — Labour Markets, Employment & Urbanisation
  A2  — Money, Banking & Monetary Policy
  A3  — Fiscal Policy & Federal Finance
  A4  — Trade Policy, 1991 Reforms & Industry
  A5  — Synthesis: Connections, Traps & Predictions"""

BASE_TAGS = [
    "IES 2026", "ESE 2026", "General Economics", "UPSC IES",
    "IES preparation", "economics lecture", "economics revision",
    "DSE economics", "JNU economics", "deep dive audio",
    "economics audio lecture", "IES 2026 preparation",
    "competitive exam economics", "economics PYQ",
    "IES general economics", "ESE general economics",
    "UPSC economics optional", "economics study audio",
]

PAPER_TAGS = {
    "ge01": ["microeconomics", "GE-01", "consumer theory", "game theory", "welfare economics"],
    "ge02": ["macroeconomics", "GE-02", "growth theory", "international economics", "development economics"],
    "ge03": ["public economics", "environmental economics", "industrial economics", "GE-03"],
    "ge04": ["Indian economy", "GE-04", "Indian economic policy", "India economics"],
}


def stem_to_key(stem: str) -> str | None:
    """Map MP3 stem like 'GE-01 _ A1a _ Topic' to key like 'ge01_a1a'."""
    m = re.match(r"GE-0?(\d)\s*_\s*(A\d+[a-z]?)", stem, re.IGNORECASE)
    if m:
        return f"ge0{m.group(1)}_{m.group(2).lower()}"
    return None


def build_description(key: str, ep: dict) -> str:
    topics_block = "\n".join(f"  • {t}" for t in ep["topics"])
    paper_num = key[:4].upper().replace("GE0", "GE-0")  # ge01 → GE-01

    return f"""\
🎓 IES 2026 General Economics | {paper_num} | Deep Dive Audio Lecture

{ep['yt_title']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 Topics covered in this episode
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{topics_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Who is this for?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• IES/ESE 2026 aspirants (General Economics paper)
• UPSC Economics Optional candidates
• DSE/JNU Masters Economics students
• Anyone who wants structured, exam-anchored economics revision

Each episode is anchored to actual IES Past Year Questions (PYQs) from 2010–2025.
All mathematical relationships are explained in plain spoken English.
Generated using NotebookLM (Google) with a structured PYQ database.

{SERIES_OVERVIEW}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Subscribe for the complete series
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#IES2026 #ESE2026 #GeneralEconomics #EconomicsRevision #UPSC #DSEEconomics #DeepDiveAudio"""


def get_youtube_client():
    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            data = json.load(f)
        creds = google.oauth2.credentials.Credentials(**data)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET.exists():
                raise FileNotFoundError(
                    f"YouTube client secret not found at {CLIENT_SECRET}\n"
                    "Download from Google Cloud Console → OAuth 2.0 credentials."
                )
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET), SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            json.dump({
                "token":         creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri":     creds.token_uri,
                "client_id":     creds.client_id,
                "client_secret": creds.client_secret,
                "scopes":        list(creds.scopes),
            }, f)

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def make_video(mp3_path: Path, thumbnail_path: Path) -> Path:
    """Wrap MP3 in a static-image MP4 for YouTube upload."""
    out = mp3_path.with_suffix(".youtube.mp4")
    if out.exists():
        return out

    if thumbnail_path and thumbnail_path.exists():
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1", "-i", str(thumbnail_path),
            "-i", str(mp3_path),
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
            "-threads", "2",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(out),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=0d0920:s=1280x720:r=1",
            "-i", str(mp3_path),
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
            "-threads", "2",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(out),
        ]

    print(f"  Making video: {out.name}")
    subprocess.run(cmd, check=True)
    return out


def _trim_tags(tags: list[str], max_tags: int = 22) -> list[str]:
    """Cap at 22 tags — empirically safe for YouTube Data API v3."""
    seen, out = set(), []
    for tag in tags:
        tag = tag.strip()[:100]
        if not tag or tag.lower() in seen:
            continue
        seen.add(tag.lower())
        out.append(tag)
        if len(out) >= max_tags:
            break
    return out


def upload_video(youtube, video_path: Path, key: str, ep: dict) -> str:
    title = ep["yt_title"][:100]
    paper_key = key[:4]  # ge01, ge02, …
    raw_tags = BASE_TAGS + PAPER_TAGS.get(paper_key, []) + ep.get("tags", [])
    tags = _trim_tags(raw_tags)
    description = build_description(key, ep)

    body = {
        "snippet": {
            "title":           title,
            "description":     description,
            "tags":            tags,
            "categoryId":      "27",        # Education
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus":          "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = googleapiclient.http.MediaFileUpload(
        str(video_path),
        chunksize=10 * 1024 * 1024,
        resumable=True,
        mimetype="video/mp4",
    )

    print(f"  Uploading: {title}")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"    {int(status.progress() * 100)}%", end="\r")

    video_id = response["id"]
    print(f"  Uploaded: https://youtu.be/{video_id}")
    return video_id


def upload_thumbnail(youtube, video_id: str, thumbnail_path: Path):
    """Upload custom thumbnail via API (account must have phone-verified channel)."""
    if not thumbnail_path or not thumbnail_path.exists():
        return
    try:
        media = googleapiclient.http.MediaFileUpload(
            str(thumbnail_path), mimetype="image/jpeg"
        )
        youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
        print(f"  Thumbnail uploaded via API")
    except googleapiclient.errors.HttpError as e:
        if "unacceptable" in str(e).lower() or "403" in str(e):
            print(f"  ⚠ Thumbnail API blocked: channel not verified. "
                  f"Verify phone at youtube.com/verify to enable custom thumbnails.")
        else:
            print(f"  ⚠ Thumbnail upload failed: {e}")


def delete_videos(youtube, video_ids: list[str]):
    """Delete YouTube videos by ID."""
    for vid in video_ids:
        try:
            youtube.videos().delete(id=vid).execute()
            print(f"  Deleted: https://youtu.be/{vid}")
        except googleapiclient.errors.HttpError as e:
            print(f"  ⚠ Could not delete {vid}: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper",  choices=["ge01", "ge02", "ge03", "ge04"])
    parser.add_argument("--all",    action="store_true")
    parser.add_argument("--file",   help="Upload a single MP3 file")
    parser.add_argument("--delete", nargs="+", metavar="VIDEO_ID",
                        help="Delete YouTube videos by ID before uploading")
    args = parser.parse_args()

    audio_dir = PROJECT_ROOT / "data" / "audio"

    # Determine file list first (needed even if we also delete)
    if args.file:
        mp3_files = [Path(args.file)]
    elif args.paper:
        mp3_files = sorted((audio_dir / args.paper).glob("*.mp3"))
    elif args.all:
        mp3_files = sorted(audio_dir.rglob("*.mp3"))
    elif args.delete:
        mp3_files = []
    else:
        parser.print_help()
        return

    # Delete old token so new scopes are picked up if needed
    youtube = get_youtube_client()

    # Delete specified videos first
    if args.delete:
        print(f"Deleting {len(args.delete)} video(s)…")
        delete_videos(youtube, args.delete)
        if not mp3_files:
            return

    if not mp3_files:
        print("No MP3 files found.")
        return

    # Clean up old .youtube.mp4 files so they rebuild with new thumbnails
    for mp3_path in mp3_files:
        old_mp4 = mp3_path.with_suffix(".youtube.mp4")
        if old_mp4.exists():
            old_mp4.unlink()

    print(f"\nFound {len(mp3_files)} MP3 file(s) to upload.")

    for mp3_path in mp3_files:
        print(f"\n[{mp3_path.name}]")
        key = stem_to_key(mp3_path.stem)
        ep  = EPISODES.get(key, {})

        if not ep:
            print(f"  ⚠ No metadata for key={key!r} — using filename as title.")
            ep = {
                "yt_title": mp3_path.stem,
                "topics":   [],
                "tags":     [],
            }

        thumbnail_path = THUMBNAIL_DIR / f"{key}.jpg" if key else None
        if thumbnail_path and thumbnail_path.exists():
            print(f"  Thumbnail: {thumbnail_path.name}")
        else:
            print(f"  No thumbnail found at data/thumbnails/{key}.jpg — run create_thumbnails.py first.")

        video_path = make_video(mp3_path, thumbnail_path)
        video_id   = upload_video(youtube, video_path, key or "unknown", ep)
        upload_thumbnail(youtube, video_id, thumbnail_path)
        print("  Sleeping 15s to respect quota...")
        time.sleep(15)

    print("\nAll uploads complete.")


if __name__ == "__main__":
    main()
