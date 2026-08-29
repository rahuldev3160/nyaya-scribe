#!/usr/bin/env python3
"""
IES GE Model Answer PDF Generator
Outputs two PDFs to ~/Desktop in parallel:
  - IES_GE_YearWise_Model_Answers.pdf   (2025→2010, Paper I–IV each year)
  - IES_GE_TopicWise_Model_Answers.pdf  (30 topics sorted by priority score)
"""

import sqlite3, re, os, sys, json, multiprocessing
from collections import defaultdict
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    PageBreak, Table, TableStyle,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Page geometry ────────────────────────────────────────────────────────────
A4W, A4H = A4
MH = 15 * mm          # horizontal margin
MV = 20 * mm          # vertical margin (top/bottom)
CW = A4W - 2 * MH    # usable content width

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'data', 'ies.db')
OUT_DIR  = os.path.expanduser('~/Desktop')
EXAM_ID  = 'ies_2026'
PAPERS   = ['ge_01', 'ge_02', 'ge_03', 'ge_04']

PAPER_LABELS = {
    'ge_01': 'Paper I — Micro & Demand Theory',
    'ge_02': 'Paper II — Macro, Growth & Finance',
    'ge_03': 'Paper III — Public, Industrial & Environmental',
    'ge_04': 'Paper IV — Development, Trade & Labour',
}

# ── Palette ──────────────────────────────────────────────────────────────────
NAVY  = colors.HexColor('#1b3d6b')
BLUE  = colors.HexColor('#2e72c0')
LBLUE = colors.HexColor('#5a9fd4')
GREEN = colors.HexColor('#1a6b1a')
AMBER = colors.HexColor('#a05800')
CRIM  = colors.HexColor('#8b0000')
GREY  = colors.HexColor('#5c5c5c')
LGREY = colors.HexColor('#888888')
WHITE = colors.white

# ── Font registration ────────────────────────────────────────────────────────
def register_fonts():
    """Register unicode-capable fonts; return (regular_name, bold_name)."""
    pairs = [
        ('/Library/Fonts/Arial Unicode.ttf',
         '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
         'MyReg', 'MyBold'),
        ('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
         '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
         'MyReg', 'MyBold'),
        ('/System/Library/Fonts/Supplemental/Arial.ttf',
         '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
         'MyReg', 'MyBold'),
    ]
    for reg_p, bold_p, reg_n, bold_n in pairs:
        if not os.path.exists(reg_p):
            continue
        try:
            pdfmetrics.registerFont(TTFont(reg_n, reg_p))
            if os.path.exists(bold_p):
                pdfmetrics.registerFont(TTFont(bold_n, bold_p))
                return reg_n, bold_n
            return reg_n, 'Helvetica-Bold'
        except Exception:
            continue
    return 'Helvetica', 'Helvetica-Bold'


# ── Styles ───────────────────────────────────────────────────────────────────
def make_styles(FR, FB):
    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        # ── Cover
        'CvTitle' : S('CvTitle',  fontName=FB, fontSize=28, leading=34,
                       textColor=NAVY, alignment=TA_CENTER, spaceAfter=5*mm),
        'CvSub'   : S('CvSub',   fontName=FR, fontSize=15, leading=20,
                       textColor=BLUE, alignment=TA_CENTER, spaceAfter=3*mm),
        'CvStat'  : S('CvStat',  fontName=FR, fontSize=11, leading=15,
                       textColor=GREY, alignment=TA_CENTER, spaceAfter=2*mm),
        'CvNote'  : S('CvNote',  fontName=FR, fontSize=9,  leading=13,
                       textColor=LGREY, alignment=TA_CENTER, spaceAfter=1*mm),

        # ── Bar text (rendered inside colored Table cells)
        'BarLg'   : S('BarLg',   fontName=FB, fontSize=20, leading=25,
                       textColor=WHITE),
        'BarMd'   : S('BarMd',   fontName=FB, fontSize=13, leading=17,
                       textColor=WHITE),
        'BarSm'   : S('BarSm',   fontName=FR, fontSize=9.5, leading=13,
                       textColor=WHITE),

        # ── Question block
        'QMeta'   : S('QMeta',   fontName=FB, fontSize=7.5, leading=11,
                       textColor=LGREY, spaceBefore=4*mm, spaceAfter=0.8*mm),
        'QText'   : S('QText',   fontName=FB, fontSize=10.5, leading=15,
                       textColor=NAVY, spaceAfter=2*mm, alignment=TA_JUSTIFY),

        # ── Section labels
        'LblI'    : S('LblI',    fontName=FB, fontSize=8,  leading=11,
                       textColor=GREEN, spaceBefore=4*mm, spaceAfter=1*mm),
        'LblB'    : S('LblB',    fontName=FB, fontSize=8,  leading=11,
                       textColor=AMBER, spaceBefore=3*mm, spaceAfter=1*mm),
        'LblC'    : S('LblC',    fontName=FB, fontSize=8,  leading=11,
                       textColor=CRIM,  spaceBefore=3*mm, spaceAfter=1*mm),
        'LblK'    : S('LblK',    fontName=FB, fontSize=7.5, leading=10,
                       textColor=LGREY, spaceBefore=2*mm, spaceAfter=3*mm),

        # ── Body text
        'Body'    : S('Body',    fontName=FR, fontSize=9.5, leading=14,
                       textColor=colors.black, alignment=TA_JUSTIFY, spaceAfter=1.5*mm),
        'Bullet'  : S('Bullet',  fontName=FR, fontSize=9.5, leading=14,
                       textColor=colors.black, leftIndent=6*mm, spaceAfter=1*mm),
    }


