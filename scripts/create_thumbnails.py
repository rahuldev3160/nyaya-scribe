#!/usr/bin/env python3.11
"""
Generate per-episode YouTube thumbnails for the IES 2026 General Economics audio series.

Optional: place a study background photo at data/thumbnails/study_bg.jpg
(1280x720+ landscape JPG, e.g. a student with headphones in a quiet room).
If present, it will be darkened and tinted and used as the background.
If not, a rich gradient is used automatically.

Usage:
    python3.11 scripts/create_thumbnails.py          # all episodes
    python3.11 scripts/create_thumbnails.py --paper ge01
    python3.11 scripts/create_thumbnails.py --open   # open one to preview
"""
import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

PROJECT_ROOT = Path(__file__).parent.parent
THUMBNAIL_DIR = PROJECT_ROOT / "data" / "thumbnails"
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

STUDY_BG = THUMBNAIL_DIR / "study_bg.jpg"

W, H = 1280, 720

FONT_BOLD = "/System/Library/Fonts/Helvetica.ttc"
FONT_REG  = "/System/Library/Fonts/Helvetica.ttc"
BOLD_IDX  = 1
REG_IDX   = 0

# Paper accent colours
PAPER_COLOR = {
    "ge01": (65, 120, 220),    # rich blue  — Microeconomics
    "ge02": (46, 160, 100),    # growth green — Macroeconomics
    "ge03": (210, 155, 20),    # amber/gold — Public & Env Econ
    "ge04": (220, 80, 60),     # warm coral — Indian Economy
}

PAPER_LABEL = {
    "ge01": ("GE-01", "MICROECONOMICS"),
    "ge02": ("GE-02", "MACROECONOMICS"),
    "ge03": ("GE-03", "PUBLIC & ENV. ECONOMICS"),
    "ge04": ("GE-04", "INDIAN ECONOMY"),
}

# ── Episode registry ────────────────────────────────────────────────────────
# key  → (paper, title_line1, title_line2_or_None, topics_list, episode_label)
EPISODES = {
    # GE-01
    "ge01_a1": ("ge01", "Consumer Demand", "Utility & Indifference",
                 ["Utility Theory", "Indifference Curves", "Slutsky Theorem", "Revealed Preference"],
                 "Episode 1 of 5"),
    "ge01_a2": ("ge01", "Consumer Demand", "Risk & Asymmetric Information",
                 ["VNM Utility", "Adverse Selection", "Moral Hazard", "Spence Signalling"],
                 "Episode 2 of 5"),
    "ge01_a3": ("ge01", "Market Structures", "& Game Theory",
                 ["Perfect Competition", "Monopoly Pricing", "Oligopoly", "Nash Equilibrium"],
                 "Episode 3 of 5"),
    "ge01_a4": ("ge01", "Production, Distribution", "& Mathematical Methods",
                 ["Cobb-Douglas", "Euler Theorem", "Kaldor Distribution", "Linear Programming"],
                 "Episode 4 of 5"),
    "ge01_a5": ("ge01", "Econometrics &", "Welfare Economics",
                 ["OLS & BLUE", "Heteroscedasticity", "Arrow Impossibility", "Coase Theorem"],
                 "Episode 5 of 5"),
    # GE-02
    "ge02_a1": ("ge02", "Growth Theory", "Classical, Solow & Endogenous",
                 ["Harrod-Domar", "Solow Model", "Golden Rule", "Romer Endogenous Growth"],
                 "Episode 1 of 5"),
    "ge02_a2": ("ge02", "Development Theories", "Big Push to Sen's Capability",
                 ["Lewis Dual Sector", "Big Push Model", "Human Development", "Sen Capability Approach"],
                 "Episode 2 of 5"),
    "ge02_a3": ("ge02", "IS-LM, Inflation", "& National Accounts",
                 ["IS-LM Framework", "Phillips Curve", "Quantity Theory of Money", "National Income Accounting"],
                 "Episode 3 of 5"),
    "ge02_a4": ("ge02", "International Trade", "& Economic Thought",
                 ["Heckscher-Ohlin Theorem", "Stolper-Samuelson", "History of Economic Thought", "EMH"],
                 "Episode 4 of 5"),
    "ge02_a5": ("ge02", "BOP, Mundell-Fleming", "& Global Institutions",
                 ["Balance of Payments", "Mundell-Fleming Model", "Marshall-Lerner Condition", "IMF & WTO"],
                 "Episode 5 of 5"),
    # GE-03
    "ge03_a1a": ("ge03", "Environmental Instruments", "Pigouvian Taxes & Cap-and-Trade",
                  ["Pigouvian Taxation", "Coasian Bargaining", "Emissions Trading", "Carbon Pricing"],
                  "Episode 1 of 7"),
    "ge03_a1b": ("ge03", "Environmental Valuation", "& Natural Resource Economics",
                  ["CVM & Hedonic Pricing", "Resource Depletion", "Sustainability", "Climate Policy"],
                  "Episode 2 of 7"),
    "ge03_a2a": ("ge03", "Market Structure", "SCP Framework & Strategic Barriers",
                  ["Structure-Conduct-Performance", "Entry Barriers", "Predatory Pricing", "Cartels"],
                  "Episode 3 of 7"),
    "ge03_a2b": ("ge03", "Competition Policy", "Regulation & Innovation",
                  ["Antitrust Law", "Regulatory Capture", "Network Effects", "R&D Policy"],
                  "Episode 4 of 7"),
    "ge03_a3a": ("ge03", "Public Goods", "& Optimal Taxation",
                  ["Samuelson Condition", "Club Goods", "Optimal Tax Theory", "Ramsey Rule"],
                  "Episode 5 of 7"),
    "ge03_a3b": ("ge03", "Government Debt,", "Federalism & Public Expenditure",
                  ["Ricardian Equivalence", "Fiscal Federalism", "Wagner's Law", "FRBM"],
                  "Episode 6 of 7"),
    "ge03_a4":  ("ge03", "State, Market", "& Development Planning",
                  ["Market Failures", "Planning Models", "Public Sector Role", "Washington Consensus"],
                  "Episode 7 of 7"),
    # GE-04
    "ge04_a1a": ("ge04", "Agriculture", "& Rural Economy",
                  ["Green Revolution", "MSP Policy", "Agricultural Credit", "Farm Reforms"],
                  "Episode 1 of 7"),
    "ge04_a1b": ("ge04", "Poverty, Inequality", "& Human Development",
                  ["Poverty Measurement", "Gini Coefficient", "MGNREGS", "SDG Progress"],
                  "Episode 2 of 7"),
    "ge04_a1c": ("ge04", "Labour Markets", "Employment & Urbanisation",
                  ["Labour Market Segmentation", "Harris-Todaro Model", "Informal Sector", "Smart Cities"],
                  "Episode 3 of 7"),
    "ge04_a2":  ("ge04", "Money, Banking", "& Monetary Policy",
                  ["RBI Monetary Policy", "Inflation Targeting", "NPA Crisis", "Financial Inclusion"],
                  "Episode 4 of 7"),
    "ge04_a3":  ("ge04", "Fiscal Policy,", "Taxation & Federal Finance",
                  ["GST Reform", "Direct Tax Code", "Finance Commission", "Centre-State Relations"],
                  "Episode 5 of 7"),
    "ge04_a4":  ("ge04", "Foreign Trade,", "Planning & Industrial Policy",
                  ["1991 LPG Reforms", "Make in India", "PLI Scheme", "WTO Obligations"],
                  "Episode 6 of 7"),
    "ge04_a5":  ("ge04", "Synthesis &", "Exam Strategy",
                  ["Inter-topic Linkages", "Exam Traps", "High-probability Questions", "Answer Frameworks"],
                  "Episode 7 of 7"),
}


