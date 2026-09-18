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

    if any(os.path.exists(os.path.join(a.out, i, 'card.json')) for i in ids):
        print()
        card_stats(a.out, ids)

    if a.json:
        json.dump({'cases': dict(tot), 'slots': dict(slot)}, sys.stdout, ensure_ascii=False, indent=2)



# ---------------------------------------------------------------- 槽位统计（思路卡）

def short(s, n=28):
    s = re.sub(r'\s+', '', str(s or ''))
    return s[:n]

CANON = {
 '标题形式': ['两个动宾','比喻式','四字＋以A打造B','其他'],
 '落点': ['近目标','上层目标'],
 'slot': ['引语','解题','家底','靶子','预告','观点','道理','数据','总括','证据','收束','意象','点名','落点','其他'],
 '推法': ['缺口','职责帽','形势','换阶段','自己的目标','重要性','其他'],
 '观点句来源': ['材料判断句','题干落点','材料里现成的一组标签','自造句框'],
 '道理句': ['抄','改','造','无'],
 '收束类型': ['补短板才能','正……','抄材料末句','比喻','让……','回到B','无'],
 '意象': ['抄材料','自造','无'],
 '点名': ['配角色词','不配词','无'],
}

def canon(val, kind):
    """把带括号说明、带斜杠并列的取值归回口径表里的标准值；归不上的返回 '其他(未归类)'。"""
    raw = re.sub(r'\s+', '', str(val or ''))
    raw = re.split(r'[（(]', raw)[0]          # 砍掉括号里的说明
    outs = []
    for part in re.split(r'[／/、]', raw):
        part = part.strip()
        if not part:
            continue
        hit = None
        for c in CANON.get(kind, []):
            if part == c or part.startswith(c) or c.startswith(part):
                hit = c
                break
        outs.append(hit or ('其他(未归类):' + part[:12]))
    return outs or ['无']

def canon1(val, kind):
    return canon(val, kind)[0]


