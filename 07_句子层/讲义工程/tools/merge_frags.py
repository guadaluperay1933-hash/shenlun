#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 data/_frag/ 下的例子碎片并进 data/*.json。

碎片文件名：<目标文件名>__<随便什么标签>.json，内容是
  {"节点 id": [例子, 例子, ...], "另一个节点 id": [...]}
或给「用法」用的
  {"节点 id": {"usages": [用法, ...]}}

这样多个 agent 可以同时写各自的碎片，不会互相覆盖；并进去由这个脚本统一做。
并的时候只动 examples / usages，其余字段一律不碰。

用法（仓库根目录运行）：
  python3 07_句子层/讲义工程/tools/merge_frags.py            # 并全部
  python3 07_句子层/讲义工程/tools/merge_frags.py --dry      # 只看会并什么
"""
import argparse, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, '..', 'data'))
FRAG = os.path.join(DATA, '_frag')


def key_ex(e):
    """一条例子的身份：样本＋成品（或第一截）＋标题。用来防止同一条被并入两次。"""
    prod = e.get('product') or (e.get('parts') or [{}])[0].get('text', '')
    return (e.get('sample', ''), (prod or '')[:60], (e.get('title') or '')[:40])


def key_us(u):
    return (u.get('sample', ''), (u.get('sentence') or '')[:60], u.get('focus', ''))


dup = [0]


def index(nodes, acc):
    for n in nodes:
        acc[n['id']] = n
        if n.get('children'):
            index(n['children'], acc)
    return acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    if not os.path.isdir(FRAG):
        print('没有 _frag 目录，什么都不用并')
        return
    by_target = {}
    for f in sorted(glob.glob(os.path.join(FRAG, '*.json'))):
        base = os.path.basename(f)
        if '__' not in base:
            print(f'[跳过] 文件名里没有 __：{base}')
            continue
        target = base.split('__')[0] + '.json'
        by_target.setdefault(target, []).append(f)

    total_ex = total_us = 0
    miss = []
    for target, frags in sorted(by_target.items()):
        p = os.path.join(DATA, target)
        if not os.path.exists(p):
            print(f'[跳过] 目标文件不存在：{target}')
            continue
        doc = json.load(open(p, encoding='utf-8'))
        idx = index(doc['nodes'], {})
        added_ex = added_us = 0
        for f in frags:
            frag = json.load(open(f, encoding='utf-8'))
            for nid, payload in frag.items():
                node = idx.get(nid)
                if node is None:
                    miss.append(f'{os.path.basename(f)} → 找不到节点 {nid!r}')
                    continue
                if isinstance(payload, dict):
                    exs = payload.get('examples', []) or []
                    uss = payload.get('usages', []) or []
                else:
                    exs, uss = payload, []
                if exs:
                    node.setdefault('examples', [])
                    have = {key_ex(e) for e in node['examples']}
                    for e in exs:
                        k = key_ex(e)
                        if k in have:      # 同一条重复并入（碎片被并过一次又留了副本）就跳过
                            dup[0] += 1
                            continue
                        have.add(k)
                        node['examples'].append(e)
                        added_ex += 1
                if uss:
                    node.setdefault('usages', [])
                    haveu = {key_us(u) for u in node['usages']}
                    for u in uss:
                        k = key_us(u)
                        if k in haveu:
                            dup[0] += 1
                            continue
                        haveu.add(k)
                        node['usages'].append(u)
                        added_us += 1
        total_ex += added_ex
        total_us += added_us
        print(f'{target}：并入例子 {added_ex} 条、用法 {added_us} 条（碎片 {len(frags)} 个）')
        if not a.dry:
            json.dump(doc, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'\n合计并入例子 {total_ex} 条、用法 {total_us} 条'
          + (f'；跳过重复 {dup[0]} 条' if dup[0] else ''))
    if miss:
        print(f'\n[对不上的节点 id] {len(miss)} 处：')
        for m in miss:
            print('  - ' + m)
        sys.exit(1)
    if a.dry:
        print('（--dry，没有写文件）')


if __name__ == '__main__':
    main()
