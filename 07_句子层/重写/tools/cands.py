#!/usr/bin/env python3
"""候选：python3 cands.py <样本id> <参数json>
参数json: {"paras":[{"name":..,"blocks":["三","四"]|"all","topic":"正则"}], "role":"正则(可省)"}"""
import re,sys,json,os
sid,pf=sys.argv[1],sys.argv[2]
pool=json.load(open(os.path.join(os.path.dirname(__file__),'..','_pool',sid+'.json'),encoding='utf-8'))
P=json.load(open(pf,encoding='utf-8'))
# R8 窗口：每则首段＋末段；首段或末段只有一句时连上相邻一段
try: PI=json.load(open(os.path.join(os.path.dirname(__file__),'..','_pool',sid+'.paras.json'),encoding='utf-8'))
except FileNotFoundError: PI={b:[0]*len(pool[b]) for b in pool}
WIN={}
for b in pool:
    pi=PI[b];first={0};last={pi[-1]}
    if pi.count(0)==1 and pi[-1]>0: first.add(1)
    if pi.count(pi[-1])==1 and pi[-1]>0: last.add(pi[-1]-1)
    WIN[b]={i+1:('首段' if pi[i] in first else '末段') for i in range(len(pi)) if pi[i] in first or pi[i] in last}
def tag(b,i): return ' ('+WIN[b][i]+')' if i in WIN.get(b,{}) else ''
if P.get('window',True):
    print("[R8 窗口：各则首段＋末段（非例证句只从这里取；材料一整则读）]")
    for b in pool:
        for i in sorted(WIN[b]): print("  %s-%02d(%s) %s"%(b,i,WIN[b][i],pool[b][i-1][:64]))
    # R1b：窗口句里的动宾尾——有串分支的标签后半「为B＋动宾」直接从这里挑 X
    VERB=r'(带来|增添|拓展|构建|提供|注入|厚植|打造|培育|激发|筑牢|夯实|营造|形成|增强|提升|守护|留下|铺展|壮大|拓宽|激活|释放|迸发|催生)'
    print("[R1b 窗口句的动宾尾（标签 X 候选）]")
    for b in pool:
        for i in sorted(WIN[b]):
            s=pool[b][i-1]
            for m in re.finditer(VERB+r'(?:了|着|出|成)?(?:一股强大的|一批|一道|一系列)?([^，。；：、]{2,16})(?=[，。；：、”]|$)', s):
                print("  %s-%02d(%s) %s%s"%(b,i,WIN[b][i],m.group(1),m.group(2).strip('“”')))
ROLE=P.get('role') or r'(底色|根基|基础|支撑|动力|引擎|保障|命脉|竞争力|源泉|屏障|未来|风尚|新风|期盼|增长点|治本之策|牛鼻子|抓手|底盘|新活力|基因|本钱|优势|招牌|沃土|脊梁|画卷|答卷|通道|纽带|样板|缩影|前提|财富|家园|活化石|见证者|途径|载体|阵地|平台|成色|生机|获得感|必答题|绿色银行)'
for cfg in P['paras']:
    blocks=[b for b in '一二三四五六七八九十' if b in pool] if cfg['blocks']=='all' else cfg['blocks']
    print("\n"+"="*26+" %s ｜ 材料:%s "%(cfg['name'],''.join(blocks))+"="*26)
    sents=[(b,i+1,s) for b in blocks for i,s in enumerate(pool[b])]
    print("[R1 …的X（角色名词）]")
    for b,i,s in sents:
        for m in list(re.finditer(r'的'+ROLE, s))+list(re.finditer(r'(?:是|成为|也是|就是)[^，。；]{0,10}?'+ROLE, s)):
            print("  %s-%02d%s %s ← %s"%(b,i,tag(b,i),m.group(1),s[max(0,m.start()-14):m.end()+2]))
    print("[R2 判断句，主语含主题词]")
    for b,i,s in sents:
        s2=re.sub(r'^[^，。]{0,14}(证明|表明|指出|强调|说)[，：]', '', s)
        m=re.search(r'(是|就是|成为|已成为|离不开|促|决定)', s2)
        if not m: continue
        subj=s2[:m.start()]
        if 2<=len(subj)<=30 and re.search(cfg['topic'], subj):
            print("  %s-%02d%s [%d字] %s %s"%(b,i,tag(b,i),len(s),s[:58],'★' if re.search(ROLE,s[m.end():]) else ''))
    print("[R3 总括句（广东/近年来/随着/…以来/xxxx年，广东 开头；只看句首，不限窗口）]")
    for b,i,s in sents:
        if re.match(r'(近年来|广东|在广东|随着|\d{4}年以来|\d{4}年，广东|党的|全省)', s) and re.search(cfg['topic'],s): print("  %s-%02d%s %s"%(b,i,tag(b,i),s[:60]))
    print("[R4 各则末句 ＋ 含才/才能/就能 的句]")
    for b in blocks:
        s=pool[b][-1]
        if re.search(cfg['topic'],s) or cfg['blocks']!='all': print("  %s-%02d(末句) %s"%(b,len(pool[b]),s[:60]))
    for b,i,s in sents:
        if re.search(r'才能|才有|就能|才是', s) and i!=len(pool[b]) and re.search(cfg['topic'],s): print("  %s-%02d%s %s"%(b,i,tag(b,i),s[:60]))
