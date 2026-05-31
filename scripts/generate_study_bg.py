#!/usr/bin/env python3.11
"""
Ghibli-style study-room illustration for thumbnail background.
- Coloured character (not a silhouette) with headphones
- 3-D book spines with titles on shelves all around
- Warm desk-lamp atmosphere
- "Audio Revision Economics Series" branding at bottom
Renders at 2× then down-samples for natural anti-aliasing.
"""
from pathlib import Path
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

PROJECT_ROOT = Path(__file__).parent.parent
OUT = PROJECT_ROOT / "data" / "thumbnails" / "study_bg.jpg"
W, H = 1280, 720

S = 2                    # super-sampling scale
WS, HS = W * S, H * S

random.seed(7)

# ── Fonts ─────────────────────────────────────────────────────────────────
def _font(size, bold=False):
    idx = 1 if bold else 0
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",
                                  size * S, index=idx)
    except Exception:
        return ImageFont.load_default()

# ── Colour palette ─────────────────────────────────────────────────────────
SKIN      = (238, 204, 168)
SKIN_SH   = (210, 172, 135)
HAIR      = (28, 16,  8)
HAIR_HI   = (65,  40, 22)
HOODIE    = (82, 102, 74)
HOODIE_SH = (60,  76, 54)
HOODIE_HI = (110, 135, 100)
HP        = (36,  32, 50)
HP_CUP    = (48,  44, 68)
HP_PAD    = (28,  24, 40)
HP_BAND   = (52,  48, 72)
EYE_W     = (245, 240, 228)
EYE_I     = (50,  30,  14)
EYE_P     = (10,   6,   2)
EYE_R     = (225, 232, 250)
BLUSH     = (215, 148, 130)
WALL      = (30,  18,  8)
SHELF     = (55,  36, 16)
SHELF_HI  = (72,  50, 24)
PAGE_TOP  = (215, 208, 192)
DESK_TOP  = (45,  28, 12)
DESK_BOT  = (30,  18,  6)

BOOK_PALETTE = [
    (148, 40, 35),  (38,  72, 145), (35, 105, 55),  (125,  95, 25),
    (85,  35, 115), (140, 70,  25), (28,  90, 105),  (148,  65, 42),
    (42, 115, 75),  (105, 38,  40), (35,  58, 115),  (110,  88, 25),
    (55,  35, 105), (120, 52,  24), (25,  85, 88),   (140,  78, 38),
    (95,  50,  30), (30,  68, 100), (50,  95,  48),  (130,  60, 30),
]

BOOK_TITLES = [
    "Economics", "History", "Philosophy", "Science",
    "Literature", "Politics", "Geography", "Mathematics",
    "Culture", "Finance", "Theory", "Analysis",
    "Practice", "Methods", "Studies", "Research",
    "Principles", "Concepts", "Foundations", "Dynamics",
]

DESK_Y  = int(HS * 0.68)   # desk surface y
HEAD_CX = int(WS * 0.60)   # character head centre x (slightly right of centre)
HEAD_CY = int(HS * 0.28)   # character head centre y


# ── Gradient helpers ───────────────────────────────────────────────────────
def vgrad(img, y0, y1, c0, c1):
    d = ImageDraw.Draw(img)
    for y in range(y0, y1 + 1):
        t = (y - y0) / max(y1 - y0, 1)
        c = tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
        d.line([(0, y), (WS, y)], fill=c)