# ── Text helpers ─────────────────────────────────────────────────────────────
def _esc(s):
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;'))

def _markup(line):
    """Convert **bold** to XML <b> after escaping."""
    parts = re.split(r'\*\*(.*?)\*\*', line)
    out = []
    for i, p in enumerate(parts):
        e = _esc(p)
        out.append(f'<b>{e}</b>' if i % 2 else e)
    return ''.join(out)

def text_flowables(text, body_sty, bullet_sty):
    """Convert multi-line markdown answer text → list of Paragraphs."""
    if not text:
        return []
    result = []
    for line in text.split('\n'):
        s = line.strip()
        if not s:
            result.append(Spacer(1, 2*mm))
            continue
        m = _markup(s)
        if s.startswith('•') or (len(s) > 2 and s[0] == '-' and s[1] == ' '):
            content = re.sub(r'^[•\-]\s*', '', m)
            result.append(Paragraph(f'• {content}', bullet_sty))
        else:
            result.append(Paragraph(m, body_sty))
    return result

def parse_terms(raw):
    if not raw:
        return []
    try:
        t = json.loads(raw)
        return t if isinstance(t, list) else []
    except Exception:
        return []

def strip_q_prefix(text):
    return re.sub(r'^Q\s*\d+[a-z]?[\.\s]+', '', text, flags=re.IGNORECASE, count=1)


# ── UI building blocks ───────────────────────────────────────────────────────
def bar(para, bg, pv=8, ph=12):
    """Colored Table-based header bar containing a Paragraph."""
    t = Table([[para]], colWidths=[CW])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), bg),
        ('TOPPADDING',    (0, 0), (-1, -1), pv),
        ('BOTTOMPADDING', (0, 0), (-1, -1), pv),
        ('LEFTPADDING',   (0, 0), (-1, -1), ph),
        ('RIGHTPADDING',  (0, 0), (-1, -1), ph),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t

def rule():
    return HRFlowable(width='100%', thickness=0.5, color=LBLUE,
                      spaceAfter=2*mm, spaceBefore=1*mm)


# ── Page header/footer callback ──────────────────────────────────────────────
def page_cb(title):
    def _draw(canvas, doc):
        if doc.page == 1:
            return
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillGray(0.55)
        y = A4H - MV + 5
        canvas.drawString(MH, y, title)
        canvas.drawRightString(A4W - MH, y, f'Page {doc.page}')
        canvas.setStrokeGray(0.80)
        canvas.line(MH, y - 3, A4W - MH, y - 3)
        canvas.restoreState()
    return _draw


# ── Cover page ────────────────────────────────────────────────────────────────
def cover(main_title, sub_title, stat_lines, note_lines, styles):
    elems = [Spacer(1, 45 * mm)]
    elems.append(Paragraph('IES General Economics', styles['CvTitle']))
    elems.append(Paragraph(main_title, styles['CvSub']))
    elems.append(Spacer(1, 8 * mm))
    for s in stat_lines:
        elems.append(Paragraph(s, styles['CvStat']))
    elems.append(Spacer(1, 6 * mm))
    elems.append(HRFlowable(width='60%', thickness=1, color=NAVY,
                             spaceAfter=5*mm, hAlign='CENTER'))
    for n in note_lines:
        elems.append(Paragraph(n, styles['CvNote']))
    elems.append(PageBreak())
    return elems


