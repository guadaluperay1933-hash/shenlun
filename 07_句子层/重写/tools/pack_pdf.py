#!/usr/bin/env python3
"""把一套卷子的材料、题干、参考答案拼成一份 PDF。

参考答案 = 小题的四问版答案 + 大作文重写稿 + 大作文逐句解析。
用法：python3 pack_pdf.py <输出目录> [样本id ...]      不给样本id就出全部
"""
import os, re, sys
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, PageBreak, HRFlowable)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
SAMPLES = os.path.join(ROOT, '07_句子层', 'samples')
REWRITE = os.path.join(ROOT, '07_句子层', '重写')
PACK = os.path.join(ROOT, '广东申论备考包')

# 样本id, 封面标题, 输出文件名, 小题答案出处
PAPERS = [
    ('2026省市', '2026 年广东省考《申论》·省市卷', '2026年广东省考申论·省市卷·材料题干与参考答案.pdf',
     '02_真题重写_四问五问版/重写_2026省市卷_四问五问版.md'),
    ('2026县镇', '2026 年广东省考《申论》·县镇卷', '2026年广东省考申论·县镇卷·材料题干与参考答案.pdf',
     '02_真题重写_四问五问版/重写_2026县镇卷_四问五问版.md'),
    ('2025省市', '2025 年广东省考《申论》·省市卷', '2025年广东省考申论·省市卷·材料题干与参考答案.pdf',
     '02_真题重写_四问五问版/重写_2025省市卷_四问五问版.md'),
    ('2025县镇', '2025 年广东省考《申论》·县镇卷', '2025年广东省考申论·县镇卷·材料题干与参考答案.pdf',
     '02_真题重写_四问五问版/重写_2025县镇卷_四问五问版.md'),
    ('2025选调', '2025 年广东选调生《申论》', '2025年广东选调申论·材料题干与参考答案.pdf',
     '03_选调/选调_2025_四问五问盲做版.md'),
    ('2024一卷', '2024 年广东省考《申论》·一卷', '2024年广东省考申论·一卷·材料题干与参考答案.pdf',
     '02_真题重写_四问五问版/重写_2024一卷_四问五问版.md'),
    ('2024二卷', '2024 年广东省考《申论》·二卷', '2024年广东省考申论·二卷·材料题干与参考答案.pdf',
     '02_真题重写_四问五问版/重写_2024二卷_四问五问版.md'),
    ('2024选调', '2024 年广东选调生《申论》', '2024年广东选调申论·材料题干与参考答案.pdf',
     '03_选调/选调_2024_四问五问盲做版.md'),
    ('2023县级', '2023 年广东省考《申论》·县级卷', '2023年广东省考申论·县级卷·材料题干与参考答案.pdf',
     '02_真题重写_四问五问版/重写_2023县级卷_四问五问版.md'),
    ('2022县级', '2022 年广东省考《申论》·县级卷', '2022年广东省考申论·县级卷·材料题干与参考答案.pdf',
     '02_真题重写_四问五问版/重写_2022县级卷_四问五问版.md'),
]
CN = '一二三四五六七八九十'

# ---------- 取料 ----------

def split_material(sid):
    """→ (材料块 [(名, [段])], 题干段)。分块、分段的规矩跟 pool.py 一样。"""
    mt = open(os.path.join(SAMPLES, sid, 'material.txt'), encoding='utf-8').read()
    mt = re.sub(r'材料\s*\n\s*([一二三四五六七八九十]+)\s*\n', r'\n材料\1\n', mt)
    m = re.search(r'\n\s*【?问题一】?[：:]?\s*\n', mt)
    body, qtext = (mt[:m.start()], mt[m.start():]) if m else (mt, '')
    parts = re.split(r'(?m)^\s*【?材料([一二三四五六七八九十]+)】?\s*$', body)
    blocks = []
    for i in range(1, len(parts), 2):
        lines = [l.strip() for l in parts[i + 1].split('\n') if l.strip()]
        buf, paras = '', []
        for l in lines:
            buf += l
            if re.search(r'[。！？”]$', l):
                paras.append(buf); buf = ''
        if buf:
            paras.append(buf)
        blocks.append(('材料' + parts[i], paras))
    return blocks, reflow_questions(qtext)


