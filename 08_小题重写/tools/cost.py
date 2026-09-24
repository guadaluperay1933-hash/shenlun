#!/usr/bin/env python3
"""小题成本尺：python3 cost.py <set_id> <答案.txt> [--q 问题一]

题号从 --q 或文件名里的 Q1..Q5 取，指定则从 questions.json 取。报：
  含标点字数 / 上限；自造字（对指定则，MIN=2）；自造字（对整卷）；
  借词（指定则里没有、整卷别处有的片段）；缩写候选（像「律所←律师事务所」）；动词壳（建、促、搭建之类单列）。
行首序号、「一是」「问题：」「建议：」这类结构字单独计，不算自造。
"""
import sys, os, re, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import split_blocks, question, norm, QN

GLUE = set('的是了在以让把才就要为和与不也更而从到于之中上下等都还并将被向对使能有着这那其及')
SHELL = ['搭建', '引进', '推进', '推动', '加强', '建立', '健全', '完善', '强化', '提升', '建', '抓', '促', '强', '优', '扩', '稳', '防', '放', '设', '办', '搞', '育', '引', '留', '补', '治', '管', '改', '减', '保', '增', '提', '推']
STRUCT = re.compile(r'(^|(?<=[。；：\n]))\s*(（?[一二三四五六七八九十\d]+[）、.．]|[①-⑩]|[一二三四五六七八九十]是|第[一二三四五六七八九十]，|存在问题[：:]|对策建议[：:]|问题[：:]|建议[：:]|对策[：:]|措施[：:]|做法[：:])')


def cover(e, m, MIN=2):
    """贪心最长覆盖，返回每个位置是否被覆盖。"""
    n = len(e); cov = [False] * n; i = 0
    while i < n:
        best = 0
        for L in range(min(24, n - i), MIN - 1, -1):
            if e[i:i + L] in m:
                best = L; break
        if best:
            for k in range(i, i + best):
                cov[k] = True
            i += best
        else:
            i += 1
    return cov


def runs(e, mask):
    out, cur = [], ''
    for ch, bad in zip(e, mask):
        if bad:
            cur += ch
        elif cur:
            out.append(cur); cur = ''
    if cur:
        out.append(cur)
    return out


def abbr(run, m):
    """run 的字按顺序出现在材料里一个不超过 3 倍长的片段里，且首尾字对得上。"""
    if len(run) < 2:
        return None
    pat = re.escape(run[0]) + ''.join('[^%s]{0,4}%s' % (re.escape(c), re.escape(c)) for c in run[1:])
    mm = re.search(pat, m)
    if mm and len(mm.group(0)) <= 3 * len(run) and mm.group(0) != run:
        return mm.group(0)
    return None


def analyse(sid, path, q):
    qo = question(sid, q)
    blocks = split_blocks(sid)
    whole = norm(''.join(''.join(ps) for _, ps in blocks))
    want = qo['blocks'] or [n for n, _ in blocks]
    desig = norm(''.join(''.join(ps) for n, ps in blocks if n in want))
    raw = open(path, encoding='utf-8').read().strip()
    lines = [l for l in raw.split('\n') if l.strip()]
    total_punct = len(re.sub(r'\s', '', raw))
    print('===== %s %s　%s　指定则：%s =====' % (sid, qo['q'], os.path.basename(path), '、'.join(want)))
    print('含标点 %d 字 / 上限 %s%s' % (total_punct, qo['limit'], '　⚠ 超字' if qo['limit'] and total_punct > qo['limit'] else ''))
    S = {'self_d': 0, 'self_w': 0, 'struct': 0, 'borrow': [], 'abbr': [], 'shell': [], 'selfruns': []}
    for l in lines:
        structs = [m.group(2) for m in STRUCT.finditer(l)]
        body = STRUCT.sub(lambda m: m.group(1), l)
        e = norm(body)
        cd = cover(e, desig); cw = cover(e, whole)
        sd = [r for r in runs(e, [not c for c in cd]) if not (len(r) == 1 and r in GLUE)]
        sw = [r for r in runs(e, [not c for c in cw]) if not (len(r) == 1 and r in GLUE)]
        borrow = runs(e, [cw[i] and not cd[i] for i in range(len(e))])
        borrow = [b for b in borrow if len(b) >= 2]
        shells, real, ab = [], [], []
        for r in sd:
            a = abbr(r, whole)
            if a:
                ab.append('%s←%s' % (r, a)); continue
            if r in SHELL:
                shells.append(r); continue
            real.append(r)
        n_struct = sum(len(norm(s)) for s in structs)
        S['struct'] += n_struct
        S['self_d'] += sum(len(r) for r in real)
        S['self_w'] += sum(len(r) for r in sw if not abbr(r, whole) and r not in SHELL)
        S['borrow'] += borrow; S['abbr'] += ab; S['shell'] += shells; S['selfruns'] += real
        print('\n  %s' % l.strip())
        tag = []
        if real: tag.append('自造 ' + '｜'.join(real))
        if borrow: tag.append('借词 ' + '｜'.join(borrow))
        if ab: tag.append('缩写 ' + '｜'.join(ab))
        if shells: tag.append('动词壳 ' + '｜'.join(shells))
        if n_struct: tag.append('结构字 %d' % n_struct)
        print('    → ' + ('；'.join(tag) if tag else '全部贴得回指定则'))
    print('\n合计：自造 %d 字（对指定则）｜对整卷 %d 字｜结构字 %d｜借词 %d 处｜缩写 %d 处｜动词壳 %d 处' %
          (S['self_d'], S['self_w'], S['struct'], len(S['borrow']), len(S['abbr']), len(S['shell'])))
    return S


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('sid'); ap.add_argument('path'); ap.add_argument('--q')
    a = ap.parse_args()
    q = a.q
    if not q:
        m = re.search(r'Q(\d)', os.path.basename(a.path))
        q = QN['Q' + m.group(1)] if m else '问题一'
    analyse(a.sid, a.path, q)
