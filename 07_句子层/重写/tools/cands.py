#!/usr/bin/env python3
"""候选：python3 cands.py <样本id> <参数json>
参数json: {"paras":[{"name":..,"blocks":["三","四"]|"all","topic":"正则"}], "role":"正则(可省)"}"""
import re,sys,json,os
sid,pf=sys.argv[1],sys.argv[2]
pool=json.load(open(os.path.join(os.path.dirname(__file__),'..','_pool',sid+'.json'),encoding='utf-8'))
P=json.load(open(pf,encoding='utf-8'))
ROLE=P.get('role') or r'(底色|根基|基础|支撑|动力|引擎|保障|命脉|竞争力|源泉|屏障|未来|风尚|新风|期盼|增长点|治本之策|牛鼻子|抓手|底盘|新活力|基因|本钱|优势|招牌|沃土|脊梁|画卷|答卷|通道|纽带|样板|缩影|前提|财富|家园|活化石|见证者|途径|载体|阵地|平台|成色|生机|获得感|必答题|绿色银行)'
for cfg in P['paras']:
    blocks=[b for b in '一二三四五六七八九十' if b in pool] if cfg['blocks']=='all' else cfg['blocks']
    print("\n"+"="*26+" %s ｜ 材料:%s "%(cfg['name'],''.join(blocks))+"="*26)
    sents=[(b,i+1,s) for b in blocks for i,s in enumerate(pool[b])]
    print("[R1 …的X（角色名词）]")
    for b,i,s in sents:
        for m in list(re.finditer(r'的'+ROLE, s))+list(re.finditer(r'(?:是|成为|也是|就是)[^，。；]{0,10}?'+ROLE, s)):
            tag=' (首句)' if i==1 else (' (末句)' if i==len(pool[b]) else '')
            print("  %s-%02d%s %s ← %s"%(b,i,tag,m.group(1),s[max(0,m.start()-14):m.end()+2]))
    print("[R2 判断句，主语含主题词]")
    for b,i,s in sents:
        s2=re.sub(r'^[^，。]{0,14}(证明|表明|指出|强调|说)[，：]', '', s)
        m=re.search(r'(是|就是|成为|已成为|离不开|促|决定)', s2)
        if not m: continue
        subj=s2[:m.start()]
        if 2<=len(subj)<=30 and re.search(cfg['topic'], subj):
            print("  %s-%02d [%d字] %s %s"%(b,i,len(s),s[:58],'★' if re.search(ROLE,s[m.end():]) else ''))
    print("[R3 总括句（广东/近年来/随着/…以来 开头）]")
    for b,i,s in sents:
        if re.match(r'(近年来|广东|在广东|随着|\d{4}年以来|党的|全省)', s) and re.search(cfg['topic'],s): print("  %s-%02d %s"%(b,i,s[:60]))
    print("[R4 各则末句 ＋ 含才/才能/就能 的句]")
    for b in blocks:
        s=pool[b][-1]
        if re.search(cfg['topic'],s) or cfg['blocks']!='all': print("  %s-%02d(末句) %s"%(b,len(pool[b]),s[:60]))
    for b,i,s in sents:
        if re.search(r'才能|才有|就能|才是', s) and i!=len(pool[b]) and re.search(cfg['topic'],s): print("  %s-%02d %s"%(b,i,s[:60]))
