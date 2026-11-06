#!/usr/bin/env python3
"""
generate_report.py
Data-driven UE Memory Audit PDF report generator.

Usage:
    pip install reportlab --break-system-packages
    python3 generate_report.py <path/to/report_data.json> <path/to/output.pdf>
"""

import sys, json
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── ARGS ──────────────────────────────────────────────────────────────────────
if len(sys.argv) < 3:
    print("Usage: python3 generate_report.py <report_data.json> <output.pdf>")
    sys.exit(1)

with open(sys.argv[1], encoding='utf-8') as f:
    D = json.load(f)
OUT_PATH = sys.argv[2]

meta     = D.get('meta', {})
PROJECT  = meta.get('project',  'Unknown Project')
BUILD    = meta.get('build',    'MemReport')
DATE_STR = meta.get('date',     '')
SOURCE   = meta.get('source',   f'{PROJECT} MemReport')

# ── COLOURS ───────────────────────────────────────────────────────────────────
BLUE_DARK  = colors.HexColor('#1F3864')
BLUE_MED   = colors.HexColor('#2E75B6')
RED_BG     = colors.HexColor('#FFE0E0')
AMBER_BG   = colors.HexColor('#FFF3CD')
GREEN_BG   = colors.HexColor('#E8F5E9')
GREY_BG    = colors.HexColor('#F5F5F5')
WHITE      = colors.white
RED_TEXT   = colors.HexColor('#CC0000')
AMBER_TEXT = colors.HexColor('#CC5500')
GREEN_TEXT = colors.HexColor('#006600')
GREY_TEXT  = colors.HexColor('#555555')

def hex_color(h):
    h = h.lstrip('#')
    return colors.HexColor(f'#{h}')

# ── PAGE GEOMETRY ─────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = letter          # 612 × 792 pt
MARGIN = 0.75 * inch             # 54 pt
BODY_W = PAGE_W - 2 * MARGIN    # 504 pt

# ── STYLES ────────────────────────────────────────────────────────────────────
def S(name, **kw):
    base = kw.pop('parent', 'Normal')
    return ParagraphStyle(name, **kw)

sH1 = S('H1', fontName='Helvetica-Bold', fontSize=16, textColor=BLUE_DARK,
         spaceBefore=18, spaceAfter=6, leading=20)
sH2 = S('H2', fontName='Helvetica-Bold', fontSize=13, textColor=BLUE_MED,
         spaceBefore=14, spaceAfter=4, leading=16)
sH3 = S('H3', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#333333'),
         spaceBefore=10, spaceAfter=3)
sBody = S('Body', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#333333'),
          spaceBefore=3, spaceAfter=3, leading=13)
sBullet = S('Bullet', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#333333'),
            leftIndent=16, firstLineIndent=-10, spaceBefore=2, spaceAfter=2, leading=13)
sSmall = S('Small', fontName='Helvetica', fontSize=8, textColor=GREY_TEXT,
           spaceBefore=2, spaceAfter=2)