def reflow_questions(qtext):
    """题干：遇到问题号、要求、（n）另起一段，其余接上一行。"""
    out = []
    for l in (l.strip() for l in qtext.split('\n')):
        if not l:
            continue
        if not out or re.match(r'^(【?问题[一二三四五六]】?[：:．.]?$|【?问题[一二三四五六]】|要求[：:]|（\s*\d\s*）|\(\d\))', l):
            out.append(l)
        else:
            out[-1] += l
    return out


def read_answers(relpath):
    """小题答案：只取 ## 1. / ## 2. 两节里的 ### 答案（…） 正文。"""
    t = open(os.path.join(PACK, relpath), encoding='utf-8').read()
    got = []
    for num, label in (('1', '问题一'), ('2', '问题二')):
        m = re.search(r'(?m)^## %s\. (.*?)\n(.*?)(?=\n## \d\.|\Z)' % num, t, re.S)
        if not m:
            continue
        head, sec = m.group(1).strip(), m.group(2)
        head = re.sub(r'^问题[一二三四]\s*　?\s*', '', head)
        for a in re.finditer(r'(?m)^### 答案(（[^）]*）)?\s*\n(.*?)(?=\n### |\n---|\Z)', sec, re.S):
            note = (a.group(1) or '').strip('（）')
            note = re.sub(r'[，,]?\s*含标点.*$', '', note).strip()
            paras = [p.strip() for p in a.group(2).strip().split('\n') if p.strip()]
            got.append((label, head, note, paras))
    return got


def read_rewrite(sid):
    """→ (大作文段落, 逐句标注条目)。"""
    t = open(os.path.join(REWRITE, sid + '_重写.md'), encoding='utf-8').read()
    e = re.search(r'\n## 一、作文\n(.*?)(?=\n## 二、)', t, re.S)
    essay = [p.strip() for p in e.group(1).strip().split('\n') if p.strip()]
    a = re.search(r'\n## 二、逐句标注\n(.*?)(?=\n## [三四五六])', t, re.S)
    items = []
    for l in (l.strip() for l in a.group(1).split('\n')):
        if not l:
            continue
        if l.startswith('### '):
            items.append(('h', l[4:].strip()))
        elif l.startswith('>'):
            items.append(('n', l.lstrip('> ').strip()))
        else:
            items.append(('s', l.strip('*').strip()))
    return essay, items

# ---------- 排版 ----------

# 行首不放标点：reportlab 自带的禁则表里没有中文逗号、分号、引号，补上
from reportlab.lib import textsplit as _ts
from reportlab.platypus import paragraph as _pp
_KINSOKU = '，；：、。！？”’」』】〉》…—·%'
for _m in (_ts, _pp):
    _m.ALL_CANNOT_START = _m.ALL_CANNOT_START + ''.join(c for c in _KINSOKU if c not in _m.ALL_CANNOT_START)

