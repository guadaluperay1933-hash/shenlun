#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核对分句匹配结果。大作文的 clauses.jsonl 和小题的 q12.jsonl 都能直接查。

用法：
  python 07_句子层/tools/check_quotes.py --material 07_句子层/samples/<id>/material.txt --clauses 07_句子层/out/<id>/clauses.jsonl
  python 07_句子层/tools/check_quotes.py --material ... --clauses ... --gold 07_句子层/gold/<文件>   # 同时和校准集比对

检查三件事：
  1. 每条 sources[].quote 是否一字不差地出现在材料里（忽略空白、引号、全半角差异）。
  2. 标成自造（case 为 "Z"，或填了 self_made_part）的文字，和材料的最长重合有多长；
     重合 >= --overlap（默认 6 个字）的列出来，提醒复核是不是其实有出处。
  3. 按 case、按 slot 计数，给出覆盖率。

只要有一条 quote 在材料里找不到，退出码为 1。
"""
import argparse, json, sys, unicodedata, re
from collections import Counter

QUOTE_CHARS = '“”‘’"\'「」『』《》〈〉'

def norm(s: str) -> str:
    s = unicodedata.normalize('NFKC', s or '')
    s = re.sub(r'\s+', '', s)
    for ch in QUOTE_CHARS:
        s = s.replace(ch, '')
    return s

def longest_common_substring(short: str, long: str):
    """返回 short 中出现在 long 里的最长片段（靠 C 实现的 in 查找，够快）。"""
    best, best_s = 0, ''
    n = len(short)
    for i in range(n):
        j = i + best + 1
        while j <= n and short[i:j] in long:
            best, best_s = j - i, short[i:j]
            j += 1
    return best, best_s

def load_jsonl(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f'[格式错误] {path} 第 {ln} 行不是合法 JSON：{e}')
                sys.exit(2)
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--material', required=True)
    ap.add_argument('--clauses', required=True)
    ap.add_argument('--gold')
    ap.add_argument('--overlap', type=int, default=6)
    a = ap.parse_args()

    mat = norm(open(a.material, encoding='utf-8').read())
    rows = load_jsonl(a.clauses)
    # 小题文件（q12.jsonl）每行有 body 列表：摊平成一行一条再查
    flat = []
    for r in rows:
        if isinstance(r.get('body'), list):
            for b in r['body']:
                b = dict(b)
                b.setdefault('slot', f"小题{r.get('q','')}")
                flat.append(b)
        else:
            flat.append(r)
    rows = flat

    bad, suspicious = [], []
    by_case, by_slot = Counter(), Counter()
    for r in rows:
        case = str(r.get('case', '')).strip() or '空'
        by_case[case] += 1
        by_slot[str(r.get('slot', '空'))] += 1
        for s in r.get('sources', []) or []:
            q = norm(s.get('quote', ''))
            if not q:
                continue
            if q not in mat:
                n, frag = longest_common_substring(q, mat)
                bad.append((r.get('text', ''), s.get('quote', ''), n, frag))
        sm = r.get('self_made_part') or (r.get('text') if case == 'Z' else '')
        if sm:
            n, frag = longest_common_substring(norm(sm), mat)
            if n >= a.overlap:
                suspicious.append((r.get('text', ''), sm, n, frag))

    total = len(rows)
    print(f'分句总数：{total}')
    print('按 case：', dict(sorted(by_case.items())))
    print('按 slot：', dict(sorted(by_slot.items())))
    covered = sum(v for k, v in by_case.items() if k.startswith('C') or k == 'F')
    if total:
        print(f'落在十二种情况或句框里的：{covered}/{total} = {covered/total:.0%}；'
              f'自造 Z：{by_case.get("Z",0)}；材料外 W：{by_case.get("W",0)}；其他 O：{by_case.get("O",0)}')
        zchars = sum(len(norm(r.get('self_made_part') or (r.get('text') if str(r.get('case'))=='Z' else ''))) for r in rows)
        wchars = sum(len(norm(r.get('text',''))) for r in rows if str(r.get('case'))=='W')
        allchars = sum(len(norm(r.get('text',''))) for r in rows) or 1
        print(f'按字数：自造 {zchars} 字（{zchars/allchars:.0%}），材料外 {wchars} 字（{wchars/allchars:.0%}），全文 {allchars} 字')

    if suspicious:
        print(f'\n[复核] 标成自造、但和材料重合 >= {a.overlap} 字的有 {len(suspicious)} 处：')
        for text, sm, n, frag in suspicious:
            print(f'  - 自造部分「{sm}」与材料重合 {n} 字：「{frag}」')

    if bad:
        print(f'\n[不通过] 有 {len(bad)} 条 quote 在材料里找不到：')
        for text, q, n, frag in bad:
            print(f'  - 分句「{text}」\n    quote「{q}」\n    材料里最长能对上的只有 {n} 字：「{frag}」')
    else:
        print('\n[通过] 所有 quote 都能在材料里原样找到。')

    if a.gold:
        gold = load_jsonl(a.gold)
        pred = {norm(r.get('text', '')): r for r in rows}
        hit_src = hit_case = found = 0
        misses = []
        for g in gold:
            gt = norm(g['text'])
            p = pred.get(gt)
            if p is None:  # 允许预测的分句更长或更短，只要互相包含
                for k, v in pred.items():
                    if gt and (gt in k or k in gt):
                        p = v
                        break
            if p is None:
                misses.append(('没找到对应分句', g['text']))
                continue
            found += 1
            gq = [norm(s['quote']) for s in g.get('sources', [])]
            pq = [norm(s.get('quote', '')) for s in p.get('sources', []) or []]
            if not gq:
                src_ok = (not pq) or str(p.get('case')) == 'Z'
            else:
                src_ok = any(longest_common_substring(x, y)[0] >= min(8, len(x)) for x in gq for y in pq)
            case_ok = str(p.get('case', '')).split('+')[0] == str(g.get('case', '')).split('+')[0]
            hit_src += src_ok
            hit_case += case_ok
            if not (src_ok and case_ok):
                misses.append((f'来源{"对" if src_ok else "错"}，情况{"对" if case_ok else "错"}'
                               f'（校准集 {g.get("case")}，你标 {p.get("case")}）', g['text']))
        n = len(gold)
        print(f'\n和校准集比对：{n} 条里找到对应分句 {found} 条；来源对上 {hit_src} 条；情况标对 {hit_case} 条。')
        for why, text in misses:
            print(f'  - {why}：{text}')

    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
