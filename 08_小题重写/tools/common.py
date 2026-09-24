"""小题工具的公用部分：路径、读材料、分则分段分句、题目表。"""
import os, re, json, unicodedata

BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ROOT = os.path.normpath(os.path.join(BASE, '..'))
CN = '一二三四五六七八九十'
QN = {'Q1': '问题一', 'Q2': '问题二', 'Q3': '问题三', 'Q4': '问题四', 'Q5': '问题五'}
TITLE_LINES = re.compile(r'^(20\d\d ?年.*(申论|题|（[^）]*）)\S*|试题卷.*|[一二]、给定材料|给定材料[：:]?|【注意事项】)\s*$')


def material_text(sid):
    return open(os.path.join(BASE, 'samples', sid, 'material.txt'), encoding='utf-8').read()


def questions():
    return json.load(open(os.path.join(BASE, 'questions.json'), encoding='utf-8'))


def question(sid, q):
    q = QN.get(q, q)
    for o in questions():
        if o['set_id'] == sid and o['q'] == q:
            return o
    raise SystemExit('questions.json 里没有 %s %s' % (sid, q))


def split_blocks(sid):
    """→ [(则名, [段])]；则名是「一」「二」…，材料一之前的导语叫「导」。题干部分不要。"""
    mt = material_text(sid)
    mt = re.sub(r'材料\s*\n\s*([一二三四五六七八九十]+)\s*\n', r'\n材料\1\n', mt)
    m = re.search(r'\n\s*【?问题一】?[：:]?\s*\n', mt)
    body = mt[:m.start()] if m else mt
    parts = re.split(r'(?m)^\s*【?(材料([一二三四五六七八九十]+)|导语)】?\s*$', body)
    out = []
    pre = [l for l in parts[0].split('\n') if l.strip() and not TITLE_LINES.match(l.strip())]
    if pre:
        out.append(('导', paragraphs(pre)))
    for i in range(1, len(parts), 3):
        name = parts[i + 1] or '导'
        lines = [l for l in parts[i + 2].split('\n') if l.strip()]
        out.append((name, paragraphs(lines)))
    return out


def paragraphs(lines):
    """一段 = 以句末标点结尾的行块；只含标点或不足 4 字的碎行并入上一段。"""
    buf, paras = '', []
    for l in (x.strip() for x in lines):
        if re.match(r'^(时间|地点|参会人员|参加人员|主持人|记录人)[：:]', l):
            if buf:
                paras.append(buf); buf = ''
            paras.append(l)
            continue
        buf += l
        if re.search(r'[。！？”」]$', l):
            if paras and len(re.sub(r'[^\w]', '', buf)) < 4:
                paras[-1] += buf
            else:
                paras.append(buf)
            buf = ''
    if buf:
        if paras and len(re.sub(r'[^\w]', '', buf)) < 4:
            paras[-1] += buf
        else:
            paras.append(buf)
    return paras


def sentences(p):
    """句末标点后面跟着的右引号归前一句。"""
    return [s for s in re.findall(r'[^。！？；]*[。！？；]+[”」’]*|[^。！？；]+$', p) if re.sub(r'[\s”」’]', '', s)]


def clauses(s):
    return [c for c in re.split(r'(?<=[，、：])', s) if re.sub(r'\s', '', c)]


def norm(t):
    t = unicodedata.normalize('NFKC', t)
    return re.sub(r'[\s“”"‘’\'《》〈〉【】（）()、，。；：！？—…·,.;:!?\-—「」/]', '', t)