def load_fonts():
    sizes = {}
    for name, sz, idx in [
        ("xl_bold", 68, BOLD_IDX),
        ("lg_bold", 44, BOLD_IDX),
        ("md_bold", 32, BOLD_IDX),
        ("sm_reg",  24, REG_IDX),
        ("xs_reg",  20, REG_IDX),
    ]:
        sizes[name] = ImageFont.truetype(FONT_BOLD, sz, index=idx)
    return sizes


def make_gradient_bg():
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    top = (8, 9, 28)
    bot = (28, 15, 52)
    for y in range(H):
        t = y / H
        r = int(top[0] * (1 - t) + bot[0] * t)
        g = int(top[1] * (1 - t) + bot[1] * t)
        b = int(top[2] * (1 - t) + bot[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    return img


def make_photo_bg():
    raw = Image.open(STUDY_BG).convert("RGB")
    # Fit to 1280x720, crop to centre
    raw.thumbnail((W, H), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), (0, 0, 0))
    paste_x = (W - raw.width) // 2
    paste_y = (H - raw.height) // 2
    bg.paste(raw, (paste_x, paste_y))
    # Darken
    darken = Image.new("RGB", (W, H), (0, 0, 0))
    bg = Image.blend(bg, darken, alpha=0.55)
    # Purple-navy colour tint
    tint = Image.new("RGB", (W, H), (15, 10, 40))
    bg = Image.blend(bg, tint, alpha=0.35)
    return bg


def draw_headphones(draw, cx, cy, size, color):
    hw = int(size * 0.44)   # half-span
    cup_r = int(size * 0.22)
    band_thick = max(int(size * 0.08), 4)

    # Headband arc
    draw.arc(
        [cx - hw, cy - int(size * 0.55), cx + hw, cy + int(size * 0.05)],
        start=190, end=350,
        fill=color, width=band_thick,
    )
    # Left ear cup
    draw.ellipse(
        [cx - hw - cup_r, cy - cup_r, cx - hw + cup_r, cy + cup_r],
        fill=color,
    )
    # Right ear cup
    draw.ellipse(
        [cx + hw - cup_r, cy - cup_r, cx + hw + cup_r, cy + cup_r],
        fill=color,
    )
    # Inner padding (hollow look)
    pad = max(int(cup_r * 0.45), 4)
    inner = tuple(max(0, c - 25) for c in color)
    draw.ellipse(
        [cx - hw - cup_r + pad, cy - cup_r + pad, cx - hw + cup_r - pad, cy + cup_r - pad],
        fill=inner,
    )
    draw.ellipse(
        [cx + hw - cup_r + pad, cy - cup_r + pad, cx + hw + cup_r - pad, cy + cup_r - pad],
        fill=inner,
    )


def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, line = [], []
    for w in words:
        test = " ".join(line + [w])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_width and line:
            lines.append(" ".join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    return lines


def create_thumbnail(key: str, episode: tuple, out_path: Path):
    paper_key, line1, line2, topics, ep_label = episode
    accent = PAPER_COLOR[paper_key]
    paper_code, subject = PAPER_LABEL[paper_key]
    fonts = load_fonts()

    # ── Background ──────────────────────────────────────────────────────────
    bg = make_photo_bg() if STUDY_BG.exists() else make_gradient_bg()
    canvas = bg.convert("RGBA")

    # ── Left gradient overlay for text readability ───────────────────────────
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for x in range(W):
        t = 1 - max(0, (x - 650) / 500) if x > 650 else 1.0
        alpha = int(180 * t)
        ov_draw.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas, overlay)

    # ── Left accent stripe ───────────────────────────────────────────────────
    stripe = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(stripe)
    s_draw.rectangle([0, 0, 7, H], fill=accent + (255,))
    canvas = Image.alpha_composite(canvas, stripe)

    # ── Decorative headphones (right side, very faded) ───────────────────────
    hp_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hp_draw = ImageDraw.Draw(hp_layer)
    hp_color = accent + (38,)  # ~15% opacity
    draw_headphones(hp_draw, cx=1030, cy=340, size=340, color=hp_color)
    canvas = Image.alpha_composite(canvas, hp_layer)

    # ── Text ─────────────────────────────────────────────────────────────────
    draw = ImageDraw.Draw(canvas)
    PAD_L = 52

    # IES 2026 badge (top)
    badge_text = "IES 2026  ·  GENERAL ECONOMICS"
    draw.text((PAD_L, 46), badge_text, font=fonts["xs_reg"],
              fill=(*accent, 220))

    # Paper code + subject
    paper_info = f"{paper_code}  ·  {subject}"
    draw.text((PAD_L, 92), paper_info, font=fonts["md_bold"], fill=(240, 240, 255, 255))

    # Divider line
    draw.rectangle([PAD_L, 148, PAD_L + 320, 151], fill=(*accent, 180))

    # Main title (large) — two lines
    title_y = 175
    for line_text in [line1, line2]:
        draw.text((PAD_L, title_y), line_text, font=fonts["xl_bold"],
                  fill=(255, 255, 255, 255))
        bbox = draw.textbbox((PAD_L, title_y), line_text, font=fonts["xl_bold"])
        title_y = bbox[3] + 12

    # Topics bullet list
    topic_y = title_y + 22
    for topic in topics[:3]:
        dot_x, dot_y = PAD_L + 2, topic_y + 10
        draw.ellipse([dot_x, dot_y, dot_x + 6, dot_y + 6], fill=(*accent, 230))
        draw.text((PAD_L + 18, topic_y), topic, font=fonts["xs_reg"],
                  fill=(200, 200, 220, 210))
        topic_y += 30

    # Bottom bar
    bar_y = H - 68
    draw.rectangle([0, bar_y, W, H], fill=(0, 0, 0, 140))
    draw.text((PAD_L, bar_y + 14), ep_label, font=fonts["sm_reg"],
              fill=(*accent, 240))
    draw.text((PAD_L + 260, bar_y + 14), "Deep Dive Audio Lecture",
              font=fonts["sm_reg"], fill=(180, 180, 200, 200))

    # ── Save ─────────────────────────────────────────────────────────────────
    final = canvas.convert("RGB")
    final.save(str(out_path), "JPEG", quality=95)
    print(f"  ✓ {out_path.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", choices=["ge01", "ge02", "ge03", "ge04"])
    parser.add_argument("--open", action="store_true", dest="preview",
                        help="Open the first generated thumbnail in Preview")
    args = parser.parse_args()

    if STUDY_BG.exists():
        print(f"Using background photo: {STUDY_BG.name}")
    else:
        print("No study_bg.jpg found — using gradient background.")
        print("  Tip: place a 1280×720 study/headphone JPG at data/thumbnails/study_bg.jpg")

    keys = sorted(EPISODES.keys())
    if args.paper:
        keys = [k for k in keys if k.startswith(args.paper)]

    first_out = None
    for key in keys:
        out = THUMBNAIL_DIR / f"{key}.jpg"
        print(f"\n[{key}]")
        create_thumbnail(key, EPISODES[key], out)
        if first_out is None:
            first_out = out

    print(f"\nDone — {len(keys)} thumbnail(s) saved to data/thumbnails/")

    if args.preview and first_out:
        subprocess.run(["open", str(first_out)])


if __name__ == "__main__":
    main()