def addglow(img, cx, cy, col, radius, strength=1.0):
    g = Image.new("RGB", (WS, HS))
    d = ImageDraw.Draw(g)
    r = max(radius // 10, 4)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    g = g.filter(ImageFilter.GaussianBlur(radius=radius))
    return ImageChops.add(img, g, scale=max(0.25, strength), offset=0)


# ── 3-D book on shelf ──────────────────────────────────────────────────────
def draw_book(draw, x, y_bot, w, h, color, title="", font_s=None):
    """Spine-facing book with page-top and optional title text."""
    # Shadow at base
    sh = tuple(max(0, c - 35) for c in color)
    draw.rectangle([x, y_bot - min(h, 20) * S, x + w, y_bot], fill=sh)
    # Main spine
    draw.rectangle([x, y_bot - h, x + w, y_bot - int(0.06 * h)], fill=color)
    # Left-edge highlight (simulates rounded spine)
    hi = tuple(min(255, c + 55) for c in color)
    draw.rectangle([x, y_bot - h, x + 4 * S, y_bot - int(0.06 * h)], fill=hi)
    # Right-edge slight shadow
    sk = tuple(max(0, c - 20) for c in color)
    draw.rectangle([x + w - 3 * S, y_bot - h, x + w, y_bot - int(0.06 * h)], fill=sk)
    # Page-top edge
    draw.rectangle([x, y_bot - h, x + w, y_bot - h + 9 * S], fill=PAGE_TOP)
    # Title text on spine (rotated via separate layer)
    if title and w > 20 * S and font_s:
        try:
            txt_img = Image.new("RGBA", (h, w), (0, 0, 0, 0))
            td = ImageDraw.Draw(txt_img)
            tc = (255, 255, 255, 180)
            td.text((10 * S, max(1, (w - font_s.getlength(title)) // 2)),
                    title, fill=tc, font=font_s)
            txt_img = txt_img.rotate(90, expand=True)
            # paste onto main image
            draw._image.paste(txt_img, (x, y_bot - h), txt_img)
        except Exception:
            pass


# ── Bookshelf row ──────────────────────────────────────────────────────────
def shelf_row(draw, y_bot, x0, x1, h_min, h_max, font_s=None):
    # Shelf board
    draw.rectangle([x0, y_bot, x1, y_bot + 10 * S], fill=SHELF)
    draw.rectangle([x0, y_bot, x1, y_bot + 3 * S], fill=SHELF_HI)
    # Books
    x = x0 + random.randint(0, 4) * S
    i = 0
    while x < x1 - 14 * S:
        bw = random.randint(18, 48) * S
        bh = random.randint(h_min, h_max) * S
        bc = random.choice(BOOK_PALETTE)
        title = random.choice(BOOK_TITLES) if random.random() > 0.45 else ""
        draw_book(draw, x, y_bot, bw, bh, bc, title, font_s)
        x += bw + random.randint(2, 5) * S
        i += 1


# ── Main scene ─────────────────────────────────────────────────────────────
def make_scene() -> Image.Image:
    img = Image.new("RGB", (WS, HS))
    draw = ImageDraw.Draw(img)
    font_book  = _font(11)
    font_brand = _font(22, bold=True)
    font_brand_sm = _font(15)

    # 1. Wall background
    vgrad(img, 0, DESK_Y,   (28, 16, 6),  (22, 12, 4))
    vgrad(img, DESK_Y, HS,  DESK_TOP,     DESK_BOT)

    # 2. Bookshelves — 4 rows across full width
    shelf_ys = [int(HS * t) for t in [0.26, 0.45, 0.64, 0.79]]
    h_ranges = [(110, 175), (100, 165), (90, 155), (80, 130)]
    for sy, (hmin, hmax) in zip(shelf_ys, h_ranges):
        shelf_row(draw, sy, 0, WS, hmin, hmax, font_book)

    # 3. Shelf vertical dividers (like a real bookcase)
    for x in [int(WS * t) for t in [0.25, 0.50, 0.75]]:
        draw.rectangle([x - 6, 0, x + 6, shelf_ys[-1] + 12 * S], fill=SHELF)

    # 4. Atmospheric vignette
    img = img.convert("RGBA")
    vig = Image.new("RGBA", (WS, HS), (0, 0, 0, 0))
    vd  = ImageDraw.Draw(vig)
    # Top
    for y in range(int(HS * 0.15)):
        a = int(180 * (1 - y / (HS * 0.15)))
        vd.line([(0, y), (WS, y)], fill=(0, 0, 0, a))
    # Side edges
    for x in range(int(WS * 0.18)):
        a = int(155 * (1 - x / (WS * 0.18)))
        vd.line([(x, 0), (x, HS)], fill=(0, 0, 0, a))
        vd.line([(WS - 1 - x, 0), (WS - 1 - x, HS)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img, vig).convert("RGB")

    # 5. Warm desk-lamp glow centred on student
    GLOW_X, GLOW_Y = HEAD_CX, HEAD_CY - int(HS * 0.06)
    img = addglow(img, GLOW_X, GLOW_Y, (255, 215, 140), 350, 0.75)
    img = addglow(img, GLOW_X, GLOW_Y, (255, 185, 90),  520, 0.52)
    img = addglow(img, GLOW_X, GLOW_Y, (195, 140, 55),  700, 0.38)
    img = addglow(img, HEAD_CX, DESK_Y, (180, 125, 55), 280, 0.50)

    draw = ImageDraw.Draw(img)

    # 6. Desk edge
    draw.rectangle([0, DESK_Y, WS, DESK_Y + 4 * S], fill=(78, 55, 26))

    # 7. Open book on desk (left of character, visible to reader)
    BX, BY = int(WS * 0.08), DESK_Y + 18 * S
    PW, PH = 185 * S, 75 * S
    # Left page
    draw.polygon([(BX, BY + PH), (BX + PW, BY + 12),
                  (BX + PW, BY + 12 + PH), (BX, BY + PH + PH)],
                 fill=(218, 210, 195))
    # Right page
    draw.polygon([(BX + PW, BY + 12), (BX + 2 * PW, BY + PH),
                  (BX + 2 * PW, BY + PH + PH), (BX + PW, BY + 12 + PH)],
                 fill=(208, 200, 185))
    # Lines
    for i in range(5):
        yy = BY + 30 + i * (PH // 5)
        draw.line([(BX + 15, yy), (BX + PW - 15, yy)], fill=(165, 155, 138), width=S)
        draw.line([(BX + PW + 15, yy), (BX + 2 * PW - 15, yy)],
                  fill=(155, 145, 128), width=S)
    draw.line([(BX + PW, BY + 12), (BX + PW, BY + 12 + PH)],
              fill=(185, 172, 155), width=2 * S)

    # 8. Stack of books on desk (right side)
    sx, sy2 = int(WS * 0.82), DESK_Y
    for tw, bc in [(155, (112, 42, 30)), (155, (30, 62, 118)), (155, (35, 98, 52))]:
        th = 14 * S
        draw.rectangle([sx, sy2 - th, sx + tw * S, sy2], fill=bc)
        draw.rectangle([sx, sy2 - th, sx + tw * S, sy2 - th + 3 * S],
                       fill=tuple(min(255, c + 35) for c in bc))
        sy2 -= th

    # 9. Mug — large, prominent, warm colours, dramatic steam
    MX = int(WS * 0.835)
    MY = DESK_Y
    MW = 58 * S   # much wider
    MH = 78 * S   # much taller
    # Shadow under mug
    shd = Image.new("RGBA", (WS, HS), (0, 0, 0, 0))
    shdd = ImageDraw.Draw(shd)
    shdd.ellipse([MX - 8 * S, MY + MH - 6 * S,
                  MX + MW + 8 * S, MY + MH + 10 * S], fill=(0, 0, 0, 80))
    shd = shd.filter(ImageFilter.GaussianBlur(radius=6 * S))
    img = Image.alpha_composite(img.convert("RGBA"), shd).convert("RGB")
    draw = ImageDraw.Draw(img)
    # Mug body (ceramic, warm brown-red)
    MUG_COLOR  = (148, 72, 38)
    MUG_INNER  = (62, 30, 12)
    MUG_SHINE  = (188, 112, 68)
    draw.rounded_rectangle([MX, MY + 5 * S, MX + MW, MY + MH],
                           radius=10 * S, fill=MUG_COLOR)
    # Inside rim (dark coffee)
    draw.ellipse([MX + 5 * S, MY + 4 * S,
                  MX + MW - 5 * S, MY + 22 * S], fill=MUG_INNER)
    # Coffee surface (dark liquid)
    draw.ellipse([MX + 7 * S, MY + 6 * S,
                  MX + MW - 7 * S, MY + 20 * S], fill=(30, 14, 6))
    # Handle (right side)
    draw.arc([MX + MW - 6 * S, MY + 18 * S,
              MX + MW + 32 * S, MY + 52 * S],
             start=270, end=90, fill=MUG_COLOR, width=10 * S)
    # Ceramic shine highlight (left side)
    draw.rounded_rectangle([MX + 8 * S, MY + 14 * S,
                             MX + 18 * S, MY + 40 * S],
                           radius=5 * S, fill=(*MUG_SHINE, 0))
    draw.arc([MX + 6 * S, MY + 12 * S, MX + 20 * S, MY + 44 * S],
             start=210, end=330, fill=MUG_SHINE, width=4 * S)
    # "IES" text on mug (like a branded mug)
    try:
        mug_font = _font(13, bold=True)
        draw.text((MX + 20 * S, MY + 38 * S), "IES", fill=(188, 100, 52), font=mug_font)
    except Exception:
        pass

    # Dramatic steam wisps — 3 large curling plumes
    steam_layer = Image.new("RGBA", (WS, HS), (0, 0, 0, 0))
    sd = ImageDraw.Draw(steam_layer)
    # Wisp 1 — left, curls left
    for j in range(8):
        y_off   = MY - (20 + j * 18) * S
        x_drift = int(-12 * (j / 8) ** 1.5) * S
        alpha   = max(0, 140 - j * 16)
        width   = max(1, (5 - j // 2)) * S
        if j < 7:
            sd.arc([MX + 5 * S + x_drift,      y_off - 12 * S,
                    MX + 24 * S + x_drift,      y_off + 4 * S],
                   start=200 + j * 8, end=360 + j * 5,
                   fill=(210, 205, 220, alpha), width=width)
    # Wisp 2 — centre, rises straight then curls right
    for j in range(10):
        y_off   = MY - (15 + j * 16) * S
        x_drift = int(10 * (j / 10) ** 1.4) * S
        alpha   = max(0, 160 - j * 14)
        width   = max(1, (6 - j // 2)) * S
        if j < 9:
            sd.arc([MX + MW // 2 - 10 * S + x_drift, y_off - 14 * S,
                    MX + MW // 2 + 10 * S + x_drift, y_off + 4 * S],
                   start=180 - j * 6, end=350 - j * 4,
                   fill=(215, 212, 225, alpha), width=width)
    # Wisp 3 — right, curls right then bends left at top
    for j in range(7):
        y_off   = MY - (25 + j * 20) * S
        x_drift = int(14 * (j / 7) ** 1.3 - 5) * S
        alpha   = max(0, 130 - j * 16)
        width   = max(1, (4 - j // 2)) * S
        if j < 6:
            sd.arc([MX + MW - 22 * S + x_drift, y_off - 12 * S,
                    MX + MW - 4 * S + x_drift,  y_off + 4 * S],
                   start=160 + j * 10, end=340 + j * 7,
                   fill=(205, 200, 218, alpha), width=width)
    steam_layer = steam_layer.filter(ImageFilter.GaussianBlur(radius=3 * S))
    img = Image.alpha_composite(img.convert("RGBA"), steam_layer).convert("RGB")
    draw = ImageDraw.Draw(img)
    # Warm glow around mug (from hot coffee)
    img = addglow(img, MX + MW // 2, MY + MH // 2,
                  (180, 100, 40), 120, 0.60)

    # ── 10. CHARACTER (Ghibli style) ────────────────────────────────────────
    HX, HY   = HEAD_CX, HEAD_CY
    HRX, HRY = 88 * S, 105 * S    # head x/y radii
    SW       = 175 * S            # shoulder half-width

    # Body / hoodie (trapezoid, widest at bottom)
    draw.polygon([
        (HX - SW,       DESK_Y + 20 * S),
        (HX + SW,       DESK_Y + 20 * S),
        (HX + SW - 15 * S, HY + HRY + 5 * S),
        (HX - SW + 15 * S, HY + HRY + 5 * S),
    ], fill=HOODIE)
    # Hoodie centre seam + pocket
    draw.rectangle([HX - 18 * S, HY + HRY + 45 * S,
                    HX + 18 * S, DESK_Y - 5 * S], fill=HOODIE_SH)

    # Hoodie highlight (shoulder area)
    draw.ellipse([HX - SW, HY + HRY,
                  HX + SW, HY + HRY + 60 * S], fill=HOODIE_HI)
    draw.ellipse([HX - SW + 5 * S, HY + HRY + 5 * S,
                  HX + SW - 5 * S, HY + HRY + 55 * S], fill=HOODIE)

    # Arms resting on desk
    ARM_W = 52 * S
    # Left arm
    draw.polygon([
        (HX - SW + 12 * S, HY + HRY + 8 * S),
        (HX - SW + 12 * S + ARM_W, HY + HRY + 8 * S),
        (HX - 210 * S, DESK_Y),
        (HX - 210 * S - ARM_W + 20 * S, DESK_Y),
    ], fill=HOODIE)
    # Right arm
    draw.polygon([
        (HX + SW - 12 * S - ARM_W, HY + HRY + 8 * S),
        (HX + SW - 12 * S, HY + HRY + 8 * S),
        (HX + 210 * S + ARM_W - 20 * S, DESK_Y),
        (HX + 210 * S, DESK_Y),
    ], fill=HOODIE)
    # Forearms on desk
    draw.rectangle([HX - 268 * S, DESK_Y, HX - 160 * S, DESK_Y + 22 * S], fill=HOODIE)
    draw.rectangle([HX + 160 * S, DESK_Y, HX + 268 * S, DESK_Y + 22 * S], fill=HOODIE)

    # Neck
    draw.rectangle([HX - 26 * S, HY + HRY - 14 * S,
                    HX + 26 * S, HY + HRY + 10 * S], fill=SKIN_SH)
    draw.rectangle([HX - 22 * S, HY + HRY - 12 * S,
                    HX + 22 * S, HY + HRY + 8 * S], fill=SKIN)

    # ── Hair (back layer, larger than head) ─────────────────────────────────
    draw.ellipse([HX - HRX - 14 * S, HY - HRY - 30 * S,
                  HX + HRX + 14 * S, HY + HRY + 10 * S], fill=HAIR)
    # Side hair flowing down
    draw.polygon([
        (HX - HRX - 14 * S, HY),
        (HX - HRX - 8 * S, HY),
        (HX - HRX - 20 * S, HY + HRY + 80 * S),
        (HX - HRX - 55 * S, HY + HRY + 60 * S),
    ], fill=HAIR)
    draw.polygon([
        (HX + HRX + 8 * S, HY),
        (HX + HRX + 14 * S, HY),
        (HX + HRX + 50 * S, HY + HRY + 55 * S),
        (HX + HRX + 18 * S, HY + HRY + 75 * S),
    ], fill=HAIR)

    # ── Face / head ─────────────────────────────────────────────────────────
    draw.ellipse([HX - HRX, HY - HRY, HX + HRX, HY + HRY], fill=SKIN)
    # Soft cheek shading
    for cx_, cy_, rx_, ry_ in [
        (HX - 58 * S, HY + 20 * S, 32 * S, 20 * S),
        (HX + 58 * S, HY + 20 * S, 32 * S, 20 * S),
    ]:
        ch = Image.new("RGBA", (WS, HS), (0, 0, 0, 0))
        cd = ImageDraw.Draw(ch)
        cd.ellipse([cx_ - rx_, cy_ - ry_, cx_ + rx_, cy_ + ry_],
                   fill=(*BLUSH, 75))
        ch = ch.filter(ImageFilter.GaussianBlur(radius=14 * S))
        img = Image.alpha_composite(img.convert("RGBA"), ch).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── Eyes (large, Ghibli-style) ──────────────────────────────────────────
    E_RX, E_RY = 22 * S, 26 * S
    for ex, ey in [(HX - 38 * S, HY - 12 * S), (HX + 38 * S, HY - 12 * S)]:
        # White
        draw.ellipse([ex - E_RX, ey - E_RY, ex + E_RX, ey + E_RY], fill=EYE_W)
        # Iris
        draw.ellipse([ex - 16 * S, ey - 18 * S, ex + 16 * S, ey + 18 * S], fill=EYE_I)
        # Pupil
        draw.ellipse([ex - 9 * S, ey - 10 * S, ex + 9 * S, ey + 10 * S], fill=EYE_P)
        # Main reflection (top-left)
        draw.ellipse([ex - 10 * S, ey - 15 * S, ex - 2 * S, ey - 8 * S], fill=EYE_R)
        # Small secondary reflection
        draw.ellipse([ex + 5 * S, ey + 4 * S, ex + 10 * S, ey + 9 * S], fill=EYE_R)
        # Eye outline / lash line (top)
        draw.arc([ex - E_RX, ey - E_RY, ex + E_RX, ey + E_RY],
                 start=200, end=340, fill=(12, 8, 4), width=4 * S)

    # Eyebrows (gentle arched)
    for ex in [HX - 38 * S, HX + 38 * S]:
        draw.arc([ex - 26 * S, HY - 55 * S, ex + 26 * S, HY - 30 * S],
                 start=205, end=335, fill=HAIR, width=5 * S)

    # Nose (Ghibli: tiny, just a small soft shape)
    draw.ellipse([HX - 5 * S, HY + 22 * S, HX + 5 * S, HY + 30 * S],
                 fill=SKIN_SH)

    # Mouth (small, gentle upward smile)
    draw.arc([HX - 20 * S, HY + 40 * S, HX + 20 * S, HY + 65 * S],
             start=15, end=165, fill=(185, 118, 98), width=4 * S)

    # Hair fringe / fringe over forehead
    draw.polygon([
        (HX - HRX + 5 * S, HY - HRY - 5 * S),
        (HX - HRX - 10 * S, HY - 30 * S),
        (HX - 50 * S, HY - HRY + 18 * S),
    ], fill=HAIR)
    draw.polygon([
        (HX - HRX - 10 * S, HY - 30 * S),
        (HX - 18 * S, HY - HRY + 8 * S),
        (HX - 12 * S, HY - HRY + 22 * S),
        (HX - 55 * S, HY - HRY + 28 * S),
    ], fill=HAIR)
    draw.polygon([
        (HX - 18 * S, HY - HRY + 8 * S),
        (HX + 18 * S, HY - HRY + 8 * S),
        (HX + 8 * S, HY - HRY + 40 * S),
        (HX - 8 * S, HY - HRY + 40 * S),
    ], fill=HAIR)
    draw.polygon([
        (HX + 18 * S, HY - HRY + 8 * S),
        (HX + HRX + 10 * S, HY - 28 * S),
        (HX + 50 * S, HY - HRY + 30 * S),
        (HX + 10 * S, HY - HRY + 22 * S),
    ], fill=HAIR)
    draw.polygon([
        (HX + HRX + 10 * S, HY - 28 * S),
        (HX + HRX - 5 * S, HY - HRY - 5 * S),
        (HX + 52 * S, HY - HRY + 18 * S),
    ], fill=HAIR)
    # Hair highlight strand
    draw.arc([HX - 60 * S, HY - HRY - 25 * S, HX + 20 * S, HY - HRY + 20 * S],
             start=195, end=295, fill=HAIR_HI, width=3 * S)

    # Ear (just visible under hair)
    for ex, sign in [(HX - HRX + 6 * S, -1), (HX + HRX - 6 * S, 1)]:
        draw.ellipse([ex - 14 * S, HY - 8 * S, ex + 14 * S, HY + 22 * S], fill=SKIN)
        draw.ellipse([ex + sign * 2 * S - 8 * S, HY - 2 * S,
                      ex + sign * 2 * S + 8 * S, HY + 16 * S], fill=SKIN_SH)

    # ── Headphones ─────────────────────────────────────────────────────────
    HP_HALF = 110 * S   # half-span
    CUP_RX  = 30 * S
    CUP_RY  = 36 * S
    LCX = HX - HP_HALF
    RCX = HX + HP_HALF
    CY  = HY - 8 * S

    # Headband (over top of hair)
    draw.arc([HX - HP_HALF + CUP_RX - 8 * S, HY - HRY - 36 * S,
              HX + HP_HALF - CUP_RX + 8 * S, HY + 18 * S],
             start=200, end=340, fill=HP_BAND, width=12 * S)
    # Band highlight stripe
    draw.arc([HX - HP_HALF + CUP_RX - 8 * S, HY - HRY - 36 * S,
              HX + HP_HALF - CUP_RX + 8 * S, HY + 18 * S],
             start=215, end=325, fill=HP_CUP, width=4 * S)

    for cx_ in [LCX, RCX]:
        # Outer shell
        draw.ellipse([cx_ - CUP_RX, CY - CUP_RY,
                      cx_ + CUP_RX, CY + CUP_RY], fill=HP)
        # Cup body
        draw.ellipse([cx_ - CUP_RX + 4 * S, CY - CUP_RY + 4 * S,
                      cx_ + CUP_RX - 4 * S, CY + CUP_RY - 4 * S], fill=HP_CUP)
        # Cushion / pad
        draw.ellipse([cx_ - CUP_RX + 10 * S, CY - CUP_RY + 10 * S,
                      cx_ + CUP_RX - 10 * S, CY + CUP_RY - 10 * S], fill=HP_PAD)
        # Rim highlight (top-left arc)
        draw.arc([cx_ - CUP_RX, CY - CUP_RY, cx_ + CUP_RX, CY + CUP_RY],
                 start=205, end=325, fill=(75, 68, 95), width=3 * S)

    # Blue LED on right cup
    draw.ellipse([RCX + 18 * S, CY - 24 * S,
                  RCX + 26 * S, CY - 16 * S], fill=(75, 118, 225))

    # ── 11. Rim light on character (warm, from overhead) ───────────────────
    rim = Image.new("RGBA", (WS, HS), (0, 0, 0, 0))
    rd  = ImageDraw.Draw(rim)
    rd.arc([HX - HRX, HY - HRY, HX + HRX, HY + HRY],
           start=210, end=330, fill=(215, 165, 80, 130), width=6 * S)
    rd.line([(HX - SW + 20 * S, HY + HRY + 10 * S),
             (HX + SW - 20 * S, HY + HRY + 10 * S)],
            fill=(185, 135, 60, 90), width=5 * S)
    rim = rim.filter(ImageFilter.GaussianBlur(radius=5 * S))
    img = Image.alpha_composite(img.convert("RGBA"), rim).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── 12. Branding text "Audio Revision Economics Series" ─────────────────
    TEXT_Y = HS - 60 * S
    label  = "Audio Revision Economics Series"
    # Background pill
    bbox   = draw.textbbox((0, 0), label, font=font_brand)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    TX     = (WS - tw) // 2
    PAD    = 14 * S
    draw.rounded_rectangle(
        [TX - PAD, TEXT_Y - PAD, TX + tw + PAD, TEXT_Y + th + PAD],
        radius=18 * S, fill=(0, 0, 0, 0)
    )
    # Gold text with subtle shadow
    draw.text((TX + 2 * S, TEXT_Y + 2 * S), label,
              fill=(100, 75, 20), font=font_brand)
    draw.text((TX, TEXT_Y), label,
              fill=(225, 185, 80), font=font_brand)
    # Subtitle
    sub    = "IES 2026  ·  General Economics  ·  Deep Dive Audio"
    sbbox  = draw.textbbox((0, 0), sub, font=font_brand_sm)
    sw2    = sbbox[2] - sbbox[0]
    draw.text(((WS - sw2) // 2, TEXT_Y + th + 8 * S),
              sub, fill=(175, 148, 82), font=font_brand_sm)

    # ── 13. Final warm overlay ──────────────────────────────────────────────
    warm = Image.new("RGBA", (WS, HS), (75, 48, 8, 15))
    img  = Image.alpha_composite(img.convert("RGBA"), warm).convert("RGB")

    # ── 14. Down-sample (anti-aliasing) ────────────────────────────────────
    img = img.resize((W, H), Image.LANCZOS)
    return img


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print("Generating Ghibli-style study background…")
    scene = make_scene()
    scene.save(str(OUT), "JPEG", quality=96)
    print(f"Saved → {OUT}")
    import subprocess
    subprocess.run(["open", str(OUT)])


if __name__ == "__main__":
    main()
