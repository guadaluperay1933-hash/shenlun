#!/usr/bin/env python3
"""一句一源：python3 onesrc.py <样本id> <正文.txt>  按。？！切句、按；：切分句，列每分句来源；⚠=跨块或同块不相邻（材料自重复要人工剔）"""
import json,re,sys,unicodedata,os
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
    t=unicodedata.normalize('NFKC',t); return re.sub(r'[\s“”"‘’\'《》【】（）()、，。；：！？—…·,.;:!?\-]','',t)
sid,path=sys.argv[1],sys.argv[2]
pool=json.load(open(os.path.join(os.path.dirname(__file__),'..','_pool',sid+'.json'),encoding='utf-8'))
P=[(b,i+1,norm(s)) for b in pool for i,s in enumerate(pool[b])]
txt=load_essay(path);bad=0
for pi,para in enumerate([p for p in txt.split('\n') if p.strip()]):
    print("\n--- 段%d ---"%pi)
    for s in [x for x in re.split(r'(?<=[。？！])',para) if x.strip()]:
        for c in [x for x in re.split(r'[；：]',s) if x.strip()]:
            nc=norm(c);hits=[]
            for b,i,ps in P:
                best=0;bsub=''
                for L in range(min(len(nc),22),5,-1):
                    for k in range(0,len(nc)-L+1):
                        if nc[k:k+L] in ps: best=L;bsub=nc[k:k+L];break
                    if best: break
                if best>=6:
                    # 套话：这段匹配文字在 >=3 句材料里都出现，不能定位来源，不计入⚠
                    boiler = sum(1 for _,_,q in P if bsub in q)>=3
                    hits.append((best if not boiler else 5,b,i))
            hits.sort(reverse=True)
            top=hits[0][0] if hits else 0
            strong=[(b,i) for l,b,i in hits if l>=8 and l>=0.6*top]
            blocks={b for b,i in strong};idx=sorted(i for b,i in strong)
            flag=''
            if len(blocks)>1: flag='  ⚠跨块';bad+=1
            elif len(idx)>1 and max(idx)-min(idx)>1: flag='  ⚠同块不相邻';bad+=1
            elif len(idx)>1: flag='  (相邻合并)'
            print("  %-32s ← %s%s"%(c[:32],' '.join("%s-%02d(%d)"%(b,i,l) for l,b,i in hits[:3]) or '（无≥6字匹配）',flag))
print("\n⚠ 数:",bad)
