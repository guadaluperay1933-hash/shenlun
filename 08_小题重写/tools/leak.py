#!/usr/bin/env python3
"""泄漏检查：python3 leak.py <文件或目录> [...]

把真人卷合集（只取 真人卷统计.json 登记的页）切成 8 字片段，减掉 16 套材料、题干里出现过的片段，
剩下的就是「考生自己写的字」。扫描给定文件，报出和它们重合 ≥8 字的位置（文件、行号、长度），不回显原文。
"""
import sys, os, re, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, ROOT, norm, questions
import pymupdf

N = 8
st = json.load(open(os.path.join(BASE, '真人卷统计.json'), encoding='utf-8'))
lo, hi = (int(x) for x in st['forbidden_pages'].split('-'))
doc = pymupdf.open(os.path.join(ROOT, '21-26广东申论高分答案合集.pdf'))
pages = set()
for papers in st['sets'].values():
    for p in papers:
        s, e = (int(x) for x in p['pages'].split('-'))
        pages.update(i for i in range(s, e + 1) if not lo <= i <= hi)
human = norm(''.join(doc[i - 1].get_text() for i in sorted(pages)))
grams = {human[i:i + N] for i in range(len(human) - N + 1)}
allowed = ''
for f in glob.glob(os.path.join(BASE, 'samples', '*', 'material.txt')):
    allowed += norm(open(f, encoding='utf-8').read()) + '|'
for q in questions():
    allowed += norm(q['stem']) + '|'
grams -= {allowed[i:i + N] for i in range(len(allowed) - N + 1)}

files = []
for a in sys.argv[1:]:
    files += [a] if os.path.isfile(a) else [f for f in glob.glob(os.path.join(a, '**', '*'), recursive=True)
                                           if f.endswith(('.md', '.txt', '.json', '.jsonl'))]
hits = 0
for f in files:
    for ln, line in enumerate(open(f, encoding='utf-8', errors='ignore'), 1):
        e = norm(line)
        i = 0
        while i <= len(e) - N:
            if e[i:i + N] in grams:
                j = i + N
                while j < len(e) and e[j - N + 1:j + 1] in grams:
                    j += 1
                print('%s:%d  重合 %d 字' % (os.path.relpath(f, ROOT), ln, j - i))
                hits += 1
                i = j
            else:
                i += 1
print('共 %d 处。' % hits)
sys.exit(1 if hits else 0)