def card_stats(out_dir, ids):
    """从 card.json 汇出槽位统计（汇总.md 第 4 节）。"""
    import os
    cards = {}

    for sid in ids:
        p = os.path.join(out_dir, sid, 'card.json')
        if os.path.exists(p):
            cards[sid] = json.load(open(p, encoding='utf-8'))

    by_genre = defaultdict(list)
    for sid, c in cards.items():
        by_genre[c.get('genre', '?')].append(sid)

    print('# 槽位统计（来自十二张思路卡）\n')
    print('体裁分布：' + '；'.join(f'{g} {len(v)} 篇（{"、".join(v)}）' for g, v in by_genre.items()))

    print('\n## 标题')
    print('| 样本 | 体裁 | 形式 | 落点 | 原文 |'); print('|---|---|---|---|---|')
    for sid, c in cards.items():
        t = c.get('标题', {}) or {}
        print(f"| {sid} | {c.get('genre','')} | {short(t.get('形式'),40)} | {t.get('落点','')} | {t.get('原文','')} |")
    f = Counter(canon1((c.get('标题') or {}).get('形式'), '标题形式') for c in cards.values())
    print('\n形式计数：' + '；'.join(f'{k} {v}' for k, v in f.most_common()))
    d = Counter(canon1((c.get('标题') or {}).get('落点'), '落点') for c in cards.values())
    print('落点计数：' + '；'.join(f'{k} {v}' for k, v in d.most_common()))

    print('\n## 开头：slot 出现比例与顺序')
    print('| 样本 | 体裁 | slot 顺序 | 句数 |'); print('|---|---|---|---|')
    slotc = Counter(); orders = Counter()
    for sid, c in cards.items():
        ss = ['／'.join(canon(s.get('slot'), 'slot')) for s in ((c.get('开头') or {}).get('句子') or [])]
        for s in {x for s0 in ss for x in s0.split('／')}:
            slotc[s] += 1
        orders['→'.join(ss)] += 1
        print(f"| {sid} | {c.get('genre','')} | {'→'.join(ss)} | {len(ss)} |")
    n = len(cards) or 1
    print('\n| 开头 slot | 出现篇数 | 比例 |'); print('|---|---|---|')
    for k, v in slotc.most_common():
        print(f'| {k} | {v} | {v/n:.0%} |')

    print('\n## 开头：推法')
    tui = Counter(); 
    print('| 样本 | 推法 |'); print('|---|---|')
    for sid, c in cards.items():
        ts = [canon1(t.get('类型'), '推法') for t in ((c.get('开头') or {}).get('推法') or [])]
        for t in set(ts):
            tui[t] += 1
        print(f"| {sid} | {'、'.join(ts)} |")
    print('\n| 推法 | 出现篇数 | 比例 |'); print('|---|---|---|')
    for k, v in tui.most_common():
        print(f'| {k} | {v} | {v/n:.0%} |')

    print('\n## 观点句来源')
    src = Counter(); src_g = defaultdict(Counter)
    for sid, c in cards.items():
        for p in c.get('段落') or []:
            k = canon1(p.get('观点句来源'), '观点句来源')
            src[k] += 1; src_g[c.get('genre','')][k] += 1
    print('| 来源 | 分论点数 | 比例 |'); print('|---|---|---|')
    tot = sum(src.values()) or 1
    for k, v in src.most_common():
        print(f'| {k} | {v} | {v/tot:.0%} |')
    for g, cc in src_g.items():
        print(f"\n{g}：" + '；'.join(f'{k} {v}' for k, v in cc.most_common()))

    print('\n## 中间段：句数、句长、证据、数字、道理句、收束')
    print('| 样本 | 体裁 | 段数 | 每段句数 | 句长范围 | 证据个数 | 数字个数 | 材料外例子 | 道理句 | 收束类型 |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    dao = Counter(); shou = Counter(); allsent = []; allev = []; allnum = []; allw = 0
    for sid, c in cards.items():
        ms = c.get('中间段') or []
        sent = [m.get('句数', 0) for m in ms]
        lens = [x for m in ms for x in (m.get('句长') or [])]
        ev = [m.get('证据个数', 0) for m in ms]
        nu = [m.get('数字个数', 0) for m in ms]
        w = sum(m.get('材料外例子个数', 0) for m in ms)
        allsent += sent; allev += ev; allnum += nu; allw += w
        for m in ms:
            dao[canon1(m.get('道理句'), '道理句')] += 1
            shou[canon1(m.get('收束类型'), '收束类型')] += 1
        print(f"| {sid} | {c.get('genre','')} | {len(ms)} | {'/'.join(map(str,sent))} | "
              f"{min(lens) if lens else 0}–{max(lens) if lens else 0} | {'/'.join(map(str,ev))} | "
              f"{'/'.join(map(str,nu))} | {w} | "
              f"{'/'.join(canon1(m.get('道理句'),'道理句') for m in ms)} | {'/'.join(canon1(m.get('收束类型'),'收束类型') for m in ms)} |")
    if allsent:
        print(f'\n中间段合计 {len(allsent)} 段：句数 {min(allsent)}–{max(allsent)}（均 {sum(allsent)/len(allsent):.1f}）；'
              f'证据 {min(allev)}–{max(allev)}（均 {sum(allev)/len(allev):.1f}）；'
              f'数字 {min(allnum)}–{max(allnum)}（均 {sum(allnum)/len(allnum):.1f}）；材料外例子共 {allw} 个')
    print('\n| 道理句 | 段数 | 比例 |'); print('|---|---|---|')
    t2 = sum(dao.values()) or 1
    for k, v in dao.most_common():
        print(f'| {k} | {v} | {v/t2:.0%} |')
    print('\n| 收束类型 | 段数 |'); print('|---|---|')
    for k, v in shou.most_common():
        print(f'| {k} | {v} |')

    print('\n## 结尾')
    print('| 样本 | 体裁 | 句数 | 意象 | 说大一圈 | 点名 | 落点词 |'); print('|---|---|---|---|---|---|---|')
    yx = Counter(); dm = Counter(); ld = Counter(); shuo = 0
    for sid, c in cards.items():
        e = c.get('结尾') or {}
        yx[canon1(e.get('意象'), '意象')] += 1; dm[canon1(e.get('点名'), '点名')] += 1
        ld[short(e.get('落点词'), 20)] += 1
        if str(e.get('说大一圈') or '').strip():
            shuo += 1
        print(f"| {sid} | {c.get('genre','')} | {e.get('句数','')} | {canon1(e.get('意象'),'意象')} | "
              f"{short(e.get('说大一圈'),24)} | {canon1(e.get('点名'),'点名')} | {short(e.get('落点词'),22)} |")
    print(f'\n意象：' + '；'.join(f'{k} {v}' for k, v in yx.most_common()))
    print(f'点名：' + '；'.join(f'{k} {v}' for k, v in dm.most_common()))
    print(f'说大一圈：{shuo}/{n} 篇填了')
    print('落点词：' + '；'.join(f'{k} {v}' for k, v in ld.most_common()))

    print('\n## 问题的写法')
    print('| 样本 | 条数 | 主语是广东 | 定语 | 谓语 |'); print('|---|---|---|---|---|')
    zt = Counter(); dy = Counter()
    for sid, c in cards.items():
        ps = c.get('问题的写法') or []
        a = sum(1 for p in ps if p.get('主语是不是广东'))
        d1 = sum(1 for p in ps if '定语' in str(p.get('缺点做定语还是谓语', '')))
        d2 = sum(1 for p in ps if '谓语' in str(p.get('缺点做定语还是谓语', '')))
        zt['是' if a else '否'] += 1
        dy['定语'] += d1; dy['谓语'] += d2
        print(f'| {sid} | {len(ps)} | {a} | {d1} | {d2} |')
    print(f"\n全部问题句：定语 {dy['定语']} 条，谓语 {dy['谓语']} 条")

    print('\n## 材料露脸')
    print('| 样本 | 用到 | 没用到 | 完整度 |'); print('|---|---|---|---|')
    for sid, c in cards.items():
        m = c.get('材料露脸') or {}
        u = m.get('用到') or []; nu2 = m.get('没用到') or []
        tt = len(u) + len(nu2)
        print(f"| {sid} | {len(u)}（{'、'.join(u)}） | {len(nu2)}（{'、'.join(nu2)}） | {len(u)}/{tt} = {len(u)/tt:.0%} |" if tt else f'| {sid} | | | |')

    print('\n## 小题要点进大作文')
    print('| 样本 | 进了大作文的要点数 |'); print('|---|---|')
    for sid, c in cards.items():
        print(f"| {sid} | {len(c.get('小题与大作文') or [])} |")


if __name__ == '__main__':
    main()