pdfmetrics.registerFont(TTFont('Song', '/usr/share/fonts/truetype/arphic/uming.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('Hei', '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', subfontIndex=0))
pdfmetrics.registerFontFamily('Song', normal='Song', bold='Hei', italic='Song', boldItalic='Hei')

GRAY = HexColor('#555555')
LINE = HexColor('#999999')
DARK = HexColor('#222222')


def style(name, **kw):
    kw.setdefault('wordWrap', 'CJK')
    return ParagraphStyle(name, **kw)


S = dict(
    title=style('t', fontName='Hei', fontSize=20, leading=30, alignment=TA_CENTER, spaceAfter=6),
    subtitle=style('st', fontName='Song', fontSize=11, leading=18, alignment=TA_CENTER,
                   textColor=GRAY, spaceAfter=18),
    h2=style('h2', fontName='Hei', fontSize=15, leading=24, spaceBefore=16, spaceAfter=8),
    h3=style('h3', fontName='Hei', fontSize=12, leading=20, spaceBefore=14, spaceAfter=4),
    h4=style('h4', fontName='Hei', fontSize=10.5, leading=18, spaceBefore=4, spaceAfter=2, textColor=DARK),
    body=style('b', fontName='Song', fontSize=10.5, leading=18, alignment=TA_JUSTIFY,
               firstLineIndent=21, spaceAfter=3),
    flat=style('f', fontName='Song', fontSize=10.5, leading=18, alignment=TA_JUSTIFY, spaceAfter=3),
    essay=style('e', fontName='Song', fontSize=11, leading=20, alignment=TA_JUSTIFY,
                firstLineIndent=22, spaceAfter=5),
    etitle=style('et', fontName='Hei', fontSize=13, leading=22, alignment=TA_CENTER, spaceAfter=10),
    sent=style('s', fontName='Hei', fontSize=10.5, leading=18, alignment=TA_JUSTIFY, spaceBefore=8),
    note=style('n', fontName='Song', fontSize=9.5, leading=16, alignment=TA_JUSTIFY,
               leftIndent=16, textColor=GRAY, spaceBefore=2),
    tip=style('tip', fontName='Song', fontSize=9.5, leading=16, textColor=GRAY, spaceAfter=6),
)


def curly(s):
    """重写稿里写的是直引号，排到纸上换成弯引号。"""
    return re.sub(r'"([^"]*)"', '“\\1”', s)


def P(text, style_key):
    t = escape(curly(text))
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    return Paragraph(t, S[style_key])


def rule():
    return HRFlowable(width='100%', thickness=0.4, color=HexColor('#dddddd'),
                      spaceBefore=10, spaceAfter=4)


def build(sid, title, outname, qapath, outdir):
    blocks, questions = split_material(sid)
    answers = read_answers(qapath)
    essay, ann = read_rewrite(sid)

    story = [P(title, 'title'), P('材料 ・ 题干 ・ 参考答案', 'subtitle')]

    story.append(P('一、给定材料', 'h2'))
    for name, paras in blocks:
        story.append(P('【%s】' % name, 'h3'))
        for p in paras:
            story.append(P(p, 'body'))

    story.append(PageBreak())
    story.append(P('二、作答要求', 'h2'))
    for q in questions:
        story.append(P(q, 'h3' if re.match(r'^【?问题[一二三四五六]', q) else 'flat'))

    story.append(PageBreak())
    story.append(P('三、参考答案', 'h2'))
    story.append(P('小题为四问法重写版答案；大作文为重写稿，附逐句解析（来源 = 材料出处，思考 = 怎么改）。', 'tip'))
    n = 0
    for label, head, note, paras in answers:
        n += 1
        cap = '（%s）%s　%s' % (CN[n - 1], label, head)
        if note:
            cap += '　〔%s〕' % note
        story.append(P(cap, 'h3'))
        for p in paras:
            story.append(P(p, 'flat'))

    n += 1
    story.append(P('（%s）大作文' % CN[n - 1], 'h3'))
    story.append(Spacer(1, 4))
    story.append(P(essay[0], 'etitle'))
    for p in essay[1:]:
        story.append(P(p, 'essay'))

    n += 1
    story.append(PageBreak())
    story.append(P('（%s）大作文逐句解析' % CN[n - 1], 'h2'))
    for kind, text in ann:
        if kind == 'h':
            story.append(rule())
            story.append(P(text, 'h4'))
        elif kind == 's':
            story.append(P(text, 'sent'))
        else:
            story.append(P(text, 'note'))

    def deco(canvas, doc):
        canvas.saveState()
        canvas.setFont('Song', 8)
        canvas.setFillColor(LINE)
        canvas.drawRightString(A4[0] - 20 * mm, A4[1] - 13 * mm, title)
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.3)
        canvas.line(20 * mm, A4[1] - 15 * mm, A4[0] - 20 * mm, A4[1] - 15 * mm)
        canvas.drawCentredString(A4[0] / 2, 12 * mm, '%d' % doc.page)
        canvas.restoreState()

    path = os.path.join(outdir, outname)
    doc = BaseDocTemplate(path, pagesize=A4, title=title, author='',
                          leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=18 * mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='f')
    doc.addPageTemplates([PageTemplate(id='p', frames=[frame], onPage=deco)])
    doc.build(story)
    return path, len(blocks), len(answers), len(ann)


if __name__ == '__main__':
    outdir = sys.argv[1]
    want = sys.argv[2:]
    os.makedirs(outdir, exist_ok=True)
    for sid, title, outname, qapath in PAPERS:
        if want and sid not in want:
            continue
        path, nb, na, nn = build(sid, title, outname, qapath, outdir)
        print('%-8s 材料%d则　小题答案%d份　标注%d条 → %s' % (sid, nb, na, nn, os.path.basename(path)))
