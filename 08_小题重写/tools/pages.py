#!/usr/bin/env python3
"""翻真人卷：python3 pages.py <set_id> [--q 问题一] [--essay]

页号只取 真人卷统计.json 里本套登记的页段，禁区页一律拒绝。逐份打印，标题用「分数 + 起始页」。
默认只打印小题；--essay 才打印大作文；--q 只打印某一题。不写任何文件。
"""
import sys, os, re, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, ROOT
import pymupdf

ap = argparse.ArgumentParser()
ap.add_argument('sid'); ap.add_argument('--q'); ap.add_argument('--essay', action='store_true')
a = ap.parse_args()

st = json.load(open(os.path.join(BASE, '真人卷统计.json'), encoding='utf-8'))
lo, hi = (int(x) for x in st['forbidden_pages'].split('-'))
papers = st['sets'].get(a.sid)
if not papers:
    sys.exit('%s 没有真人卷。' % a.sid)

WM = '一次购买，持续更新'
TPAT = re.compile(r'^(20)?\d\d ?年广东(申论)?.{0,8}?卷\s*[\d.]+\+? ?分')
QPAT = re.compile(r'^(第[一二三四五1-5]题|[一二三四五]、|请根据材料)')
ENDPAT = re.compile(r'(不超过 ?\d+$|^字[。）)]*$|\d+ ?字[。）)】\s]*$|[）)]\s*$|字左右[。）]*$|以内[。）]*$)')
doc = pymupdf.open(os.path.join(ROOT, '21-26广东申论高分答案合集.pdf'))


def lines_of(p):
    s, e = (int(x) for x in p['pages'].split('-'))
    if not (e < lo or s > hi):
        sys.exit('拒绝：页段 %s 落在禁区 %s。' % (p['pages'], st['forbidden_pages']))
    out, on = [], False
    for i in range(s - 1, e):
        for raw in doc[i].get_text().splitlines():
            l = raw.strip()
            if not l or WM in l or re.match(r'^- ?\d+ ?-?$', l):
                continue
            if TPAT.match(l):
                on = (re.sub(r'\s', '', l) == re.sub(r'\s', '', p['title']))
                continue
            if on:
                out.append(l)
    return out


def segments(L):
    def is_header(k):
        return QPAT.match(L[k]) and len(L[k]) > 6 and any(re.search(r'\d+ ?字|要求|篇幅', w) for w in L[k:k + 5])
    segs, stem, body, state = [], '', [], 'pre'
    for k, l in enumerate(L):
        if is_header(k):
            if state != 'pre':
                segs.append((stem, body))
            stem, body = l, []
            state = 'body' if ENDPAT.search(l) else 'stem'
            continue
        if state == 'stem':
            stem += l
            if ENDPAT.search(l):
                state = 'body'
            continue
        if state != 'pre':
            body.append(l)
    if state != 'pre':
        segs.append((stem, body))
    out = []
    for stem, body in segs:
        m = re.match(r'第([一二三四五1-5])题|([一二三四五])、', stem)
        k = (m.group(1) or m.group(2)) if m else '一'
        n = '一二三四五'.index(k) + 1 if k in '一二三四五' else int(k)
        essay = bool(re.search(r'(议论文|策论文|自拟题目|自拟标题|(8|9|10|12)00 ?字|深入思考)', stem))
        out.append(('大作文' if essay else '问题' + '一二三四五'[n - 1], body))
    return out


for p in papers:
    segs = segments(lines_of(p))
    print('\n' + '=' * 60)
    print('【%s 分　p%s】' % (p['score'], p['pages']))
    if not segs:
        print('（切不出题目，整份打印）')
        print('\n'.join(lines_of(p)))
        continue
    for q, body in segs:
        if a.q and q != a.q:
            continue
        if q == '大作文' and not a.essay:
            print('\n〔大作文，合集收了 %d 字，略〕' % sum(len(x) for x in body))
            continue
        print('\n〔%s〕' % q)
        print('\n'.join(body))
