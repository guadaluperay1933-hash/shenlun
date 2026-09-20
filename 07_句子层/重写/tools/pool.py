#!/usr/bin/env python3
"""句池：python3 pool.py <样本id>  → 打印编号句池并存 _pool/<样本id>.json（另存 .paras.json：每句所在自然段号，供 R8 窗口用）"""
import re,sys,json,os
sid=sys.argv[1]
root=os.path.join(os.path.dirname(__file__),'..','..')
mt=open(os.path.join(root,'samples',sid,'material.txt'),encoding='utf-8').read()
mt=re.split(r'\n\s*【?问题一】?\s*\n', mt)[0]
blocks=re.split(r'(?m)^\s*【?材料([一二三四五六七八九十]+)】?\s*$', mt)
pool={};paraidx={}
for i in range(1,len(blocks),2):
    name=blocks[i]; body=blocks[i+1]
    lines=[l.strip() for l in body.split('\n') if l.strip()]
    buf='';paras=[]
    for l in lines:
        buf+=l
        if re.search(r'[。！？”]$', l): paras.append(buf); buf=''
    if buf: paras.append(buf)
    sents=[];pidx=[]
    for k,ptxt in enumerate(paras):
        ss=[s.strip() for s in re.split(r'(?<=[。！？；])', ptxt) if len(re.sub(r'\s','',s))>=8]
        sents+=ss; pidx+=[k]*len(ss)
    pool[name]=sents; paraidx[name]=pidx
os.makedirs(os.path.join(os.path.dirname(__file__),'..','_pool'),exist_ok=True)
json.dump(pool,open(os.path.join(os.path.dirname(__file__),'..','_pool',sid+'.json'),'w',encoding='utf-8'),ensure_ascii=False)
json.dump(paraidx,open(os.path.join(os.path.dirname(__file__),'..','_pool',sid+'.paras.json'),'w',encoding='utf-8'),ensure_ascii=False)
n=0
for name in '一二三四五六七八九十':
    if name not in pool: continue
    print("\n######## 材料%s（%d 句）########"%(name,len(pool[name])))
    for j,s in enumerate(pool[name],1):
        n+=1; print("%s-%02d %s"%(name,j,s))
print("\n合计 %d 句"%n)