sStatVal = S('StatVal', fontName='Helvetica-Bold', fontSize=16, leading=20)
sStatLbl = S('StatLbl', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#444444'), leading=11)
sStatSub = S('StatSub', fontName='Helvetica', fontSize=7, textColor=colors.HexColor('#888888'), leading=10)
sCellBold = S('CellBold', fontName='Helvetica-Bold', fontSize=8, leading=11)
sCell = S('Cell', fontName='Helvetica', fontSize=8, leading=11)
sCellSm = S('CellSm', fontName='Helvetica', fontSize=7.5, textColor=GREY_TEXT, leading=10)
sCellR = S('CellR', fontName='Helvetica', fontSize=8, alignment=TA_RIGHT, leading=11)
sCellRC= S('CellRC',fontName='Helvetica-Bold', fontSize=8, alignment=TA_RIGHT, leading=11)
sCellCenter = S('CellCenter', fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER, leading=11)

BASE_TABLE_STYLE = [
    ('GRID',        (0, 0), (-1, -1), 0.4, colors.HexColor('#CCCCCC')),
    ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING',  (0, 0), (-1, -1), 4),
    ('BOTTOMPADDING',(0,0), (-1, -1), 4),
    ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ('RIGHTPADDING',(0, 0), (-1, -1), 5),
]

HEADER_ROW_STYLE = [
    ('BACKGROUND',  (0, 0), (-1, 0), BLUE_DARK),
    ('TEXTCOLOR',   (0, 0), (-1, 0), WHITE),
    ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE',    (0, 0), (-1, 0), 8),
    ('TOPPADDING',  (0, 0), (-1, 0), 5),
    ('BOTTOMPADDING',(0,0), (-1, 0), 5),
]

def zebra(num_rows, start=1, c0=WHITE, c1=GREY_BG):
    """Return TableStyle entries for alternating row backgrounds (rows start..num_rows)."""
    cmds = []
    for i in range(start, num_rows):
        bg = c0 if (i % 2 == 0) else c1
        cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
    return cmds

def hdr(text):
    return Paragraph(f'<font color="white"><b>{text}</b></font>', sCell)

def P(text, style=sBody):
    return Paragraph(str(text) if text is not None else '', style)

def spacer(h=8):
    return Spacer(1, h)

def hr():
    return HRFlowable(width='100%', thickness=0.5, color=BLUE_MED, spaceAfter=4, spaceBefore=4)

def bullet_item(text):
    return Paragraph(f'• {text}', sBullet)

# ── PAGE HEADER / FOOTER ──────────────────────────────────────────────────────
def _on_page(canvas, doc):
    canvas.saveState()
    # Header
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#888888'))
    canvas.drawString(MARGIN, PAGE_H - MARGIN + 10, f'{PROJECT} — Memory Audit')
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN + 10, DATE_STR)
    canvas.setStrokeColor(colors.HexColor('#CCCCCC'))
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, PAGE_H - MARGIN + 6, PAGE_W - MARGIN, PAGE_H - MARGIN + 6)
    # Footer
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(colors.HexColor('#AAAAAA'))
    canvas.drawString(MARGIN, MARGIN - 14, f'Generated from {BUILD} MemReport')
    canvas.drawRightString(PAGE_W - MARGIN, MARGIN - 14, f'Page {doc.page}')
    canvas.line(MARGIN, MARGIN - 8, PAGE_W - MARGIN, MARGIN - 8)
    canvas.restoreState()

