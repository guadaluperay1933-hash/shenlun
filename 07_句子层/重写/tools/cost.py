#!/usr/bin/env python3
"""计分：python3 cost.py <样本id> <正文.txt> [更多正文...]  自造字＝去标点后贴不回材料的字，单个胶水字不计"""
import sys,re,unicodedata,os
def load_essay(path):
    """正文文件：.txt 整读；.md 只取「## 一、作文」到下一个「## 」之间"""
    t=open(path,encoding='utf-8').read()
    if path.endswith('.md'):
        k=t.find('## 一、作文')
        if k>=0:
            t=t[k:].split('\n',1)[1]
            j=t.find('\n## ')
            t=t[:j] if j>=0 else t
    return t
def norm(t):
    t=unicodedata.normalize('NFKC',t)
    return re.sub(r'[\s“”"‘’\'《》〈〉【】（）()、，。；：！？—…·,.;:!?\-—]','',t)
GLUE=set('的是了在以让把才就要为和与不也更而从到于之中上下等都还并将被向对使能有着这那其')
def cover(e,m,MIN):
    n=len(e);i=0;unc=[]
    while i<n:
        best=0
        for L in range(min(24,n-i),MIN-1,-1):
            if e[i:i+L] in m: best=L;break
        if best: i+=best
        else: unc.append((i,e[i]));i+=1
    runs=[];cur='';last=-2
    for pos,ch in unc:
        if pos==last+1: cur+=ch
        else:
            if cur: runs.append(cur)
            cur=ch
        last=pos
    if cur: runs.append(cur)
    sm=[r for r in runs if not(len(r)==1 and r in GLUE)]
    return n,sum(len(r) for r in sm),sm
sid=sys.argv[1]
root=os.path.join(os.path.dirname(__file__),'..','..')
m=norm(open(os.path.join(root,'samples',sid,'material.txt'),encoding='utf-8').read())
for path in sys.argv[2:]:
    txt=load_essay(path)
    paras=[p for p in txt.split('\n') if p.strip()]
    print("\n===== %s ====="%os.path.basename(path))
    print("段落字数(去标点):",[len(norm(p)) for p in paras],"合计",len(norm(txt)),"｜含标点",len(re.sub(r'\s','',txt)))
    for MIN in (2,3):
        n,s,runs=cover(norm(txt),m,MIN)
        print("  MIN=%d → 自造 %d 字 (%.1f%%)"%(MIN,s,100*s/n),("  片段:"+str([r for r in runs if len(r)>=2])) if MIN==2 else '')
