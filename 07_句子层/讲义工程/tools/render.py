#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 data/*.json 渲染成两种离线格式，都可以逐级展开、收起：
  out/<部分>.md    标题加层层缩进的列表。Obsidian、VS Code、Logseq 里标题和列表项都能折叠。
  out/<部分>.opml  大纲文件。幕布、XMind、MindNode、OmniOutliner 都能导入，一层一层点开。
不产生任何 HTML 标签。

整段的例子（开头、结尾、一个完整中间段）用 parts 把定稿按拍子切开，每一截下面再挂它的材料出处。

每条例子的层次：
  例子标题（标签、出处、看点）
    原文（材料原句，留下来的字加粗）
    成品（定稿里的句子）
      动了什么
      为什么选它
所以收起来时只看到原文，可以先自己动手改，再点开看成品，当练习用。

用法（在仓库根目录运行）：python 07_句子层/讲义工程/tools/render.py
"""
import json, glob, os, re
from xml.sax.saxutils import quoteattr, escape

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
OUT = os.path.join(HERE, '..', 'out')
os.makedirs(OUT, exist_ok=True)
TAG_ORDER = {'典型': 0, '变体': 1, '难点': 2, '反例': 3}


def bold_kept(text, kept):
    spans = []
    for k in kept or []:
        i = text.find(k)
        if i >= 0:
            spans.append((i, i + len(k)))
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    out, last = [], 0
    for s, e in merged:
        out.append(text[last:s])
        out.append('**' + text[s:e] + '**')
        last = e
    out.append(text[last:])
    return ''.join(out)


def example_tree(ex, idx):
    head = f"例{idx}【{ex.get('tag', '典型')}】{ex.get('sample', '')}·{ex.get('where', '')}｜{ex.get('title', '')}"
    kids = []
    for s in ex.get('source', []) or []:
        label = '定稿原句' if s.get('from') == 'essay' else f"原文（材料{s.get('material', '')}）"
        kids.append((f"{label}：{bold_kept(s.get('text', ''), s.get('kept'))}", []))
    for part in ex.get('parts', []) or []:
        pk = []
        for s2 in part.get('source', []) or []:
            pk.append((f"出自材料{s2.get('material', '')}：{bold_kept(s2.get('text', ''), s2.get('kept'))}", []))
        if part.get('note'):
            pk.append((part['note'], []))
        kids.append((f"{part.get('label', '')}：{part.get('text', '')}", pk))
    sub = []
    if ex.get('steps'):
        sub.append((f"动了什么：{ex['steps']}", []))
    if ex.get('why'):
        sub.append((f"为什么选它：{ex['why']}", []))
    if ex.get('product'):
        label = '示范（定稿里没有，照规则写的）' if ex.get('product_is_mine') else '成品'
        kids.append((f"{label}：{ex['product']}", sub))
    else:
        kids.extend(sub)
    return (head, kids)


def usage_tree(u, idx):
    sent, f = u.get('sentence', ''), u.get('focus', '')
    if f and f in sent:
        sent = sent.replace(f, '**' + f + '**', 1)
    kids = [(u['note'], [])] if u.get('note') else []
    return (f"用法{idx}｜{u.get('sample', '')}·{u.get('where', '')}：{sent}", kids)


def node_tree(node):
    kids = []
    if node.get('one_line'):
        kids.append((f"一句话：{node['one_line']}", []))
    if node.get('plain'):
        kids.append(("讲开了说", [(p, []) for p in node['plain']]))
    exs = sorted(node.get('examples', []) or [], key=lambda e: TAG_ORDER.get(e.get('tag', '典型'), 9))
    if exs:
        kids.append((f"例子（{len(exs)} 条，按优先级排）", [example_tree(e, i) for i, e in enumerate(exs, 1)]))
    us = node.get('usages', []) or []
    if us:
        kids.append((f"定稿里是怎么用的（{len(us)} 处）", [usage_tree(u, i) for i, u in enumerate(us, 1)]))
    for ch in node.get('children', []) or []:
        kids.append(node_tree(ch))
    return (f"{node.get('id', '')} {node.get('title', '')}".strip(), kids)


def bullets(tree, indent, lines):
    text, kids = tree
    lines.append('  ' * indent + '- ' + text)
    for k in kids:
        bullets(k, indent + 1, lines)


def node_md(node, depth, lines):
    """理论节点用标题（最多到六级），节点里面的一句话、讲解是正文，例子和用法是可折叠的缩进列表。"""
    level = min(depth + 1, 6)
    lines.append('\n' + '#' * level + ' ' + f"{node.get('id', '')} {node.get('title', '')}".strip() + '\n')
    if node.get('one_line'):
        lines.append('**一句话**：' + node['one_line'] + '\n')
    for p in node.get('plain', []) or []:
        lines.append(p + '\n')
    exs = sorted(node.get('examples', []) or [], key=lambda e: TAG_ORDER.get(e.get('tag', '典型'), 9))
    if exs:
        lines.append(f"**例子（{len(exs)} 条，按优先级排；先只看原文自己改，再展开看成品）**\n")
        for i, e in enumerate(exs, 1):
            bullets(example_tree(e, i), 0, lines)
        lines.append('')
    us = node.get('usages', []) or []
    if us:
        lines.append(f"**定稿里是怎么用的（{len(us)} 处）**\n")
        for i, u in enumerate(us, 1):
            bullets(usage_tree(u, i), 0, lines)
        lines.append('')
    for ch in node.get('children', []) or []:
        node_md(ch, depth + 1, lines)


def to_opml(tree, depth, lines):
    text, kids = tree
    plain = re.sub(r'\*\*(.+?)\*\*', r'【\1】', text)  # 大纲软件不认粗体，留下来的字改用【】标出
    if kids:
        lines.append('  ' * depth + f'<outline text={quoteattr(plain)}>')
        for k in kids:
            to_opml(k, depth + 1, lines)
        lines.append('  ' * depth + '</outline>')
    else:
        lines.append('  ' * depth + f'<outline text={quoteattr(plain)}/>')


for f in sorted(glob.glob(os.path.join(DATA, '*.json'))):
    doc = json.load(open(f, encoding='utf-8'))
    name = os.path.splitext(os.path.basename(f))[0]
    title = f"{doc.get('part', '')}、{doc.get('title', '')}"
    trees = [node_tree(n) for n in doc.get('nodes', [])]
    md = ['# ' + title]
    if doc.get('intro'):
        md.append('\n' + doc['intro'] + '\n')
    for n in doc.get('nodes', []):
        node_md(n, 1, md)
    open(os.path.join(OUT, name + '.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    op = ['<?xml version="1.0" encoding="UTF-8"?>', '<opml version="2.0">',
          f'<head><title>{escape(title)}</title></head>', '<body>', f'  <outline text={quoteattr(title)}>']
    for t in trees:
        to_opml(t, 2, op)
    op += ['  </outline>', '</body>', '</opml>']
    open(os.path.join(OUT, name + '.opml'), 'w', encoding='utf-8').write('\n'.join(op) + '\n')
    print('已生成', name + '.md', '和', name + '.opml')
