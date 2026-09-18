#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核对讲义数据里的每一条引文是不是原话。

用法（在仓库根目录运行）：
  python 07_句子层/讲义工程/tools/verify_examples.py "07_句子层/讲义工程/data/*.json"

查四件事：
  1. source[].text 必须一字不差地出现在对应样本的 material.txt 里（忽略空白、引号、全半角）。
     source[].from 为 "essay" 时，改为去该样本的 essay.txt / q12.txt 里找。
  2. source[].kept 里的每个片段必须出现在它所属的 source.text 里。
  3. product 必须出现在对应样本的 essay.txt 或 q12.txt 里（product_is_mine 为 true 的除外）。
     parts[].text（把定稿的一整段按拍子切开时用）必须在定稿里；parts[].source 同第 1、2 条。
  4. usages[].sentence 必须出现在 essay.txt 或 q12.txt 里，且包含 focus。
另外统计每个节点的例子数，列出低于 min_examples 的节点。
任何一条不过，退出码为 1。
"""
import json, sys, re, unicodedata, os, glob

SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'samples')
QUOTE_CHARS = '“”‘’"\'「」『』《》〈〉'


def norm(s):
    s = unicodedata.normalize('NFKC', s or '')
    s = re.sub(r'\s+', '', s)
    for ch in QUOTE_CHARS:
        s = s.replace(ch, '')
    return s


_cache = {}


def load(sample, name):
    key = (sample, name)
    if key not in _cache:
        p = os.path.join(SAMPLES, sample, name)
        _cache[key] = norm(open(p, encoding='utf-8').read()) if os.path.exists(p) else None
    return _cache[key]


def in_answers(sample, text):
    t = norm(text)
    if not t:
        return False
    for name in ('essay.txt', 'q12.txt'):
        body = load(sample, name)
        if body and t in body:
            return True
    return False


errors, thin = [], []
count = {'nodes': 0, 'examples': 0, 'usages': 0}


def walk(node, path):
    count['nodes'] += 1
    here = f"{path} / {node.get('id', '?')} {node.get('title', '')}"
    exs = node.get('examples', []) or []
    uss = node.get('usages', []) or []
    count['examples'] += len(exs)
    count['usages'] += len(uss)
    want = node.get('min_examples')
    if want and len(exs) + len(uss) < want:
        thin.append((here, len(exs) + len(uss), want))
    for i, ex in enumerate(exs, 1):
        tag = f"{here} · 例{i}"
        sample = ex.get('sample')
        if not sample or not os.path.isdir(os.path.join(SAMPLES, sample)):
            errors.append(f"{tag}：样本 {sample!r} 不存在")
            continue
        mat = load(sample, 'material.txt')
        for s in ex.get('source', []) or []:
            txt = norm(s.get('text', ''))
            if not txt:
                errors.append(f"{tag}：source.text 为空")
                continue
            if s.get('from') == 'essay':
                if not in_answers(sample, s['text']):
                    errors.append(f"{tag}：标为来自定稿的原文在定稿里找不到：{s['text'][:40]}")
            elif mat is None or txt not in mat:
                errors.append(f"{tag}：材料里找不到这段原文：{s['text'][:40]}")
            for k in s.get('kept', []) or []:
                if norm(k) not in txt:
                    errors.append(f"{tag}：kept 片段不在原文里：{k}")
        for j, part in enumerate(ex.get('parts', []) or [], 1):
            if not in_answers(sample, part.get('text', '')):
                errors.append(f"{tag}：第 {j} 截不在定稿里：{part.get('text', '')[:40]}")
            for s2 in part.get('source', []) or []:
                t2 = norm(s2.get('text', ''))
                if mat is None or t2 not in mat:
                    errors.append(f"{tag}：第 {j} 截的材料原文找不到：{s2.get('text', '')[:40]}")
                for k in s2.get('kept', []) or []:
                    if norm(k) not in t2:
                        errors.append(f"{tag}：第 {j} 截的 kept 片段不在原文里：{k}")
        prod = ex.get('product')
        if prod and not ex.get('product_is_mine') and not in_answers(sample, prod):
            errors.append(f"{tag}：成品不在该样本的定稿或小题答案里：{prod[:40]}")
    for i, u in enumerate(uss, 1):
        tag = f"{here} · 用法{i}"
        sample, sent, focus = u.get('sample'), u.get('sentence', ''), u.get('focus', '')
        if not sample or not in_answers(sample, sent):
            errors.append(f"{tag}：句子不在 {sample} 的定稿或小题答案里：{sent[:40]}")
        if focus and norm(focus) not in norm(sent):
            errors.append(f"{tag}：句子里没有要看的词「{focus}」")
    for ch in node.get('children', []) or []:
        walk(ch, here)


files = []
for a in sys.argv[1:]:
    files.extend(glob.glob(a))
if not files:
    print(__doc__)
    sys.exit(2)
for f in sorted(files):
    doc = json.load(open(f, encoding='utf-8'))
    for node in doc.get('nodes', []):
        walk(node, f"{doc.get('part', '?')}")

print(f"节点 {count['nodes']} 个，例子 {count['examples']} 条，词的用法 {count['usages']} 条。")
if thin:
    print(f"\n[偏少] 例子数低于设定下限的节点 {len(thin)} 个：")
    for here, have, want in thin:
        print(f"  - {here}：现有 {have}，下限 {want}")
if errors:
    print(f"\n[不通过] {len(errors)} 处：")
    for e in errors:
        print("  - " + e)
    sys.exit(1)
print("\n[通过] 所有原文、成品、用法都能在材料或定稿里原样找到。")