# ── STAT BOX TABLE ────────────────────────────────────────────────────────────
def stat_table(stats):
    n = len(stats)
    col_w = BODY_W / n
    data = []
    row_cells = []
    style_cmds = list(BASE_TABLE_STYLE)

    for i, s in enumerate(stats):
        fill   = hex_color(s.get('fill', '2E75B6'))
        bg     = hex_color(s.get('bg',   'F5F5F5'))
        val_p  = Paragraph(f'<font color="#{s.get("fill","2E75B6")}" size="18"><b>{s["value"]}</b></font>', sStatVal)
        lbl_p  = Paragraph(f'<b>{s["label"]}</b>', sStatLbl)
        sub_p  = Paragraph(s.get('sub', ''), sStatSub)
        row_cells.append([val_p, lbl_p, sub_p])

        style_cmds += [
            ('BACKGROUND',   (i, 0), (i, 0), bg),
            ('LINEABOVE',    (i, 0), (i, 0), 3, fill),
            ('LEFTPADDING',  (i, 0), (i, 0), 8),
            ('RIGHTPADDING', (i, 0), (i, 0), 8),
            ('TOPPADDING',   (i, 0), (i, 0), 8),
            ('BOTTOMPADDING',(i, 0), (i, 0), 8),
        ]

    # We build a sub-table per cell (value/label/sub stacked vertically)
    outer_data = [[]]
    for i, s in enumerate(stats):
        fill = hex_color(s.get('fill', '2E75B6'))
        bg   = hex_color(s.get('bg',   'F5F5F5'))
        inner = Table([
            [Paragraph(f'<font color="#{s.get("fill","2E75B6")}"><b>{s["value"]}</b></font>',
                       ParagraphStyle('sv', fontName='Helvetica-Bold', fontSize=16, leading=20))],
            [Paragraph(f'<b>{s["label"]}</b>',
                       ParagraphStyle('sl', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#444444'), leading=11))],
            [Paragraph(s.get('sub', ''),
                       ParagraphStyle('ss', fontName='Helvetica', fontSize=7, textColor=colors.HexColor('#888888'), leading=10))],
        ], colWidths=[col_w - 16])
        inner.setStyle(TableStyle([
            ('LEFTPADDING',  (0,0),(-1,-1), 0),
            ('RIGHTPADDING', (0,0),(-1,-1), 0),
            ('TOPPADDING',   (0,0),(-1,-1), 2),
            ('BOTTOMPADDING',(0,0),(-1,-1), 1),
            ('VALIGN',       (0,0),(-1,-1), 'TOP'),
        ]))
        cell_tbl = Table([[inner]], colWidths=[col_w])
        cell_tbl.setStyle(TableStyle([
            ('BACKGROUND',   (0,0),(0,0), bg),
            ('LINEABOVE',    (0,0),(0,0), 3, fill),
            ('LINEBELOW',    (0,0),(0,0), 0, WHITE),
            ('LINEBEFORE',   (0,0),(0,0), 0, WHITE),
            ('LINEAFTER',    (0,0),(0,0), 0, WHITE),
            ('LEFTPADDING',  (0,0),(0,0), 8),
            ('RIGHTPADDING', (0,0),(0,0), 8),
            ('TOPPADDING',   (0,0),(0,0), 8),
            ('BOTTOMPADDING',(0,0),(0,0), 8),
        ]))
        outer_data[0].append(cell_tbl)

    outer = Table(outer_data, colWidths=[col_w] * n)
    outer.setStyle(TableStyle([
        ('LEFTPADDING',  (0,0),(-1,-1), 0),
        ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('TOPPADDING',   (0,0),(-1,-1), 0),
        ('BOTTOMPADDING',(0,0),(-1,-1), 0),
        ('VALIGN',       (0,0),(-1,-1), 'TOP'),
        ('INNERGRID',    (0,0),(-1,-1), 4, WHITE),
        ('BOX',          (0,0),(-1,-1), 0, WHITE),
    ]))
    return outer

# ── CRITICAL TABLE ────────────────────────────────────────────────────────────
def critical_table(rows):
    # cols: Name | MB | Dim | Format | Streams | Path
    cw = [BODY_W * f for f in [0.22, 0.07, 0.12, 0.12, 0.08, 0.39]]
    data = [[hdr('Texture Name'), hdr('MB'), hdr('Dimensions'),
             hdr('Format'), hdr('Streams?'), hdr('Asset Path')]]
    style = list(BASE_TABLE_STYLE) + list(HEADER_ROW_STYLE)

    for i, r in enumerate(rows):
        row_num = i + 1
        no_stream = str(r.get('stream', 'NO')).upper() == 'NO'
        is_float  = 'Float' in r.get('fmt', '')
        zebra_bg  = WHITE if i % 2 == 0 else GREY_BG

        data.append([
            P(r.get('name',''),  sCellBold),
            P(r.get('mb',''),    sCellRC),
            P(r.get('dim',''),   sCellSm),
            P(r.get('fmt',''),   sCell),
            P(r.get('stream',''),sCellCenter),
            P(r.get('path',''),  sCellSm),
        ])
        style += [
            ('BACKGROUND', (0, row_num), (0, row_num), zebra_bg),
            ('BACKGROUND', (1, row_num), (1, row_num), zebra_bg),
            ('BACKGROUND', (2, row_num), (2, row_num), zebra_bg),
            ('BACKGROUND', (3, row_num), (3, row_num), RED_BG if (no_stream and not is_float) else (AMBER_BG if is_float else zebra_bg)),
            ('BACKGROUND', (4, row_num), (4, row_num), RED_BG if no_stream else GREEN_BG),
            ('TEXTCOLOR',  (1, row_num), (1, row_num), RED_TEXT if no_stream else GREEN_TEXT),
            ('TEXTCOLOR',  (4, row_num), (4, row_num), RED_TEXT if no_stream else GREEN_TEXT),
            ('BACKGROUND', (5, row_num), (5, row_num), zebra_bg),
        ]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t

# ── NEVERSTREAM TABLE ─────────────────────────────────────────────────────────
def neverstream_table(rows):
    cw = [BODY_W * f for f in [0.24, 0.07, 0.13, 0.12, 0.11, 0.33]]
    data = [[hdr('Texture Name'), hdr('MB'), hdr('Dimensions'),
             hdr('Format'), hdr('LOD Group'), hdr('Notes')]]
    style = list(BASE_TABLE_STYLE) + list(HEADER_ROW_STYLE)
    for i, r in enumerate(rows):
        rn = i + 1
        zb = WHITE if i % 2 == 0 else GREY_BG
        data.append([
            P(r.get('name',''),  sCellBold),
            P(r.get('mb',''),    sCellRC),
            P(r.get('dim',''),   sCellSm),
            P(r.get('fmt',''),   sCell),
            P(r.get('group',''), sCell),
            P(r.get('note',''),  sCellSm),
        ])
        style += [
            ('BACKGROUND', (0, rn), (5, rn), zb),
            ('TEXTCOLOR',  (1, rn), (1, rn), AMBER_TEXT),
            ('FONTNAME',   (1, rn), (1, rn), 'Helvetica-Bold'),
        ]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t

# ── UI TABLE ──────────────────────────────────────────────────────────────────
def ui_table(rows):
    cw = [BODY_W * f for f in [0.26, 0.07, 0.13, 0.54]]
    data = [[hdr('Texture Name'), hdr('MB'), hdr('Current Size'), hdr('Recommended Action')]]
    style = list(BASE_TABLE_STYLE) + list(HEADER_ROW_STYLE)
    for i, r in enumerate(rows):
        rn = i + 1
        zb = WHITE if i % 2 == 0 else GREY_BG
        data.append([
            P(r.get('name',''),   sCellBold),
            P(r.get('mb',''),     sCellRC),
            P(r.get('dim',''),    sCell),
            P(r.get('action',''), sCell),
        ])
        style += [
            ('BACKGROUND', (0, rn), (2, rn), zb),
            ('BACKGROUND', (3, rn), (3, rn), AMBER_BG),
            ('TEXTCOLOR',  (1, rn), (1, rn), AMBER_TEXT),
            ('FONTNAME',   (1, rn), (1, rn), 'Helvetica-Bold'),
        ]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t

# ── FORMAT REFERENCE TABLE ────────────────────────────────────────────────────
def format_ref_table():
    cw = [BODY_W * f for f in [0.22, 0.24, 0.24, 0.30]]
    rows_data = [
        ['PF_B8G8R8A8', 'Colour + Alpha (UI, VFX)',         'BC7',                           '~4:1 compression ratio'],
        ['PF_B8G8R8A8', 'Colour only (Decals, World)',       'DXT1 / BC7',                    '~8:1 / ~4:1'],
        ['PF_FloatRGBA','Height / Displacement maps',         'BC6H (HDR) or BC4 (single ch)', '~4:1 to ~8:1'],
        ['PF_FloatRGBA','Normal maps',                        'BC5',                            '~4:1'],
        ['PF_FloatRGBA','Starfield / Sky HDR',                'BC6H',                           '~4:1'],
    ]
    data = [[hdr('Current Format'), hdr('Use Case'), hdr('Recommended Format'), hdr('Approx. Savings')]]
    style = list(BASE_TABLE_STYLE) + list(HEADER_ROW_STYLE)
    for i, r in enumerate(rows_data):
        rn = i + 1
        zb = WHITE if i % 2 == 0 else GREY_BG
        data.append([P(r[0], sCellBold), P(r[1], sCell),
                     P(r[2], ParagraphStyle('grcell', fontName='Helvetica-Bold', fontSize=8,
                                            textColor=GREEN_TEXT, leading=11)),
                     P(r[3], sCellSm)])
        style += [
            ('BACKGROUND', (0, rn), (1, rn), zb),
            ('BACKGROUND', (2, rn), (2, rn), GREEN_BG),
            ('BACKGROUND', (3, rn), (3, rn), zb),
        ]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t

# ── RTAS TABLE ────────────────────────────────────────────────────────────────
def rtas_table(rows):
    cw = [BODY_W * f for f in [0.28, 0.10, 0.10, 0.52]]
    data = [[hdr('Asset'), hdr('Mesh MB'), hdr('RTAS MB'), hdr('Notes & Recommendation')]]
    style = list(BASE_TABLE_STYLE) + list(HEADER_ROW_STYLE)
    for i, r in enumerate(rows):
        rn = i + 1
        zb = WHITE if i % 2 == 0 else GREY_BG
        data.append([
            P(r.get('name',''),    sCellBold),
            P(r.get('mesh_mb',''), sCellR),
            P(r.get('rtas_mb',''), sCellRC),
            P(r.get('note',''),    sCellSm),
        ])
        style += [
            ('BACKGROUND', (0, rn), (1, rn), zb),
            ('BACKGROUND', (2, rn), (2, rn), AMBER_BG),
            ('BACKGROUND', (3, rn), (3, rn), zb),
            ('TEXTCOLOR',  (2, rn), (2, rn), AMBER_TEXT),
        ]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t

# ── HAIR RT TABLE ─────────────────────────────────────────────────────────────
def hair_rt_table(rows):
    cw = [BODY_W * f for f in [0.30, 0.10, 0.60]]
    data = [[hdr('Asset'), hdr('Size'), hdr('Recommendation')]]
    style = list(BASE_TABLE_STYLE) + list(HEADER_ROW_STYLE)
    for r in rows:
        data.append([
            P(r.get('name',''),           sCellBold),
            P(r.get('size',''),           sCellRC),
            P(r.get('recommendation',''), sCell),
        ])
        style += [
            ('BACKGROUND', (0, 1), (1, 1), RED_BG),
            ('BACKGROUND', (2, 1), (2, 1), AMBER_BG),
            ('TEXTCOLOR',  (1, 1), (1, 1), RED_TEXT),
        ]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t

# ── ADDITIONAL SECTION TABLE ──────────────────────────────────────────────────
def additional_table(rows):
    cw = [BODY_W * f for f in [0.37, 0.10, 0.53]]
    data = [[hdr('Subsystem'), hdr('Size'), hdr('Notes')]]
    style = list(BASE_TABLE_STYLE) + list(HEADER_ROW_STYLE)
    for i, r in enumerate(rows):
        rn = i + 1
        zb = WHITE if i % 2 == 0 else GREY_BG
        data.append([P(r.get('name',''), sCellBold), P(r.get('size',''), sCellRC), P(r.get('note',''), sCellSm)])
        style += [
            ('BACKGROUND', (0, rn), (0, rn), zb),
            ('BACKGROUND', (1, rn), (1, rn), AMBER_BG),
            ('BACKGROUND', (2, rn), (2, rn), zb),
            ('TEXTCOLOR',  (1, rn), (1, rn), AMBER_TEXT),
            ('FONTNAME',   (1, rn), (1, rn), 'Helvetica-Bold'),
        ]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t

# ── PRIORITY TABLE ────────────────────────────────────────────────────────────
def priority_table(rows):
    cw = [BODY_W * f for f in [0.31, 0.10, 0.12, 0.12, 0.35]]
    data = [[hdr('Issue'), hdr('Est. Savings'), hdr('Effort'), hdr('Priority'), hdr('Action')]]
    style = list(BASE_TABLE_STYLE) + list(HEADER_ROW_STYLE)
    pri_bg    = {'P0': RED_BG, 'P1': AMBER_BG, 'P2': colors.HexColor('#FFF8F0'), 'P3': GREY_BG}
    pri_color = {'P0': RED_TEXT, 'P1': AMBER_TEXT, 'P2': GREY_TEXT, 'P3': GREY_TEXT}
    for i, r in enumerate(rows):
        rn  = i + 1
        zb  = WHITE if i % 2 == 0 else GREY_BG
        pri = r.get('priority', 'P3')
        data.append([
            P(r.get('issue',''),   sCellBold),
            P(r.get('savings',''), sCellRC),
            P(r.get('effort',''),  sCellCenter),
            P(r.get('priority',''),sCellCenter),
            P(r.get('action',''),  sCellSm),
        ])
        style += [
            ('BACKGROUND', (0, rn), (0, rn), zb),
            ('BACKGROUND', (1, rn), (1, rn), GREEN_BG),
            ('BACKGROUND', (2, rn), (2, rn), zb),
            ('BACKGROUND', (3, rn), (3, rn), pri_bg.get(pri, GREY_BG)),
            ('BACKGROUND', (4, rn), (4, rn), zb),
            ('TEXTCOLOR',  (1, rn), (1, rn), GREEN_TEXT),
            ('FONTNAME',   (1, rn), (1, rn), 'Helvetica-Bold'),
            ('TEXTCOLOR',  (3, rn), (3, rn), pri_color.get(pri, GREY_TEXT)),
            ('FONTNAME',   (3, rn), (3, rn), 'Helvetica-Bold'),
        ]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t

# ── VT POOL TABLE ─────────────────────────────────────────────────────────────
def vt_pool_table(rows):
    cw = [BODY_W * f for f in [0.45, 0.15, 0.40]]
    data = [[hdr('Pool'), hdr('Size'), hdr('Format')]]
    style = list(BASE_TABLE_STYLE) + list(HEADER_ROW_STYLE)
    for i, r in enumerate(rows):
        rn = i + 1
        zb = WHITE if i % 2 == 0 else GREY_BG
        warn = '⚠' in str(r.get('format', ''))
        data.append([P(r.get('pool',''), sCellBold), P(r.get('size',''), sCellR), P(r.get('format',''), sCell)])
        style += [
            ('BACKGROUND', (0, rn), (1, rn), zb),
            ('BACKGROUND', (2, rn), (2, rn), AMBER_BG if warn else zb),
            ('TEXTCOLOR',  (2, rn), (2, rn), AMBER_TEXT if warn else colors.HexColor('#333333')),
        ]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t

# ── TITLE PAGE ────────────────────────────────────────────────────────────────
def title_block():
    items = [
        spacer(24),
        Paragraph(PROJECT, ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=32,
                                           leading=42, textColor=BLUE_DARK,
                                           spaceBefore=0, spaceAfter=6)),
        Paragraph('Memory Audit Report', ParagraphStyle('Subtitle', fontName='Helvetica',
                                                         fontSize=20, leading=26,
                                                         textColor=BLUE_MED, spaceAfter=6)),
        HRFlowable(width='100%', thickness=2, color=BLUE_MED, spaceAfter=8),
        Paragraph(f'{BUILD} MemReport  |  {DATE_STR}',
                  ParagraphStyle('Meta', fontName='Helvetica', fontSize=11, leading=15,
                                 textColor=colors.HexColor('#888888'), spaceAfter=20)),
    ]
    return items

# ── DOCUMENT ASSEMBLY ─────────────────────────────────────────────────────────
story = []

story += title_block()

# Executive Summary
story.append(P('Executive Summary', sH1))
story.append(hr())
story.append(P(
    f'This report identifies the worst memory offenders in the {PROJECT} build based on the '
    f'{BUILD} memory report. Texture problems (uncompressed, NeverStream, oversized UI) are '
    f'covered first, followed by ray tracing, geometry, plugins, and shaders.',
    sBody
))
story.append(spacer(6))

if D.get('summary_stats'):
    story.append(stat_table(D['summary_stats']))
    story.append(spacer(8))

if D.get('summary_body'):
    story.append(P(D['summary_body'], sBody))

# Section 1 — Critical
if D.get('critical_textures'):
    story.append(spacer(8))
    story.append(P('Section 1 — Critical Offenders', sH1))
    story.append(hr())
    story.append(P('Uncompressed + NeverStream (Worst of Both Worlds)', sH2))
    story.append(P(
        'The following textures use uncompressed pixel formats (4–16× larger than BC equivalents) '
        'AND are set to never stream — permanently occupying GPU memory regardless of visibility. '
        'Fix these first.',
        sBody
    ))
    story.append(spacer(4))
    story.append(critical_table(D['critical_textures']))
    story.append(spacer(4))
    if D.get('critical_summary'):
        story.append(P(f'<b>{D["critical_summary"]}</b>', sBody))

# Section 2 — NeverStream Compressed
if D.get('neverstream_textures'):
    story.append(spacer(8))
    story.append(P('Section 2 — NeverStream Textures (Compressed)', sH1))
    story.append(hr())
    story.append(P('Large Textures Locked Resident Without Need', sH2))
    story.append(P(
        'These textures use proper BC compression but have NeverStream=true. They stay fully '
        'resident regardless of camera proximity. Textures with 0 usage count are especially '
        'suspicious — they may not be referenced by anything currently loaded.',
        sBody
    ))
    story.append(spacer(4))
    story.append(neverstream_table(D['neverstream_textures']))
    story.append(spacer(4))
    for b in D.get('neverstream_bullets', []):
        story.append(bullet_item(b))

# Section 3 — UI
if D.get('ui_textures'):
    story.append(spacer(8))
    story.append(P('Section 3 — UI Texture Budget', sH1))
    story.append(hr())
    story.append(P('Always-Resident UI Group', sH2))
    story.append(P(
        'TEXTUREGROUP_UI is entirely non-streaming. The only levers are compression and resolution. '
        'UI textures misassigned to TEXTUREGROUP_World also eat into the world texture pool.',
        sBody
    ))
    story.append(spacer(4))
    story.append(ui_table(D['ui_textures']))
    story.append(spacer(4))
    if D.get('ui_note'):
        story.append(P(D['ui_note'], sBody))

# Section 4 — Recommendations
if D.get('recommendations'):
    story.append(spacer(8))
    story.append(P('Section 4 — Recommendations', sH1))
    story.append(hr())
    for rec in D['recommendations']:
        story.append(P(rec.get('title', ''), sH2))
        for b in rec.get('bullets', []):
            story.append(bullet_item(b))
    story.append(spacer(6))
    story.append(P('Format Reference — Compression Recommendations', sH2))
    story.append(spacer(4))
    story.append(format_ref_table())

# Section 5 — Geometry & RT
has_geo = D.get('geometry_stats') or D.get('rtas_offenders') or D.get('hair_rt')
if has_geo:
    story.append(PageBreak())
    story.append(P('Section 5 — Geometry & Ray Tracing', sH1))
    story.append(hr())

    if D.get('geometry_stats'):
        story.append(P('Overall Memory Budget', sH2))
        story.append(spacer(4))
        story.append(stat_table(D['geometry_stats']))
        story.append(spacer(8))

    if D.get('hair_rt'):
        story.append(P('Critical — Hair Ray Tracing', sH2))
        if D.get('hair_rt_intro'):
            story.append(P(D['hair_rt_intro'], sBody))
        story.append(spacer(4))
        story.append(hair_rt_table(D['hair_rt']))
        story.append(spacer(8))

    if D.get('rtas_offenders'):
        story.append(P('Ray Tracing Acceleration Structures — Top Offenders', sH2))
        if D.get('rtas_intro'):
            story.append(P(D['rtas_intro'], sBody))
        story.append(spacer(4))
        story.append(rtas_table(D['rtas_offenders']))
        story.append(spacer(4))
        if D.get('rtas_note'):
            story.append(P(D['rtas_note'], sBody))

# Section 6 — Additional Findings
if D.get('additional_sections'):
    story.append(spacer(8))
    story.append(P('Section 6 — Additional Findings', sH1))
    story.append(hr())
    for sec in D['additional_sections']:
        story.append(P(sec.get('title', ''), sH2))
        if sec.get('intro'):
            story.append(P(sec['intro'], sBody))
        if sec.get('table'):
            story.append(spacer(4))
            story.append(additional_table(sec['table']))
            story.append(spacer(4))
        if sec.get('body'):
            story.append(P(sec['body'], sBody))

# Section 7 — Priority Table
if D.get('priority_table'):
    story.append(spacer(8))
    story.append(P('Section 7 — Summary Priority Table', sH1))
    story.append(hr())
    story.append(P('All identified issues ranked by estimated memory impact and implementation effort.', sBody))
    story.append(spacer(4))
    story.append(priority_table(D['priority_table']))

# Appendix — VT Pools
if D.get('vt_pools'):
    story.append(PageBreak())
    story.append(P('Appendix — Virtual Texture Physical Pools', sH1))
    story.append(hr())
    if D.get('vt_note'):
        story.append(P(D['vt_note'], sBody))
    story.append(spacer(4))
    story.append(vt_pool_table(D['vt_pools']))

story.append(spacer(12))
story.append(P(f'Source: {SOURCE} via NotebookLM RAG — {DATE_STR}.', sSmall))

# ── BUILD DOC ─────────────────────────────────────────────────────────────────
frame = Frame(MARGIN, MARGIN, BODY_W, PAGE_H - 2 * MARGIN, id='main')
template = PageTemplate(id='main', frames=[frame], onPage=_on_page)
# ── BUILD DOC ─────────────────────────────────────────────────────────────────
frame = Frame(MARGIN, MARGIN, BODY_W, PAGE_H - 2 * MARGIN, id='main')
template = PageTemplate(id='main', frames=[frame], onPage=_on_page)
doc = BaseDocTemplate(
    OUT_PATH,
    pagesize=letter,
    leftMargin=MARGIN, rightMargin=MARGIN,
    topMargin=MARGIN + 14, bottomMargin=MARGIN + 14,
    pageTemplates=[template],
)
doc.build(story)
print(f'Done. Written to: {OUT_PATH}')
