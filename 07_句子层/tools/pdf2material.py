#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把试题 PDF 转成 07_句子层/samples/<id>/material.txt。

做三件事：
  1. 按行取文字（带坐标），删掉页眉、页脚、页码、"本试卷由……生成"一类的行。
  2. 用右边距判断段落：一行没顶到右边距就是段末，否则和下一行接上。
     （不这么做，跨页跨行的句子会被打断，后面的原文核对过不了。）
  3. 把各种材料标记（资料1 / 【资料 1】 / 材料一 / 【材料一】）统一成【材料一】，
     作答要求统一成【问题一】。

用法：
  python 07_句子层/tools/pdf2material.py --pdf <试题.pdf> --out 07_句子层/samples/<id>/material.txt \
      [--title "2026 年广东省公考《申论》（省市卷）题"] [--pages 3-40] [--dump]
"""
import argparse, re, sys
from collections import Counter

import pymupdf

CN = '一二三四五六七八九十十一十二十三十四十五十六十七十八十九二十'
CN_NUM = ['一','二','三','四','五','六','七','八','九','十',
          '十一','十二','十三','十四','十五','十六','十七','十八','十九','二十']

DROP_PAT = [
    re.compile(r'^第\s*\d+\s*页(\s*[，,／/]?\s*共\s*\d+\s*页)?$'),
    re.compile(r'^\d{1,3}$'),
    re.compile(r'本试卷由.*生成'),
    re.compile(r'^[-—–]\s*\d+\s*[-—–]$'),
    re.compile(r'^\s*$'),
]

MARK_PAT = re.compile(
    r'^(?:[【\[]?\s*(?:给定)?(?:材料|资料)\s*[【\[]?\s*[0-9一二三四五六七八九十]{1,3}\s*[】\]]?\s*[】\]]?\s*[:：、.．]?'
    r'|[【\[]?\s*(?:问题|第)\s*[0-9一二三四五六七八九十]{1,3}\s*(?:题)?\s*[】\]]?\s*[:：、.．]?'
    r'|[（(][一二三四五六七八九十]{1,3}[）)])\s*$')

def page_lines(page):
    """返回 [(text, x0, x1, y0)]，按阅读顺序。"""
    out = []
    d = page.get_text('dict')
    for blk in d['blocks']:
        if blk.get('type') != 0:
            continue
        for ln in blk['lines']:
            txt = ''.join(sp['text'] for sp in ln['spans'])
            if not txt.strip():
                continue
            x0, y0, x1, y1 = ln['bbox']
            out.append([txt.rstrip(), x0, x1, y0])
    out.sort(key=lambda r: (round(r[3], 1), r[1]))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--out')
    ap.add_argument('--title', default='')
    ap.add_argument('--pages', default='', help='取哪几页，如 3-40（1 起算，含两端）')
    ap.add_argument('--start', default='', help='从匹配这个正则的行开始保留')
    ap.add_argument('--stop', default='', help='遇到匹配这个正则的行就停')
    ap.add_argument('--dump', action='store_true', help='只打印，不写文件')
    a = ap.parse_args()

    doc = pymupdf.open(a.pdf)
    lo, hi = 0, doc.page_count - 1
    if a.pages:
        m = re.match(r'^(\d+)-(\d+)$', a.pages)
        lo, hi = int(m.group(1)) - 1, int(m.group(2)) - 1

    # 先统计每页重复出现的行 = 页眉页脚
    seen = Counter()
    for i in range(lo, hi + 1):
        for t, *_ in page_lines(doc[i]):
            seen[t.strip()] += 1
    npages = hi - lo + 1
    running = {t for t, c in seen.items() if c >= max(3, npages * 0.5) and len(t) < 60}

    paras = []
    for i in range(lo, hi + 1):
        lines = page_lines(doc[i])
        body = [r for r in lines if r[0].strip() not in running
                and not any(p.search(r[0].strip()) for p in DROP_PAT)]
        if not body:
            continue
        right = max(r[2] for r in body)
        for txt, x0, x1, y0 in body:
            t = txt.strip()
            cont = (x1 >= right - 6)          # 顶到右边距 → 和下一行是同一段
            if MARK_PAT.match(t):             # 材料／问题的标记行自成一段，不和上下行粘连
                if paras:
                    paras[-1] = (paras[-1][0], False)
                paras.append((t, False))
                continue
            if paras and paras[-1][1]:
                paras[-1] = (paras[-1][0] + t, cont)
            else:
                paras.append((t, cont))
    text = [p[0] for p in paras]

    # 统一标记
    # （一）（二）（三）只在最后一则材料之后才当作问题标记：材料内部也用它分小节
    MAT_ONLY = re.compile(r'^[【\[]?\s*(?:给定)?(?:材料|资料)\s*[【\[]?\s*[0-9一二三四五六七八九十]{1,3}\s*[】\]]?\s*[】\]]?\s*[:：、.．]?\s*$')
    last_mat = max((i for i, t in enumerate(text) if MAT_ONLY.match(t.strip())), default=-1)
    out, mi, qi = [], 0, 0
    started = not bool(a.start)
    for idx, t in enumerate(text):
        if a.start and not started:
            if re.search(a.start, t):
                started = True
            else:
                continue
        if a.stop and re.search(a.stop, t):
            break
        s = t.strip()
        m = re.match(r'^[【\[]?\s*(?:给定)?(?:材料|资料)\s*[【\[]?\s*([0-9一二三四五六七八九十]{1,3})\s*[】\]]?\s*[】\]]?\s*[:：、.．]?\s*$', s)
        if m:
            mi += 1
            out.append(f'【材料{CN_NUM[mi-1]}】')
            continue
        m2 = re.match(r'^(?:[【\[]?\s*)?(?:问题|第)\s*([0-9一二三四五六七八九十]{1,3})\s*(?:题)?\s*[】\]]?\s*[:：、.．]?\s*$', s) \
             or (idx > last_mat and re.match(r'^[（(]([一二三四五六七八九十]{1,3})[）)]\s*$', s))
        if m2:
            qi += 1
            out.append(f'【问题{CN_NUM[qi-1]}】')
            continue
        if re.match(r'^[一二三]、(给定资料|作答要求)$', s):
            continue
        out.append(s)

    head = a.title.strip()
    body = '\n'.join(x for x in out if x.strip())
    res = (head + '\n' if head else '') + body + '\n'
    if a.dump or not a.out:
        sys.stdout.write(res)
    else:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(res)
        print(f'写出 {a.out}：{len(res)} 字，材料 {mi} 则，问题 {qi} 道')

if __name__ == '__main__':
    main()
