#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 out/<id>/clauses.jsonl、q12.jsonl、card.json 汇成统计表，给 out/汇总.md 用。

用法：python 07_句子层/tools/stats.py [--out 07_句子层/out] [--json]
"""
import argparse, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

QUOTE_CHARS = '“”‘’"\'「」『』《》〈〉'
CASES = [f'C{i}' for i in range(1, 13)] + ['F', 'Z', 'W', 'O']

def norm(s):
    s = unicodedata.normalize('NFKC', s or '')
    s = re.sub(r'\s+', '', s)
    for ch in QUOTE_CHARS:
        s = s.replace(ch, '')
    return s

def load_jsonl(p):
    rows = []
    with open(p, encoding='utf-8') as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f'[格式错误] {p}:{ln} {e}', file=sys.stderr)
                    sys.exit(2)
    return rows

def main_case(c):
    return str(c or '').split('+')[0].strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='07_句子层/out')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    ids = sorted(d for d in os.listdir(a.out) if os.path.isdir(os.path.join(a.out, d)))
    per, cards = {}, {}
    for sid in ids:
        d = os.path.join(a.out, sid)
        rec = {'id': sid}
        cp = os.path.join(d, 'card.json')
        if os.path.exists(cp):
            cards[sid] = json.load(open(cp, encoding='utf-8'))
            rec['genre'] = cards[sid].get('genre', '')
        fp = os.path.join(d, 'clauses.jsonl')
        if os.path.exists(fp):
            rec['clauses'] = load_jsonl(fp)
        qp = os.path.join(d, 'q12.jsonl')
        if os.path.exists(qp):
            rec['q12'] = load_jsonl(qp)
        per[sid] = rec

    # ---- 作文覆盖率
    print('## 大作文 · 按 case')
    tot = Counter(); by_genre = defaultdict(Counter); rows = []
    for sid, rec in per.items():
        cs = rec.get('clauses') or []
        if not cs:
            continue
        c = Counter(main_case(r.get('case')) for r in cs)
        g = rec.get('genre') or '?'
        tot += c; by_genre[g] += c
        chars = sum(len(norm(r.get('text', ''))) for r in cs)
        z = sum(len(norm(r.get('self_made_part') or (r.get('text') if main_case(r.get('case')) == 'Z' else ''))) for r in cs)
        w = sum(len(norm(r.get('text', ''))) for r in cs if main_case(r.get('case')) == 'W')
        cov = sum(v for k, v in c.items() if k.startswith('C') or k == 'F')
        rows.append((sid, g, len(cs), cov, chars, z, w, c))
    hdr = '| 样本 | 体裁 | 分句 | C1–C12+F | 占比 | 全文字 | 自造字 | 材料外字 | ' + ' | '.join(CASES) + ' |'
    print(hdr); print('|' + '---|' * (9 + len(CASES)))
    for sid, g, n, cov, chars, z, w, c in rows:
        print(f'| {sid} | {g} | {n} | {cov} | {cov/n:.0%} | {chars} | {z} | {w} | '
              + ' | '.join(str(c.get(k, 0) or '') for k in CASES) + ' |')
    n = sum(r[2] for r in rows) or 1
    cov = sum(r[3] for r in rows)
    print(f'| **合计** | | {n} | {cov} | {cov/n:.0%} | {sum(r[4] for r in rows)} | {sum(r[5] for r in rows)} | {sum(r[6] for r in rows)} | '
          + ' | '.join(str(tot.get(k, 0) or '') for k in CASES) + ' |')
    for g, c in by_genre.items():
        s = sum(c.values()) or 1
        print(f'| **{g}小计** | | {s} | | | | | | ' + ' | '.join(str(c.get(k, 0) or '') for k in CASES) + ' |')

    print('\n## 大作文 · case 排序与累计占比')
    s = sum(tot.values()) or 1
    acc = 0
    print('| 名次 | case | 分句数 | 占比 | 累计 |'); print('|---|---|---|---|---|')
    for i, (k, v) in enumerate(sorted(tot.items(), key=lambda x: -x[1]), 1):
        acc += v
        print(f'| {i} | {k} | {v} | {v/s:.0%} | {acc/s:.0%} |')

    print('\n## 大作文 · 按 slot')
    slot = Counter()
    for rec in per.values():
        for r in rec.get('clauses') or []:
            slot[str(r.get('slot', ''))] += 1
    print('| slot | 分句数 |'); print('|---|---|')
    for k, v in slot.most_common():
        print(f'| {k} | {v} |')

    print('\n## 大作文 · slot × case')
    sc = defaultdict(Counter)
    for rec in per.values():
        for r in rec.get('clauses') or []:
            sc[str(r.get('slot', ''))][main_case(r.get('case'))] += 1
    print('| slot | ' + ' | '.join(CASES) + ' |'); print('|' + '---|' * (1 + len(CASES)))
    for k, c in sorted(sc.items(), key=lambda x: -sum(x[1].values())):
        print(f'| {k} | ' + ' | '.join(str(c.get(x, 0) or '') for x in CASES) + ' |')

    print('\n## 小题 · 按 case')
    qtot = Counter(); qrows = []
    for sid, rec in per.items():
        rs = rec.get('q12') or []
        if not rs:
            continue
        c = Counter()
        for r in rs:
            for b in r.get('body', []) or []:
                c[main_case(b.get('case'))] += 1
        qtot += c
        qrows.append((sid, sum(c.values()), c))
    print('| 样本 | 分句 | ' + ' | '.join(CASES) + ' |'); print('|' + '---|' * (2 + len(CASES)))
    for sid, n0, c in qrows:
        print(f'| {sid} | {n0} | ' + ' | '.join(str(c.get(k, 0) or '') for k in CASES) + ' |')
    qn = sum(r[1] for r in qrows) or 1
    qcov = sum(v for k, v in qtot.items() if k.startswith('C') or k == 'F')
    print(f'| **合计** | {qn} | ' + ' | '.join(str(qtot.get(k, 0) or '') for k in CASES) + ' |')
    print(f'\n小题落在 C1–C12+F 里：{qcov}/{qn} = {qcov/qn:.0%}')

    print('\n## 小题 · 标签来源与形式')
    ls, lf = Counter(), Counter()
    for rec in per.values():
        for r in rec.get('q12') or []:
            ls[str(r.get('label_source', ''))] += 1
            lf[str(r.get('label_form', ''))] += 1
    print('| 标签来源 | 次数 |'); print('|---|---|')
    for k, v in ls.most_common():
        print(f'| {k} | {v} |')
    print('\n| 标签形式 | 次数 |'); print('|---|---|')
    for k, v in lf.most_common():
        print(f'| {k} | {v} |')

    print('\n## glue 词频')
    g = Counter()
    for rec in per.values():
        for r in (rec.get('clauses') or []):
            for t in re.split(r'[、,，/／\s]+', str(r.get('glue') or '')):
                if t.strip():
                    g[t.strip()] += 1
        for r in (rec.get('q12') or []):
            for b in r.get('body', []) or []:
                for t in re.split(r'[、,，/／\s]+', str(b.get('glue') or '')):
                    if t.strip():
                        g[t.strip()] += 1
    print('| glue | 次数 |'); print('|---|---|')
    for k, v in g.most_common():
        if v >= 2:
            print(f'| {k} | {v} |')

    print('\n## 自造清单（Z 与 self_made_part）')
    sm = defaultdict(lambda: [0, set()])
    for sid, rec in per.items():
        for r in rec.get('clauses') or []:
            t = r.get('self_made_part') or (r.get('text') if main_case(r.get('case')) == 'Z' else '')
            if t:
                k = (str(r.get('slot', '')), t.strip())
                sm[k][0] += 1
                sm[k][1].add(sid)
    print('| slot | 自造的字 | 篇数 |'); print('|---|---|---|')
    for (s0, t), (n0, ss) in sorted(sm.items(), key=lambda x: (x[0][0], -x[1][0])):
        print(f'| {s0} | {t} | {len(ss)} |')

    print('\n## O 类逐条')
    print('| 样本 | slot | 分句 | note |'); print('|---|---|---|---|')
    for sid, rec in per.items():
        for r in rec.get('clauses') or []:
            if main_case(r.get('case')) == 'O':
                print(f"| {sid} | {r.get('slot','')} | {r.get('text','')} | {r.get('note','')} |")
        for r in rec.get('q12') or []:
            for b in r.get('body', []) or []:
                if main_case(b.get('case')) == 'O':
                    print(f"| {sid} | 小题{r.get('q','')} | {b.get('text','')} |  |")

    print('\n## W 类逐条（材料外）')
    print('| 样本 | slot | 分句 |'); print('|---|---|---|')
    for sid, rec in per.items():
        for r in rec.get('clauses') or []:
            if main_case(r.get('case')) == 'W':
                print(f"| {sid} | {r.get('slot','')} | {r.get('text','')} |")

    if a.json:
        json.dump({'cases': dict(tot), 'slots': dict(slot)}, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
