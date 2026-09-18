#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核对 data/_frag/ 下的碎片文件。碎片的形状是 {"节点 id": [例子, ...]} 或
{"节点 id": {"examples": [...], "usages": [...]}}，和讲义数据文件不一样，
所以这里先包成数据文件的形状，再交给 verify_examples.py 查。

用法（仓库根目录运行）：
  python3 07_句子层/讲义工程/tools/verify_frag.py 07_句子层/讲义工程/data/_frag/2_转译__行1-2.json
  python3 07_句子层/讲义工程/tools/verify_frag.py "07_句子层/讲义工程/data/_frag/*.json"
"""
import glob, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

def wrap(path):
    frag = json.load(open(path, encoding='utf-8'))
    nodes = []
    for nid, payload in frag.items():
        if isinstance(payload, dict):
            exs = payload.get('examples', []) or []
            uss = payload.get('usages', []) or []
        else:
            exs, uss = payload, []
        nodes.append({'id': nid, 'title': '', 'min_examples': 0,
                      'one_line': '', 'plain': [], 'examples': exs, 'usages': uss})
    return {'part': os.path.basename(path), 'title': '碎片', 'intro': '', 'nodes': nodes}

def main():
    args = []
    for a in sys.argv[1:]:
        args.extend(glob.glob(a))
    if not args:
        print(__doc__); sys.exit(2)
    tmpdir = tempfile.mkdtemp(prefix='frag_')
    made = []
    for p in sorted(args):
        doc = wrap(p)
        t = os.path.join(tmpdir, os.path.basename(p))
        json.dump(doc, open(t, 'w', encoding='utf-8'), ensure_ascii=False)
        made.append(t)
        n = sum(len(x['examples']) + len(x['usages']) for x in doc['nodes'])
        print(f'{os.path.basename(p)}：节点 {len(doc["nodes"])} 个，例子和用法合计 {n} 条')
    print()
    r = subprocess.run([sys.executable, os.path.join(HERE, 'verify_examples.py')] + made)
    sys.exit(r.returncode)

if __name__ == '__main__':
    main()
