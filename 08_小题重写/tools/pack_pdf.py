#!/usr/bin/env python3
"""出 PDF：python3 pack_pdf.py <输出目录> [set_id ...]

每套一份：一、给定材料 → 二、作答要求 → 三、参考答案（每道小题：答案、考场上的思路、逐条解析、压缩与成本；
有大作文的再接：考场上的思路、作文、逐句解析）。小题读 08_小题重写/<套>/Qn.md，大作文读 07_句子层/重写/<套>_重写.md。
"""
import os, re, sys
from xml.sax.saxutils import escape
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, ROOT, CN, split_blocks, material_text
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, HRFlowable, KeepTogether
from reportlab.lib import textsplit as _ts
from reportlab.platypus import paragraph as _pp

_KINSOKU = '，；：、。！？”’」』】〉》…—·%'
for _m in (_ts, _pp):
    _m.ALL_CANNOT_START = _m.ALL_CANNOT_START + ''.join(c for c in _KINSOKU if c not in _m.ALL_CANNOT_START)
pdfmetrics.registerFont(TTFont('Song', '/usr/share/fonts/truetype/arphic/uming.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('Hei', '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', subfontIndex=0))
pdfmetrics.registerFontFamily('Song', normal='Song', bold='Hei', italic='Song', boldItalic='Hei')

ESSAY = os.path.join(ROOT, '07_句子层', '重写')
PAPERS = [  # 套, 封面标题, 文件名
    ('2026省市', '2026 年广东省考《申论》·省市卷', '2026年广东省考申论·省市卷·材料题干与参考答案.pdf'),
    ('2026县镇', '2026 年广东省考《申论》·县镇卷', '2026年广东省考申论·县镇卷·材料题干与参考答案.pdf'),
    ('2025省市', '2025 年广东省考《申论》·省市卷', '2025年广东省考申论·省市卷·材料题干与参考答案.pdf'),
    ('2025县镇', '2025 年广东省考《申论》·县镇卷', '2025年广东省考申论·县镇卷·材料题干与参考答案.pdf'),
    ('2025选调', '2025 年广东选调生《申论》', '2025年广东选调申论·材料题干与参考答案.pdf'),
    ('2024一卷', '2024 年广东省考《申论》·一卷', '2024年广东省考申论·一卷·材料题干与参考答案.pdf'),
    ('2024二卷', '2024 年广东省考《申论》·二卷', '2024年广东省考申论·二卷·材料题干与参考答案.pdf'),
    ('2024选调', '2024 年广东选调生《申论》', '2024年广东选调申论·材料题干与参考答案.pdf'),
    ('2023县级', '2023 年广东省考《申论》·县级卷', '2023年广东省考申论·县级卷·材料题干与参考答案.pdf'),
    ('2023乡镇', '2023 年广东省考《申论》·乡镇卷', '2023年广东省考申论·乡镇卷·材料题干与参考答案.pdf'),
    ('2022县级', '2022 年广东省考《申论》·县级卷', '2022年广东省考申论·县级卷·材料题干与参考答案.pdf'),
    ('2022乡镇', '2022 年广东省考《申论》·乡镇卷', '2022年广东省考申论·乡镇卷·材料题干与参考答案.pdf'),
    ('2021县级', '2021 年广东省考《申论》·县级卷', '2021年广东省考申论·县级卷·材料题干与参考答案.pdf'),
    ('2021乡镇', '2021 年广东省考《申论》·乡镇卷', '2021年广东省考申论·乡镇卷·材料题干与参考答案.pdf'),
    ('2020县级', '2020 年广东省考《申论》·县级卷', '2020年广东省考申论·县级卷·材料题干与参考答案.pdf'),
    ('2020乡镇', '2020 年广东省考《申论》·乡镇卷', '2020年广东省考申论·乡镇卷·材料题干与参考答案.pdf'),
]

GRAY, LINE, DARK = HexColor('#555555'), HexColor('#999999'), HexColor('#222222')


def st(name, **kw):
    kw.setdefault('wordWrap', 'CJK')
    return ParagraphStyle(name, **kw)


S = dict(
    title=st('t', fontName='Hei', fontSize=20, leading=30, alignment=TA_CENTER, spaceAfter=6),
    subtitle=st('st', fontName='Song', fontSize=11, leading=18, alignment=TA_CENTER, textColor=GRAY, spaceAfter=18),
    h2=st('h2', fontName='Hei', fontSize=14, leading=24, spaceBefore=12, spaceAfter=8),
    h3=st('h3', fontName='Hei', fontSize=12.5, leading=20, spaceBefore=12, spaceAfter=5),
    h4=st('h4', fontName='Hei', fontSize=11, leading=18, spaceBefore=6, spaceAfter=3, textColor=DARK),
    body=st('b', fontName='Song', fontSize=10.5, leading=18, alignment=TA_JUSTIFY, firstLineIndent=21, spaceAfter=3),
    flat=st('f', fontName='Song', fontSize=10.5, leading=18, alignment=TA_JUSTIFY, spaceAfter=3),
    answer=st('a', fontName='Song', fontSize=11, leading=20, alignment=TA_JUSTIFY, spaceAfter=0,
              backColor=HexColor('#f4f4f2'), borderPadding=(7, 8, 7, 8), borderColor=HexColor('#dcdcd6'), borderWidth=0.5),
    lead=st('l', fontName='Song', fontSize=10.5, leading=18, alignment=TA_JUSTIFY, spaceBefore=3, spaceAfter=3),
    sent=st('s', fontName='Hei', fontSize=10.5, leading=18, alignment=TA_JUSTIFY, spaceBefore=7, spaceAfter=1),
    note=st('n', fontName='Song', fontSize=9.5, leading=16, alignment=TA_JUSTIFY, leftIndent=16, textColor=GRAY, spaceBefore=1),
    essay=st('e', fontName='Song', fontSize=11, leading=20, alignment=TA_JUSTIFY, firstLineIndent=22, spaceAfter=5),
    etitle=st('et', fontName='Hei', fontSize=13, leading=22, alignment=TA_CENTER, spaceAfter=4),
    esub=st('es', fontName='Song', fontSize=11, leading=20, alignment=TA_CENTER, textColor=DARK, spaceAfter=10),
    tip=st('tip', fontName='Song', fontSize=9.5, leading=16, textColor=GRAY, spaceAfter=6),
)


def curly(s):
    return re.sub(r'"([^"]*)"', '“\\1”', s)


def P(text, key):
    t = escape(curly(text))
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    return Paragraph(t, S[key])


def lead(text, key='lead'):
    """「**现实里是一件什么事**　……」或「来源：……」→ 黑体引导词 + 正文。"""
    m = re.match(r'^\*\*(.+?)\*\*[　：:\s]*(.*)$', text)
    if m:
        return Paragraph('<b>%s</b>　%s' % (escape(curly(m.group(1))), escape(curly(m.group(2)))), S[key])
    m = re.match(r'^([^：:]{1,8})[：:](.*)$', text)
    if m:
        return Paragraph('<b>%s</b>：%s' % (escape(m.group(1)), escape(curly(m.group(2)))), S[key])
    return P(text, key)


def rule():
    return HRFlowable(width='100%', thickness=0.4, color=HexColor('#dddddd'), spaceBefore=8, spaceAfter=3)


def question_story(path, num):
    """渲染一道小题的 Qn.md。"""
    t = open(path, encoding='utf-8').read()
    out, sec, box = [], '', []

    def flush():
        if box:
            out.append(Paragraph('<br/>'.join(escape(curly(x)) for x in box), S['answer']))
            out.append(Spacer(1, 10))
            box.clear()
    for raw in t.split('\n'):
        l = raw.strip()
        if not l:
            continue
        if sec.startswith('答案') and not l.startswith('#'):
            box.append(l); continue
        flush()
        if l.startswith('# '):
            out.append(P('（%s）%s' % (CN[num - 1], l[2:].strip()), 'h2'))
            continue
        if l.startswith('## '):
            sec = l[3:].strip()
            out.append(P(sec, 'h3'))
            continue
        if l.startswith('### '):
            out.append(rule()); out.append(P(l[4:].strip(), 'h4')); continue
        if l.startswith('#### '):
            out.append(P(l[5:].strip(), 'sent')); continue
        if l.startswith('- '):
            out.append(lead(l[2:].strip(), 'note')); continue
        if l.startswith('**'):
            out.append(lead(l)); continue
        out.append(P(l, 'body'))
    flush()
    return out


def essay_story(sid, num):
    path = os.path.join(ESSAY, sid + '_重写.md')
    if not os.path.exists(path):
        return []
    t = open(path, encoding='utf-8').read()
    think = re.search(r'\n## 考场上的思路\n(.*?)(?=\n## )', t, re.S)
    essay = re.search(r'\n## 一、作文\n(.*?)(?=\n## 二、)', t, re.S)
    ann = re.search(r'\n## 二、逐句标注\n(.*?)(?=\n## [三四五六七])', t, re.S)
    out = [PageBreak(), P('（%s）大作文' % CN[num - 1], 'h2')]
    if think:
        out.append(P('考场上的思路', 'h3'))
        for l in (x.strip() for x in think.group(1).split('\n')):
            if l:
                out.append(P(l, 'body'))
    paras = [p.strip() for p in essay.group(1).strip().split('\n') if p.strip()]
    head, _, sub = paras[0].partition('——')
    out += [PageBreak(), P('作文', 'h3'), Spacer(1, 4), P(head.strip(), 'etitle')]
    body = paras[1:]
    if sub:
        body = ['——' + sub.strip()] + body
    if body and body[0].startswith('——'):
        out.append(P(body[0], 'esub'))
        body = body[1:]
    out += [P(p, 'essay') for p in body]
    out += [PageBreak(), P('大作文逐句解析', 'h3')]
    for l in (x.strip() for x in ann.group(1).split('\n')):
        if not l:
            continue
        if l.startswith('### '):
            out.append(rule()); out.append(P(l[4:].strip(), 'h4'))
        elif l.startswith('>'):
            out.append(lead(l.lstrip('> ').strip(), 'note'))
        elif l.startswith('**') and l.endswith('**'):
            out.append(P(l.strip('*').strip(), 'sent'))
        else:
            out.append(P(l, 'body'))
    return out


def questions_block(sid):
    mt = material_text(sid)
    mt = re.sub(r'材料\s*\n\s*([一二三四五六七八九十]+)\s*\n', r'\n材料\1\n', mt)
    m = re.search(r'\n\s*【?问题一】?[：:]?\s*\n', mt)
    out = []
    for l in (x.strip() for x in (mt[m.start():] if m else '').split('\n')):
        if not l or re.match(r'^(答题纸|第[一二三四五]大题|\d+字)', l):
            continue
        if not out or re.match(r'^(【?问题[一二三四五六]】?[：:．.]?$|【?问题[一二三四五六]】|要求[：:]|（\s*\d\s*）|\(\d\))', l):
            out.append(l)
        else:
            out[-1] += l
    return out


def build(sid, title, outname, outdir):
    story = [P(title, 'title'), P('材料 ・ 题干 ・ 参考答案', 'subtitle'), P('一、给定材料', 'h2')]
    for name, paras in split_blocks(sid):
        story.append(P('【导语】' if name == '导' else '【材料%s】' % name, 'h3'))
        story += [P(p, 'body') for p in paras]
    story += [PageBreak(), P('二、作答要求', 'h2')]
    for q in questions_block(sid):
        story.append(P(q, 'h3' if re.match(r'^【?问题[一二三四五六]', q) else 'flat'))
    story += [PageBreak(), P('三、参考答案', 'h2'),
              P('每道题依次是：答案、考场上的思路、逐条解析（每条答案现实里是什么事、为什么这么归、每个分句从哪来怎么改）、压缩与成本。', 'tip')]
    qs = sorted(f for f in os.listdir(os.path.join(BASE, sid)) if re.match(r'^Q\d\.md$', f))
    for i, f in enumerate(qs, 1):
        if i > 1:
            story.append(PageBreak())
        story += question_story(os.path.join(BASE, sid, f), i)
    story += essay_story(sid, len(qs) + 1)

    def deco(canvas, doc):
        canvas.saveState()
        canvas.setFont('Song', 8); canvas.setFillColor(LINE)
        canvas.drawRightString(A4[0] - 20 * mm, A4[1] - 13 * mm, title)
        canvas.setStrokeColor(LINE); canvas.setLineWidth(0.3)
        canvas.line(20 * mm, A4[1] - 15 * mm, A4[0] - 20 * mm, A4[1] - 15 * mm)
        canvas.drawCentredString(A4[0] / 2, 12 * mm, '%d' % doc.page)
        canvas.restoreState()

    path = os.path.join(outdir, outname)
    doc = BaseDocTemplate(path, pagesize=A4, title=title, author='',
                          leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=18 * mm)
    doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)], onPage=deco)])
    doc.build(story)
    return path, len(qs)


if __name__ == '__main__':
    outdir = sys.argv[1]; want = sys.argv[2:]
    os.makedirs(outdir, exist_ok=True)
    for sid, title, outname in PAPERS:
        if want and sid not in want:
            continue
        path, nq = build(sid, title, outname, outdir)
        print('%-8s 小题 %d 道　大作文 %s → %s' % (sid, nq, '有' if os.path.exists(os.path.join(ESSAY, sid + '_重写.md')) else '无', outname))
