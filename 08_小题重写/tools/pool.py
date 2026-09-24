#!/usr/bin/env python3
"""句池：python3 pool.py <set_id> [--blocks 三,五 | --q 问题一] [--clause]

打印指定则（不给就全卷）的编号句池：段号 p1 p2…，句号 1 2…，--clause 再按「，、：」出 a b c。
编号写法「三-p12-1a」＝材料三第 12 段第 1 句第 a 分句。全卷句池存 _pool/<set_id>.json。
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, split_blocks, sentences, clauses, question

ap = argparse.ArgumentParser()
ap.add_argument('sid')
ap.add_argument('--blocks')
ap.add_argument('--q')
ap.add_argument('--clause', action='store_true')
a = ap.parse_args()

blocks = split_blocks(a.sid)
pool = {}
for name, paras in blocks:
    for pi, p in enumerate(paras, 1):
        for si, s in enumerate(sentences(p), 1):
            pool['%s-p%d-%d' % (name, pi, si)] = s
            for ci, c in enumerate(clauses(s)):
                pool['%s-p%d-%d%s' % (name, pi, si, 'abcdefghijklmnopqrstuvwxyz'[min(ci, 25)])] = c
os.makedirs(os.path.join(BASE, '_pool'), exist_ok=True)
json.dump({'blocks': {n: ps for n, ps in blocks}, 'ids': pool},
          open(os.path.join(BASE, '_pool', a.sid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

want = None
if a.blocks:
    want = a.blocks.replace('，', ',').split(',')
elif a.q:
    want = question(a.sid, a.q)['blocks'] or None
for name, paras in blocks:
    if want and name not in want:
        continue
    print('\n######## %s（%d 段）########' % ('导语' if name == '导' else '材料' + name, len(paras)))
    for pi, p in enumerate(paras, 1):
        print('\n[%s-p%d]' % (name, pi))
        for si, s in enumerate(sentences(p), 1):
            if a.clause:
                for ci, c in enumerate(clauses(s)):
                    print('  %s-p%d-%d%s  %s' % (name, pi, si, 'abcdefghijklmnopqrstuvwxyz'[min(ci, 25)], c.strip()))
            else:
                print('  %s-p%d-%d  %s' % (name, pi, si, s.strip()))
