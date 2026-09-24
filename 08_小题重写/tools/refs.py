#!/usr/bin/env python3
"""两份参照，第 7 步才用：
  python3 refs.py prev <set_id> [--q 问题一]   上一版（fable 定稿）的小题答案正文，只抽答案，不带任何分析
  python3 refs.py jigou <set_id>               机构参考答案 PDF 的全文（没有就说跳过）
上一版答案同时写到 <set_id>/参照_上一版/Qn.txt，方便 cost.py 量它的成本。
"""
import sys, os, re, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, ROOT, CN

PACK = os.path.join(ROOT, '广东申论备考包')
SEC04 = {'2020县级': '2020广东县级卷', '2020乡镇': '2020广东乡镇卷', '2021县级': '2021广东县级卷',
         '2021乡镇': '2021广东乡镇卷', '2022县级': '2022广东县级卷', '2022乡镇': '2022广东乡镇卷',
         '2023县级': '2023广东县级卷', '2023乡镇': '2023广东乡镇卷', '2024一卷': '2024广东一卷',
         '2024二卷': '2024广东二卷', '2025省市': '2025广东省市卷', '2025县镇': '2025广东县镇卷',
         '2026省市': '2026广东省市卷', '2026县镇': '2026广东县镇卷'}
SEL03 = {'2024选调': '选调_2024_四问五问盲做版.md', '2025选调': '选调_2025_四问五问盲做版.md'}
JIGOU = {'2020县级': '2020年广东省考申论·县级卷·参考答案.pdf', '2020乡镇': '2020年广东省考申论·乡镇卷·参考答案.pdf',
         '2021县级': '2021年广东省考申论·县级卷·参考答案.pdf', '2021乡镇': '2021年广东省考申论·乡镇卷·参考答案.pdf',
         '2022县级': '2022年广东省考申论·县级卷·参考答案.pdf', '2022乡镇': '2022年广东省考申论·乡镇卷·参考答案.pdf',
         '2023县级': '2023年广东省考申论·县级卷·参考答案.pdf', '2023乡镇': '2023年广东省考申论·乡镇卷·参考答案.pdf',
         '2024一卷': '2024年广东省考申论·一卷·参考答案.pdf', '2024二卷': '2024年广东省考申论·二卷·参考答案.pdf',
         '2025省市': '2025年广东省考申论·省市卷·参考答案.pdf', '2025县镇': '2025年广东省考申论·县镇卷·参考答案.pdf',
         '2024选调': '24广东选调《申论》答案.pdf', '2025选调': '25年广东选调《申论》答案.pdf'}


def prev(sid):
    """→ {问题一: [行], ...}"""
    out = {}
    if sid in SEC04:
        t = open(os.path.join(PACK, '04_答案本', '广东申论定稿答案汇编_2020-2026.md'), encoding='utf-8').read()
        m = re.search(r'(?m)^## %s\n(.*?)(?=^## |\Z)' % re.escape(SEC04[sid]), t, re.S)
        sec = m.group(1) if m else ''
        for h in re.finditer(r'(?m)^### (问题[一二三四五])[^\n]*\n(.*?)(?=^### |\Z)', sec, re.S):
            lines = [l for l in h.group(2).split('\n')
                     if l.strip() and not l.startswith('>') and not re.match(r'^（\d+ ?字', l.strip())]
            out.setdefault(h.group(1), lines)
    elif sid in SEL03:
        t = open(os.path.join(PACK, '03_选调', SEL03[sid]), encoding='utf-8').read()
        for num in '12':
            m = re.search(r'(?m)^## %s\. [^\n]*\n(.*?)(?=^## \d\.|\Z)' % num, t, re.S)
            if not m:
                continue
            a = re.search(r'(?m)^### 答案[^\n]*\n(.*?)(?=^### |^---|\Z)', m.group(1), re.S)
            if a:
                out['问题' + CN[int(num) - 1]] = [l for l in a.group(1).split('\n') if l.strip() and not l.startswith('>')]
    return out


def jigou(sid):
    fn = JIGOU.get(sid)
    if not fn:
        return None
    import pymupdf
    d = pymupdf.open(os.path.join(ROOT, fn))
    return '\n'.join(p.get_text() for p in d)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['prev', 'jigou']); ap.add_argument('sid'); ap.add_argument('--q')
    a = ap.parse_args()
    if a.kind == 'prev':
        p = prev(a.sid)
        if not p:
            sys.exit('%s：没有上一版，跳过。' % a.sid)
        d = os.path.join(BASE, a.sid, '参照_上一版'); os.makedirs(d, exist_ok=True)
        for q, lines in p.items():
            open(os.path.join(d, 'Q%d.txt' % ('一二三四五'.index(q[-1]) + 1)), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
            if a.q and q != a.q:
                continue
            print('\n〔上一版 %s〕' % q); print('\n'.join(lines))
    else:
        t = jigou(a.sid)
        print(t if t else '%s：没有机构参考答案，跳过。' % a.sid)
