#!/usr/bin/env python3
"""查交付文件：python3 check_q.py <set_id> [Q1 Q2 ...]

逐题查 <set_id>/Qn.md：
  1. 节齐不齐（# 题目行、## 答案、## 考场上的思路、## 逐条解析、## 压缩与成本）；
  2. 「## 答案」和 答案/Qn.txt 一字不差，含标点字数不超上限；
  3. 每个要点有「现实里是一件什么事」「为什么归成这一条」；
  4. 每个「来源：」里用「」引的原句都能在全卷材料里找到（去空白、归一引号后比，删节号两边分开找）；
  5. 答案里的每个分句（按，；。切）在解析的 #### 块里出现过；
  6. 考场思路和解析里没有「真人卷」「上一版」「机构」「账本」「定稿」这类过程词；没有 HTML 标签。
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, split_blocks, question, QN, norm

PROC = re.compile(r'真人卷|上一版|机构答案|机构参考|账本|定稿|[GXT]-\S{1,4}-?\d\d|高分卷|对齐\.json|必答点')


def body_of(t, head):
    m = re.search(r'(?m)^## %s\s*\n(.*?)(?=^## |\Z)' % re.escape(head), t, re.S)
    return m.group(1).strip() if m else None


def check(sid, qn):
    path = os.path.join(BASE, sid, qn + '.md')
    out = []
    if not os.path.exists(path):
        return ['缺文件 %s' % path]
    t = open(path, encoding='utf-8').read()
    qo = question(sid, QN[qn])
    limit = qo['limit']
    if sid == '2024选调' and qn == 'Q2':
        limit = 350
    if not re.match(r'^# ', t):
        out.append('第一行不是「# 题目」')
    for h in ('答案', '考场上的思路', '逐条解析', '压缩与成本'):
        if body_of(t, h) is None:
            out.append('缺节 ## %s' % h)
    ans = body_of(t, '答案') or ''
    txtp = os.path.join(BASE, sid, '答案', qn + '.txt')
    if os.path.exists(txtp):
        txt = open(txtp, encoding='utf-8').read().strip()
        if re.sub(r'\s', '', txt) != re.sub(r'\s', '', ans):
            out.append('答案和 答案/%s.txt 不一致' % qn)
    else:
        out.append('缺 答案/%s.txt' % qn)
    n = len(re.sub(r'\s', '', ans))
    if limit and n > limit:
        out.append('超字：%d / %d' % (n, limit))
    parse = body_of(t, '逐条解析') or ''
    points = re.split(r'(?m)^### ', parse)[1:]
    if not points:
        out.append('逐条解析里没有 ### 要点')
    for p in points:
        name = p.split('\n', 1)[0].strip()
        if '现实里是一件什么事' not in p:
            out.append('要点「%s」缺「现实里是一件什么事」' % name[:20])
        if '为什么归成这一条' not in p:
            out.append('要点「%s」缺「为什么归成这一条」' % name[:20])
    mat = norm(''.join(''.join(ps) for _, ps in split_blocks(sid)))
    bad_q = 0
    for line in re.findall(r'(?m)^- 来源[：:](.*)$', parse):
        for qt in re.findall(r'「([^」]{4,})」', line):
            for piece in re.split(r'……|…|\.\.\.', qt):
                pc = norm(piece)
                if len(pc) >= 4 and pc not in mat:
                    bad_q += 1
                    out.append('来源引文在材料里找不到：「%s」' % piece[:30])
    heads = ' '.join(re.findall(r'(?m)^###?#? (.*)$', parse))
    hn = norm(heads)
    for c in re.split(r'[，；。：\n]', re.sub(r'^[一二三四五六七八九十\d]+[、.．]', '', ans, flags=re.M)):
        cn = norm(re.sub(r'^(问题|对策|建议|对策建议|存在问题)', '', c.strip()))
        if len(cn) >= 6 and cn[:6] not in hn:
            out.append('答案分句没有自己的 #### 块：「%s」' % c.strip()[:24])
    think = body_of(t, '考场上的思路') or ''
    for sec, s in (('考场上的思路', think), ('逐条解析', parse)):
        m = PROC.findall(s)
        if m:
            out.append('%s 里有过程词：%s' % (sec, '、'.join(sorted(set(m))[:5])))
    if re.search(r'<[a-zA-Z/][^>]*>', t):
        out.append('有 HTML 标签')
    return out


if __name__ == '__main__':
    sid = sys.argv[1]
    qs = sys.argv[2:] or sorted(f[:-3] for f in os.listdir(os.path.join(BASE, sid)) if re.match(r'^Q\d\.md$', f))
    total = 0
    for qn in qs:
        r = check(sid, qn)
        total += len(r)
        print('%s %s：%s' % (sid, qn, '通过' if not r else '%d 处' % len(r)))
        for x in r:
            print('   - ' + x)
    sys.exit(1 if total else 0)
