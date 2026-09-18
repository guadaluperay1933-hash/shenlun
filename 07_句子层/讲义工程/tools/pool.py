#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配例子用的候选池：按 case / slot 列出已匹配好的分句，并把 clauses.jsonl 里那一小截 quote
**还原成 material.txt 里的完整原句**（讲义要求 source.text 给完整句子）。

用法（仓库根目录运行）：
  python3 07_句子层/讲义工程/tools/pool.py --case C8              # 某种情况的全部分句
  python3 07_句子层/讲义工程/tools/pool.py --case C8 --n 40
  python3 07_句子层/讲义工程/tools/pool.py --slot 收束
  python3 07_句子层/讲义工程/tools/pool.py --sample 2025选调 --slot 观点
  python3 07_句子层/讲义工程/tools/pool.py --q12 --case C11       # 小题
  python3 07_句子层/讲义工程/tools/pool.py --expand 2025选调 "保障海洋牧场"   # 只做还原
  python3 07_句子层/讲义工程/tools/pool.py --json --case C3       # 直接吐 JSON 片段

输出里的「完整原句」可以直接抄进 data/*.json 的 source.text；「留下」是建议的 kept，自己复核。
"""
import argparse, glob, json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
SAMPLES = os.path.join(ROOT, '07_句子层', 'samples')
OUT = os.path.join(ROOT, '07_句子层', 'out')
QC = '“”‘’"\'「」『』《》〈〉'
SENT_END = '。！？；'

def norm(s):
    s = unicodedata.normalize('NFKC', s or '')
    s = re.sub(r'\s+', '', s)
    for ch in QC:
        s = s.replace(ch, '')
    return s

_mat = {}
def material(sample):
    if sample not in _mat:
        p = os.path.join(SAMPLES, sample, 'material.txt')
        _mat[sample] = open(p, encoding='utf-8').read() if os.path.exists(p) else ''
    return _mat[sample]

def sentences(sample):
    """把 material.txt 切成句子。material.txt 里有不少句子被 PDF 的换行断开，
    所以先按「上一行不是以句末标点结束、下一行又不是材料标记」把行接回去，再切句。"""
    key = ('S', sample)
    if key not in _mat:
        raw = [l.strip() for l in material(sample).split('\n')]
        paras, buf = [], ''
        for ln in raw:
            if not ln:
                if buf:
                    paras.append(buf); buf = ''
                continue
            if ln.startswith('【') or re.match(r'^(材料|资料|问题)[一二三四五六七八九十0-9]', ln):
                if buf:
                    paras.append(buf); buf = ''
                paras.append(ln); continue
            if buf and buf[-1] not in SENT_END:
                buf += ln            # 上一行没写完，接上
            else:
                if buf:
                    paras.append(buf)
                buf = ln
        if buf:
            paras.append(buf)
        out = []
        for para in paras:
            b = ''
            for ch in para:
                b += ch
                if ch in SENT_END:
                    out.append(b.strip()); b = ''
            if b.strip():
                out.append(b.strip())
        _mat[key] = out
    return _mat[key]

def expand(sample, quote, span=1):
    """把一小截 quote 还原成它所在的完整句子；找不到就返回 None。
    span>1 时连着把后面几句也带上（原句意思要靠下一句才完整时用）。"""
    q = norm(quote)
    if not q:
        return None
    ss = sentences(sample)
    for i, s in enumerate(ss):
        if q in norm(s):
            return ''.join(ss[i:i + span])
    # 跨句：拼相邻两句再找
    for i in range(len(ss) - 1):
        two = ss[i] + ss[i + 1]
        if q in norm(two):
            return two
    for i in range(len(ss) - 2):
        three = ss[i] + ss[i + 1] + ss[i + 2]
        if q in norm(three):
            return three
    return None

def rows(which='clauses'):
    for f in sorted(glob.glob(os.path.join(OUT, '*', which + '.jsonl'))):
        sample = os.path.basename(os.path.dirname(f))
        for line in open(f, encoding='utf-8'):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if which == 'q12':
                for b in r.get('body') or []:
                    b = dict(b)
                    b['_q'] = r.get('q'); b['_point'] = r.get('point')
                    b['_label'] = r.get('label'); b['slot'] = f"小题{r.get('q')}"
                    yield sample, b
            else:
                yield sample, r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case'); ap.add_argument('--slot'); ap.add_argument('--sample')
    ap.add_argument('--q12', action='store_true')
    ap.add_argument('--n', type=int, default=200)
    ap.add_argument('--span', type=int, default=1)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--expand', nargs=2, metavar=('SAMPLE', 'QUOTE'))
    a = ap.parse_args()

    if a.expand:
        s = expand(a.expand[0], a.expand[1], a.span)
        print(s if s else '[找不到] 请检查 quote 是不是来自这个样本')
        return

    which = 'q12' if a.q12 else 'clauses'
    got = []
    for sample, r in rows(which):
        if a.sample and sample != a.sample:
            continue
        if a.case and str(r.get('case', '')).split('+')[0] != a.case and str(r.get('case', '')) != a.case:
            continue
        if a.slot and a.slot not in str(r.get('slot', '')):
            continue
        srcs = []
        for s in r.get('sources', []) or []:
            full = expand(sample, s.get('quote', ''), a.span)
            srcs.append({'material': s.get('material', ''), 'quote': s.get('quote', ''),
                         'text': full or '[未还原，请手工回 material.txt 取]'})
        got.append({'sample': sample, 'slot': r.get('slot', ''), 'case': r.get('case', ''),
                    'product': r.get('text', ''), 'glue': r.get('glue', ''),
                    'self_made_part': r.get('self_made_part', ''), 'note': r.get('note', ''),
                    'sources': srcs,
                    **({'q': r.get('_q'), 'point': r.get('_point'), 'label': r.get('_label')} if a.q12 else {})})
        if len(got) >= a.n:
            break

    if a.json:
        json.dump(got, sys.stdout, ensure_ascii=False, indent=2)
        return
    print(f'共 {len(got)} 条\n')
    for i, g in enumerate(got, 1):
        print(f"[{i}] {g['sample']} · {g['slot']} · {g['case']}")
        for s in g['sources']:
            print(f"    完整原句（材料{s['material']}）：{s['text']}")
            print(f"    留下（来自 quote，需复核）：{s['quote']}")
        print(f"    成品：{g['product']}")
        if g['glue']:
            print(f"    胶水：{g['glue']}")
        if g['self_made_part']:
            print(f"    自造：{g['self_made_part']}")
        if g['note']:
            print(f"    备注：{g['note']}")
        print()

if __name__ == '__main__':
    main()