# ── Question + answer block ──────────────────────────────────────────────────
def q_block(row, styles):
    """Build flowables for one question + model answer row (dict)."""
    q_text = strip_q_prefix(row['question_text'])
    meta   = (f"[{row['year']}]  {PAPER_LABELS.get(row['paper_id'], row['paper_id'])}"
              f"  ·  {row['marks']} marks")

    elems = []
    elems.append(Paragraph(_esc(meta), styles['QMeta']))
    elems.append(Paragraph(_markup(q_text), styles['QText']))

    elems.append(Paragraph('▸ INTRODUCTION', styles['LblI']))
    elems.extend(text_flowables(row['intro_text'], styles['Body'], styles['Bullet']))

    elems.append(Paragraph('▸ MAIN ANALYSIS', styles['LblB']))
    elems.extend(text_flowables(row['body_text'],  styles['Body'], styles['Bullet']))

    elems.append(Paragraph('▸ CONCLUSION', styles['LblC']))
    elems.extend(text_flowables(row['conclusion_text'], styles['Body'], styles['Bullet']))

    terms = parse_terms(row.get('key_terms_used'))
    if terms:
        kstr = '  ·  '.join(terms[:7])
        elems.append(Paragraph(f'<i>Key terms: {_esc(kstr)}</i>', styles['LblK']))

    elems.append(rule())
    return elems


# ── YEAR-WISE PDF ─────────────────────────────────────────────────────────────
def generate_yearwise_pdf(db_path, output_path):
    FR, FB = register_fonts()
    styles = make_styles(FR, FB)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT pq.question_id, pq.year, pq.paper_id, pq.marks, pq.question_text,
               ma.intro_text, ma.body_text, ma.conclusion_text, ma.key_terms_used
        FROM pyq_questions pq
        JOIN model_answers ma
             ON pq.question_id = ma.question_id AND pq.exam_id = ma.exam_id
        WHERE pq.exam_id = ?
        ORDER BY pq.year DESC, pq.paper_id ASC, pq.question_id ASC
    """, (EXAM_ID,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    by_year_paper = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_year_paper[r['year']][r['paper_id']].append(r)
    years = sorted(by_year_paper.keys(), reverse=True)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=MV + 4, bottomMargin=MV,
        leftMargin=MH, rightMargin=MH,
        compress=1,
        title='IES GE Year-Wise Model Answers',
        author='Descriptive Exams Prep',
    )

    story = cover(
        'Year-Wise Model Answers (2025 → 2010)',
        f'All 4 Papers  ·  Generated {datetime.now().strftime("%d %b %Y")}',
        [f'{len(rows)} Questions  ·  {len(years)} Years  ·  4 Papers'],
        ['Sections: Introduction  |  Main Analysis  |  Conclusion'],
        styles,
    )

    for year in years:
        story.append(bar(Paragraph(str(year), styles['BarLg']), NAVY, pv=10, ph=14))
        story.append(Spacer(1, 4 * mm))

        for paper in PAPERS:
            qs = by_year_paper[year].get(paper, [])
            if not qs:
                continue
            label = f'{PAPER_LABELS[paper]}  —  {len(qs)} questions'
            story.append(bar(Paragraph(label, styles['BarSm']), BLUE, pv=5, ph=10))
            story.append(Spacer(1, 2 * mm))
            for row in qs:
                story.extend(q_block(row, styles))
            story.append(Spacer(1, 3 * mm))

        story.append(PageBreak())

    cb = page_cb('IES GE — Year-Wise Model Answers')
    doc.build(story, onFirstPage=cb, onLaterPages=cb)
    print(f'[DONE] Year-wise  → {output_path}')


# ── TOPIC-WISE PDF ────────────────────────────────────────────────────────────
def generate_topicwise_pdf(db_path, output_path):
    FR, FB = register_fonts()
    styles = make_styles(FR, FB)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT t.topic_id, t.topic_name, t.paper_id,
               tbs.base_priority_score, tbs.pyq_count, tbs.distinct_years,
               tbs.pyq_recurrence_score, tbs.ca_relevance_score,
               tbs.pyq_recency_score
        FROM topics t
        JOIN topic_base_scores tbs
             ON t.topic_id = tbs.topic_id AND t.exam_id = tbs.exam_id
        WHERE t.exam_id = ?
        ORDER BY tbs.base_priority_score DESC
    """, (EXAM_ID,))
    topics = [dict(r) for r in cur.fetchall()]

    cur.execute("""
        SELECT pq.question_id, pq.year, pq.paper_id, pq.marks, pq.question_text,
               pq.topic_id, pq.key_concepts,
               ma.intro_text, ma.body_text, ma.conclusion_text, ma.key_terms_used
        FROM pyq_questions pq
        JOIN model_answers ma
             ON pq.question_id = ma.question_id AND pq.exam_id = ma.exam_id
        WHERE pq.exam_id = ?
        ORDER BY pq.topic_id, pq.year DESC, pq.question_id ASC
    """, (EXAM_ID,))
    all_qs = [dict(r) for r in cur.fetchall()]
    conn.close()

    by_topic = defaultdict(list)
    for q in all_qs:
        by_topic[q['topic_id']].append(q)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=MV + 4, bottomMargin=MV,
        leftMargin=MH, rightMargin=MH,
        compress=1,
        title='IES GE Topic-Wise Model Answers (Priority Order)',
        author='Descriptive Exams Prep',
    )

    story = cover(
        'Topic-Wise Model Answers (Priority Order)',
        f'Highest-priority topics first  ·  Generated {datetime.now().strftime("%d %b %Y")}',
        [
            f'{len(all_qs)} Questions  ·  {len(topics)} Topics  ·  4 Papers',
        ],
        [
            'Priority score = weighted average of: PYQ frequency, recency,',
            'CA relevance, concept persistence & graph centrality',
        ],
        styles,
    )

    for rank, t in enumerate(topics, 1):
        tid = t['topic_id']
        qs  = by_topic.get(tid, [])
        if not qs:
            continue

        years_present = sorted({q['year'] for q in qs})
        yr_range = f'{years_present[0]}–{years_present[-1]}' if years_present else '—'
        yr_list  = '  '.join(str(y) for y in years_present)

        # ── Topic name bar
        story.append(bar(
            Paragraph(f'#{rank}  {_esc(t["topic_name"])}', styles['BarLg']),
            NAVY, pv=10, ph=14,
        ))

        # ── Stats bar
        stats = (
            f'{PAPER_LABELS.get(t["paper_id"], t["paper_id"])}  ·  '
            f'Priority: <b>{t["base_priority_score"]:.3f}</b>  ·  '
            f'{t["pyq_count"]} PYQs  ·  '
            f'{t["distinct_years"]}/16 years  ·  '
            f'Range: {yr_range}'
        )
        story.append(bar(Paragraph(stats, styles['BarSm']), BLUE, pv=5, ph=10))

        # ── Years map bar
        story.append(bar(
            Paragraph(f'Years asked: {_esc(yr_list)}', styles['BarSm']),
            LBLUE, pv=4, ph=10,
        ))
        story.append(Spacer(1, 4 * mm))

        # ── Questions
        for row in qs:
            story.extend(q_block(row, styles))

        story.append(PageBreak())

    cb = page_cb('IES GE — Topic-Wise Model Answers (Priority Order)')
    doc.build(story, onFirstPage=cb, onLaterPages=cb)
    print(f'[DONE] Topic-wise → {output_path}')


# ── Entry point ──────────────────────────────────────────────────────────────
def main():
    year_path  = os.path.join(OUT_DIR, 'IES_GE_YearWise_Model_Answers.pdf')
    topic_path = os.path.join(OUT_DIR, 'IES_GE_TopicWise_Model_Answers.pdf')

    print(f'Generating both PDFs in parallel...')
    print(f'  → {year_path}')
    print(f'  → {topic_path}')
    print()

    p1 = multiprocessing.Process(
        target=generate_yearwise_pdf,  args=(DB_PATH, year_path),  name='yearwise')
    p2 = multiprocessing.Process(
        target=generate_topicwise_pdf, args=(DB_PATH, topic_path), name='topicwise')

    p1.start()
    p2.start()

    p1.join()
    p2.join()

    if p1.exitcode == 0 and p2.exitcode == 0:
        # File sizes
        def sz(path):
            mb = os.path.getsize(path) / 1_048_576
            return f'{mb:.1f} MB'
        print()
        print('Both PDFs generated successfully!')
        print(f'  Year-wise  ({sz(year_path)})  → {year_path}')
        print(f'  Topic-wise ({sz(topic_path)}) → {topic_path}')
    else:
        codes = {'yearwise': p1.exitcode, 'topicwise': p2.exitcode}
        print(f'\nError — exit codes: {codes}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    multiprocessing.set_start_method('fork', force=True)
    main()
