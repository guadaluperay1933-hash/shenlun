#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 07_句子层/out/汇总.md。表由 out/ 下的 card.json / clauses.jsonl / q12.jsonl 算出，
结论写在本文件里。改了标注重跑一次即可：

    python 07_句子层/tools/make_summary.py
"""
import json, glob, os, re, sys, unicodedata
from collections import Counter, defaultdict

import re
from collections import Counter, defaultdict
OUT='07_句子层/out'
IDS=['2020县级','2021县级','2022县级','2023县级','2024一卷','2024二卷',
     '2024选调','2025县镇','2025省市','2025选调','2026县镇','2026省市']
CASES=[f'C{i}' for i in range(1,13)]+['F','Z','W','O']
QC='“”‘’"\'「」『』《》〈〉'
def norm(s):
    s=unicodedata.normalize('NFKC',s or ''); s=re.sub(r'\s+','',s)
    for ch in QC: s=s.replace(ch,'')
    return s
def mc(c): return str(c or '').split('+')[0].strip()
def jl(p): return [json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]

cards={i:json.load(open(f'{OUT}/{i}/card.json',encoding='utf-8')) for i in IDS}
cl={i:jl(f'{OUT}/{i}/clauses.jsonl') for i in IDS}
q1={i:jl(f'{OUT}/{i}/q12.jsonl') for i in IDS}
genre={i:cards[i]['genre'] for i in IDS}

D={}
# --- 覆盖率
rows=[]; tot=Counter(); byg=defaultdict(Counter)
for i in IDS:
    c=Counter(mc(r['case']) for r in cl[i]); tot+=c; byg[genre[i]]+=c
    n=len(cl[i]); cov=sum(v for k,v in c.items() if k.startswith('C') or k=='F')
    ch=sum(len(norm(r['text'])) for r in cl[i])
    z=sum(len(norm(r.get('self_made_part') or (r['text'] if mc(r['case'])=='Z' else ''))) for r in cl[i])
    w=sum(len(norm(r['text'])) for r in cl[i] if mc(r['case'])=='W')
    rows.append((i,genre[i],n,cov,ch,z,w,c))
D['cov_rows']=rows; D['cov_tot']=tot; D['cov_byg']=byg
D['n_all']=sum(r[2] for r in rows); D['cov_all']=sum(r[3] for r in rows)
D['ch_all']=sum(r[4] for r in rows); D['z_all']=sum(r[5] for r in rows); D['w_all']=sum(r[6] for r in rows)
# --- slot x case
sc=defaultdict(Counter); slot=Counter()
for i in IDS:
    for r in cl[i]:
        slot[r['slot']]+=1; sc[r['slot']][mc(r['case'])]+=1
D['slot']=slot; D['sc']=sc
# --- 小题
qt=Counter(); qrows=[]
for i in IDS:
    c=Counter()
    for r in q1[i]:
        for b in r.get('body') or []: c[mc(b.get('case'))]+=1
    qt+=c; qrows.append((i,sum(c.values()),c))
D['q_rows']=qrows; D['q_tot']=qt
D['qn']=sum(r[1] for r in qrows)
D['qcov']=sum(v for k,v in qt.items() if k.startswith('C') or k=='F')
ls=Counter(); lf=Counter()
for i in IDS:
    for r in q1[i]:
        ls[r.get('label_source') or '（无标签）']+=1
        lf[r.get('label_form') or '（无标签）']+=1
D['ls']=ls; D['lf']=lf
# 对策题里的 C11/C12：只看确有对策部分的卷子
DUICE=['2024一卷','2024二卷','2024选调','2025县镇','2025省市','2025选调','2026县镇','2026省市']
dc=Counter()
for i in DUICE:
    for r in q1[i]:
        for b in r.get('body') or []: dc[mc(b.get('case'))]+=1
D['duice']=dc; D['duice_n']=sum(dc.values()); D['duice_ids']=DUICE
# --- glue
g=Counter()
for i in IDS:
    for r in cl[i]:
        for t in re.split(r'[、,，/／\s]+', str(r.get('glue') or '')):
            if t.strip(): g[t.strip()]+=1
    for r in q1[i]:
        for b in r.get('body') or []:
            for t in re.split(r'[、,，/／\s]+', str(b.get('glue') or '')):
                if t.strip(): g[t.strip()]+=1
D['glue']=g
# --- 自造归七处
SEVEN={'标题':'①标题','家底':'②开头','靶子':'②开头','预告':'②开头','解题':'②开头','引语':'②开头',
 '观点':'③观点句后半句','道理':'④道理句','证据':'⑤证据句的连接词和转换动词','总括':'⑤证据句的连接词和转换动词',
 '数据':'⑤证据句的连接词和转换动词','收束':'⑥收束句句框','意象':'⑦结尾','点名':'⑦结尾','落点':'⑦结尾'}
zc=Counter(); zch=Counter(); zitems=defaultdict(list)
for i in IDS:
    for r in cl[i]:
        t=r.get('self_made_part') or (r['text'] if mc(r['case'])=='Z' else '')
        if not t: continue
        k=SEVEN.get(r['slot'],'⑧七处之外')
        zc[k]+=1; zch[k]+=len(norm(t)); zitems[k].append((i,t))
D['zc']=zc; D['zch']=zch; D['zitems']=zitems
D['z_n']=sum(zc.values()); D['z_c']=sum(zch.values())
# --- O 类
D['O']=[(i,r['slot'],r['text'],r.get('note','')) for i in IDS for r in cl[i] if mc(r['case'])=='O']
D['W']=[(i,r['slot'],r['text']) for i in IDS for r in cl[i] if mc(r['case'])=='W']



L=[]
def w(s=''): L.append(s)
pct=lambda a,b: f'{a/b:.0%}' if b else '—'
def canon(val, kinds):
    raw=re.split(r'[（(]', re.sub(r'\s+','',str(val or '')))[0]
    o=[]
    for p in re.split(r'[／/、]', raw):
        p=p.strip()
        if not p: continue
        o.append(next((c for c in kinds if p==c or p.startswith(c) or c.startswith(p)), f'其他:{p[:8]}'))
    return o or ['无']
def c1v(v,k): return canon(v,k)[0]
K_TITLE=['两个动宾','比喻式','四字＋以A打造B','其他']; K_LD=['近目标','上层目标']
K_SLOT=['引语','解题','家底','靶子','预告','其他']
K_TUI=['缺口','职责帽','形势','换阶段','自己的目标','重要性','其他']
K_SRC=['材料判断句','题干落点','材料里现成的一组标签','自造句框']
K_DAO=['抄','改','造','无']
K_SHOU=['补短板才能','正……','抄材料末句','比喻','让……','回到B','无']
K_YX=['抄材料','自造','无']; K_DM=['配角色词','不配词','无']

w('# 07_句子层 · 汇总')
w()
w(f"十二篇定稿大作文（`clauses.jsonl`，{D['n_all']} 条分句）＋十二套定稿小题（`q12.jsonl`，{D['qn']} 条分句），逐句对回给定材料。"
  '全部出处经 `tools/check_quotes.py` 核对通过；十二篇分句可逐字拼回定稿（无漏切、无重复）。'
  '样本只用定稿；真人卷合集与机构参考答案未读，`2024三卷行政执法` 未进入任何产出。')
w()
# ── 1
w('## 1. 校准结果')
w()
w('三个现成样本，做的时候不看 `gold/`，做完才比对。')
w()
w('| 样本 | 校准条数 | 来源对上 | 情况标对 |')
w('|---|---|---|---|')
w('| 2025省市 | 17 | 16（94%） | 14（82%） |')
w('| 2025选调 | 17 | 16（94%） | 15（88%） |')
w('| 2023县级 | 18 | 17（94%） | 17（94%） |')
w('| **合计** | **52** | **49（94%）** | **46（88%）** |')
w()
w('目标来源九成、情况八成，**两项都过线**，故按原做法跑完其余九篇。过线后把确实标错的五处改了')
w('（改完 51/52、51/52）；**上表是盲测数，不是订正后的数**。')
w()
w('**异议一条**：`海丝博览会成为与"一带一路"沿线合作的重要平台`，校准集 C5，我坚持 **C1**。')
w('`参考/申论改写手册_语法层.md` 动法 4「删修饰」表里逐字列着这条的原句→成品，属 0 档只删不写；')
w('材料原句本身就是评价句，成品只删了「已逐渐／广东／国家和地区／密切」，没有发生 C5 的「留名字＋半句评价」。')
w('**它暴露的是 C1 与 C5 的边界最弱**：同一段材料，取评价句尾是 C1、取整段叙述压缩是 C5。')
w('建议口径写死：**以定稿实际引用的那一句为准，不看它所在段落有多长。**')
w()
w('**一处是测量假象**：`工业增加值稳居全国第一` 被记成来源不对。校准集引 `位居全国第一，约占全国的八分之一`，')
w('我引 `工业增加值突破 4.5 万亿元，位居全国第一`——同一句材料的两个片段，重合 6 字、低于脚本 8 字阈值。')
w('按「是不是同一句材料」算，来源实为 50/52＝96%。')
w()
# ── 2
w('## 2. 覆盖率')
w()
w('| 样本 | 体裁 | 分句 | C1–C12+F | 占比 | 全文字 | 自造字 | 材料外字 |')
w('|---|---|---|---|---|---|---|---|')
for i,g,n,cov,ch,z,wc,c in D['cov_rows']:
    w(f'| {i} | {g} | {n} | {cov} | {pct(cov,n)} | {ch} | {z}（{pct(z,ch)}） | {wc} |')
w(f"| **合计** | | **{D['n_all']}** | **{D['cov_all']}** | **{pct(D['cov_all'],D['n_all'])}** | **{D['ch_all']}** | **{D['z_all']}（{pct(D['z_all'],D['ch_all'])}）** | **{D['w_all']}** |")
w()
ty=D['cov_byg']; s=sum(D['cov_tot'].values())
w('| case | ' + ' | '.join(k for k in CASES if D['cov_tot'].get(k,0)) + ' |')
w('|---|' + '---|'*len([k for k in CASES if D['cov_tot'].get(k,0)]))
w('| 全部 | ' + ' | '.join(str(D['cov_tot'][k]) for k in CASES if D['cov_tot'].get(k,0)) + ' |')
w('| 议论11篇 | ' + ' | '.join(str(ty['议论'].get(k,0)) for k in CASES if D['cov_tot'].get(k,0)) + ' |')
w('| 策论1篇 | ' + ' | '.join(str(ty['策论'].get(k,0)) for k in CASES if D['cov_tot'].get(k,0)) + ' |')
w()
w(f"策论只有一篇，列出只为看形状。可下的结论只有一条：策论 48 条里 C12 占 {ty['策论'].get('C12',0)} 条，")
w(f"十一篇议论合计才 {ty['议论'].get('C12',0)} 条——**C12 确是策论专用**。")
w()
w(f"**Z（自造）{D['z_all']} 字＝{pct(D['z_all'],D['ch_all'])}，合 {D['z_all']//12} 字/篇**，前期结论「每篇一百字上下、占全文一成」成立。")
w(f"**W（材料外）只有 {len(D['W'])} 条 {D['w_all']} 字**：`{D['W'][0][2]}`（{D['W'][0][0]}）。方法允许每篇补一句联系实际，十二篇只用掉一次。")
w()
w(f"**O 共 {len(D['O'])} 条＝{pct(len(D['O']),D['n_all'])}，这是本次拟合最重要的数：十二种情况不够用。**")
w('缺的不是零星几条，而是有规律的六族（下表条数经逐条归族核对，合计 45）：')
w()
w('| 族 | 机制 | 条数 | 代表 | 能否并进现有情况 |')
w('|---|---|---|---|---|')
w('| 甲 两处拼一句 | 不相邻的两处（常跨自然段或跨材料）各取半句，补一个动词粘起来 | 16 | 让制造强国梦后继有人；南沙引来香港科技大学（广州） | **能**，单开 C13，见第 8 节 |')
w('| 乙 只借材料一两个词、句框自造 | 含把一整段做法压成自拟的四到八字对仗口号 | 12 | 经验是：人文聚人心，绿色聚人气；以海洋文明涵养发展底气 | 不宜，**本质是自造，归 Z 更诚实** |')
w('| 丙 引语／设问／说话人改判断句 | 换主语、疑问改陈述、陈述改要求 | 6 | 长远看，它是留给子孙的"绿色银行" | **能**，把 C2 说明扩成「截半句／转述／改判断句」 |')
w('| 丁 判断句调序＋自造判断框 | 材料判断拆开重排，或只借一个词当主语 | 5 | 人往产业走，是乡村最朴素的规律 | **拆开**：纯调序并进 C1，自造框归 Z |')
w('| 戊 主客翻转／判断改使令 | 让 X 当 Y；动宾对调 | 3 | 让企业当创新主角 | 不宜，手册已判为低性价比写法（X7） |')
w('| 己 标题与结尾点名 | 本就是七处自造里的第一处和第七处 | 3 | 以绿美广东为笔　绘就……的画卷 | 不必，**属自造清单，不该用改法表描述** |')
w()
# ── 3
w('## 3. 哪几种情况最值得先学')
w()
rk=[]; acc=0
for n,(k,v) in enumerate(sorted(D['cov_tot'].items(), key=lambda x:-x[1]),1):
    acc+=v; rk.append((n,k,v,pct(v,s),pct(acc,s)))
w('| # | case | 条 | 占比 | 累计 |   | # | case | 条 | 占比 | 累计 |')
w('|---|---|---|---|---|---|---|---|---|---|---|')
hh=(len(rk)+1)//2
for n in range(hh):
    a='| %d | %s | %d | %s | %s |'%rk[n]
    b=(' | %d | %s | %d | %s | %s |'%rk[n+hh]) if n+hh<len(rk) else ' |  |  |  |  |  |'
    w(a+b)
w()
c4=sum(D['cov_tot'].get(k,0) for k in ('C1','F','C5','C10'))
w(f'**C1＋F＋C5＋C10 合计 {c4} 条＝{pct(c4,s)}，先学这四种就够一多半：**')
w('C1 照抄材料的判断句、首句、末句只删修饰；F 把材料的词填进「……才能……」「……就是要……」；')
w('C5 一段带细节的叙述只留项目名＋那半句评价；C10 五项留三、三项留两头、长名缩短。')
w('再往下 O（8%）不是改法而是缺口，C2 只服务开头和道理句，其余每种都在 3% 以下。')
w()
# ── 4
w('## 4. 槽位统计（来自十二张思路卡＋分句表）')
w()
w('体裁：议论 11 篇、策论 1 篇（2023县级）。**段数十二篇全是「开头＋四个中间段＋结尾」，一篇不差**，是唯一百分百固定的量。')
w()
w('### 4.1 每个 slot 用哪几种 case（最实用的一张）')
w()
w('| slot | 分句 | 头三种 case |   | slot | 分句 | 头三种 case |')
w('|---|---|---|---|---|---|---|')
sl=D['slot'].most_common(); h=(len(sl)+1)//2
for n in range(h):
    k,v=sl[n]; t3='、'.join(f'{a} {b}' for a,b in D['sc'][k].most_common(3))
    a=f'| {k} | {v} | {t3} |'
    if n+h<len(sl):
        k2,v2=sl[n+h]; t32='、'.join(f'{a2} {b2}' for a2,b2 in D['sc'][k2].most_common(3))
        b=f' | {k2} | {v2} | {t32} |'
    else: b=' |  |  |  |'
    w(a+b)
w()
gd=D['sc']['观点']; ev=D['sc']['证据']; ss=D['sc']['收束']; dl=D['sc']['道理']; yy=D['sc']['引语']
w(f"- **观点句 {D['slot']['观点']} 条里 F 占 {gd.get('F',0)}（{pct(gd.get('F',0),D['slot']['观点'])}）**——分论点靠句框，不靠抄。")
w(f"- **证据句 {D['slot']['证据']} 条最杂**，但 C5 {ev.get('C5',0)}／C1 {ev.get('C1',0)}／C10 {ev.get('C10',0)}／C8 {ev.get('C8',0)}／C3 {ev.get('C3',0)} 五种就够。")
w(f"- **收束句 F {ss.get('F',0)}＋C1 {ss.get('C1',0)}**——要么套句框，要么抄材料末句。")
w(f"- **道理句 C1 {dl.get('C1',0)}／Z {dl.get('Z',0)}／O {dl.get('O',0)}**——抄判断句是主路，**这里是全文自造最密的地方**。")
w(f"- **引语句 C2 {yy.get('C2',0)}/{D['slot']['引语']}**——C2 基本只服务这一个 slot。")
w()
# 4.2 汇总式
w('### 4.2 各 slot 的写法分布（每种出现在几篇里）')
w()
tf=Counter(c1v(cards[i]['标题'].get('形式'),K_TITLE) for i in IDS)
tl=Counter(c1v(cards[i]['标题'].get('落点'),K_LD) for i in IDS)
sc2=Counter(); tui=Counter()
for i in IDS:
    for x in {y for z in [canon(x.get('slot'),K_SLOT) for x in cards[i]['开头']['句子']] for y in z}: sc2[x]+=1
    for x in {c1v(x.get('类型'),K_TUI) for x in cards[i]['开头']['推法']}: tui[x]+=1
srcc=Counter()
for i in IDS:
    for p in cards[i]['段落']: srcc[c1v(p.get('观点句来源'),K_SRC)]+=1
dao=Counter(); shou=Counter(); AS=[];AE=[];AN=[];AL=[];AW=0
for i in IDS:
    for m in cards[i]['中间段']:
        dao[c1v(m.get('道理句'),K_DAO)]+=1; shou[c1v(m.get('收束类型'),K_SHOU)]+=1
        AS.append(m['句数']); AE.append(m['证据个数']); AN.append(m['数字个数']); AL+=m['句长']; AW+=m['材料外例子个数']
yx=Counter(); dm=Counter(); shuo=0; ld=[]
for i in IDS:
    e=cards[i]['结尾']
    yx[c1v(e.get('意象'),K_YX)]+=1; dm[c1v(e.get('点名'),K_DM)]+=1
    if str(e.get('说大一圈') or '').strip(): shuo+=1
    ld.append(re.split(r'[（(]', str(e.get('落点词') or ''))[0].strip())
def line(name, cc, unit='篇'):
    w(f"| {name} | " + '；'.join(f'{k} {v}' for k,v in cc.most_common()) + ' |')
w('| 项目 | 分布 |')
w('|---|---|')
line('标题形式', tf); line('标题落点', tl)
line('开头出现的 slot', sc2); line('开头的推法', tui)
w(f"| 观点句来源（48 个分论点） | " + '；'.join(f'{k} {v}' for k,v in srcc.most_common()) + ' |')
w(f"| 道理句（48 段） | " + '；'.join(f'{k} {v} 段' for k,v in dao.most_common()) + ' |')
w(f"| 收束类型（48 段） | " + '；'.join(f'{k} {v}' for k,v in shou.most_common()) + ' |')
line('结尾意象', yx); line('结尾点名', dm)
w(f"| 结尾说大一圈 | 有 {shuo} 篇；无 {12-shuo} 篇 |")
w(f"| 落点词 | " + '；'.join(f'{k} {v}' for k,v in Counter(ld).most_common()) + ' |')
w(f"| 中间段的量（48 段） | 每段 {min(AS)}–{max(AS)} 句均 {sum(AS)/len(AS):.1f}；句长 {min(AL)}–{max(AL)} 字；"
  f"证据 {min(AE)}–{max(AE)} 个均 {sum(AE)/len(AE):.1f}；数字 {min(AN)}–{max(AN)} 个均 {sum(AN)/len(AN):.1f}；材料外例子十二篇共 {AW} 个 |")
tn=sum(len(cards[i]['问题的写法']) for i in IDS)
tz=sum(1 for i in IDS for p in cards[i]['问题的写法'] if p.get('主语是不是广东'))
td=sum(1 for i in IDS for p in cards[i]['问题的写法'] if '定语' in str(p.get('缺点做定语还是谓语','')))
tp=sum(1 for i in IDS for p in cards[i]['问题的写法'] if '谓语' in str(p.get('缺点做定语还是谓语','')))
w(f"| 问题句 {tn} 句 | 主语是广东只有 {tz} 句（{pct(tz,tn)}）；缺点做定语 {td} 次、做谓语 {tp} 次 |")
full=sum(1 for i in IDS if not (cards[i]['材料露脸'].get('没用到') or []))
w(f"| 材料露脸 | {full}/12 篇每则材料都用上了 |")
w()
w('读法（只说十二篇一致或接近一致的）：')
w()
w(f"- **标题「其他」占 {tf.get('其他',0)} 篇，说明四选一口径太窄。** 实际只有两类：两个动宾并列，和「以 A 动 B」的单句。")
w(f"- **引语开头 {sc2['引语']}/12 篇，是开头唯一接近固定的一步。** 但十二篇没有两篇 slot 顺序完全一样，所以开头是可选清单不是流程。")
w(f"- **推法全是多选**（每篇 2–3 个），最常用「重要性」{tui['重要性']}、「职责帽」{tui['职责帽']}、「缺口」{tui['缺口']}。")
w(f"- **道理句抄＋改 {dao['抄']+dao['改']}/48 段**，「默认抄材料判断句、抄不到就不写」成立；但自己造的（{dao['造']} 段）比前期多。")
w(f"- **问题句 {tn} 句里只有 {tz} 句拿广东当主语**，其余挂在下位主体上或包成定语，印证动法 13「缺点包成短板」。")
w(f"- **{full}/12 篇材料全部露脸**（方法第四问真做到了）；**落点全部落在广东的地位上**，说法就三种：走在（全国）前列、中国式现代化、题干自己的目标词——全篇最稳的一条。")
w()
# ── 5
w('## 5. 自造清单')
w()
order=['①标题','②开头','③观点句后半句','④道理句','⑤证据句的连接词和转换动词','⑥收束句句框','⑦结尾','⑧七处之外']
w(f"全部 Z 和 `self_made_part` 共 **{D['z_n']} 条、{D['z_c']} 字**，占十二篇总字数 {pct(D['z_c'],D['ch_all'])}。")
w()
w('| 七处 | ' + ' | '.join(k for k in order if k in D['zc']) + ' |')
w('|---|' + '---|'*len([k for k in order if k in D['zc']]))
w('| 条数 | ' + ' | '.join(str(D['zc'][k]) for k in order if k in D['zc']) + ' |')
w('| 字数 | ' + ' | '.join(str(D['zch'][k]) for k in order if k in D['zc']) + ' |')
w()
o7=D['zc'].get('⑧七处之外',0); oc=D['zch'].get('⑧七处之外',0)
w(f"**七处之外只有 {o7} 条、{oc} 字（{pct(oc,D['z_c'])}）——前期结论「需要自己出词的位置是固定的七处」成立。**")
w('落在七处之外的逐条：' + '；'.join(f'`{t}`（{i}）' for i,t in D['zitems'].get('⑧七处之外',[])))
w('三条都是段间或末段收口前的过渡语，可并成第八处「过渡语」，也可忽略——量太小。')
w()
dedup=defaultdict(Counter)
for k,items in D['zitems'].items():
    for i,t in items: dedup[k][re.sub(r'[\s"“”]','',t)[:14]]+=1
rep=[(k,t,n) for k in order for t,n in dedup.get(k,Counter()).most_common() if n>=2]
w(f"**{D['z_n']} 条自造里，字面在两篇以上重复出现的只有 {len(rep)} 条：**" + '；'.join(f'`{t}`（{k}，{n} 篇）' for k,t,n in rep))
w()
w('**这是本次拟合最该记住的一条负面结论：自造的不是句子，是句框。**')
w('自造的字几乎从不跨篇复用，因为框里填的词每篇都得重新从当次的材料和题干里取。能背的只有框，背句子没有用。')
w()
# ── 6
w('## 6. 词表原料')
w()
w('只列出现两次以上的，次数为十二篇大作文＋十二套小题合计。')
w()
LINK=set('让 把 用 以 要 才能 才有 就能 正 等 就 才 和 为 是 而 以…… 是……的 把……变成 就是要 才是'.split())
lk=[(k,v) for k,v in D['glue'].most_common() if k in LINK and v>=2]
vb=[(k,v) for k,v in D['glue'].most_common() if k not in LINK and v>=2]
w('**连接词**：' + '；'.join(f'{k} {v}' for k,v in lk))
w()
w('**转换动词和补进去的动词**：' + '；'.join(f'{k} {v}' for k,v in vb))
w()
w('策论和对策题里「要」后面跟什么转换动词，按后面接的东西分（沿用改写手册动法 15，十二篇逐条核过，无需增删）：')
w()
w('省里已在做的战略改革→深入推进／持续深化／加快；某地某企业试出来的做法→推广……的做法／经验；')
w('已建成的平台奖项基金→用好／发挥……作用；企业人才这类主体→支持／壮大／培育；一条原则或机制→坚持／围绕／健全。')
w()
NOUN=['根基','基础','底色','招牌','沃土','引擎','动力','脊梁','支撑','屏障','本钱','保障','源泉','底盘','优势','根本','命脉','纽带','磁石','活水']
hit=[]
for i in IDS:
    for p in cards[i]['段落']:
        m=re.search(r'[，,]\s*([^，,。；]{4,20})$', p.get('观点句原文','').rstrip('。'))
        if m and any(nn in m.group(1) for nn in NOUN): hit.append(m.group(1))
w('**观点句后半句的「动词＋角色名词」对**（' + str(len(hit)) + ' 个分论点用了角色名词）：')
w('；'.join(f'`{x}`' for x in hit))
w()
w('**名词配动词是固定的**（改写手册「硬编码：词」，十二篇全部对得上）：根基／基础配夯实、筑牢；')
w('底色／招牌配擦亮、厚植；脊梁配挺起；引擎配点燃；最后一公里／堵点配打通；短板配补齐、补上；沃土配厚植；链条配畅通。')
w()
vp=Counter()
for i in IDS:
    for r in cl[i]:
        for m in re.finditer(r'动词[：:]\s*([^\s，,。；;、]{1,6})\s*[→>-]+\s*([^\s，,。；;、）)]{1,6})', str(r.get('note') or '')):
            vp[f'{m.group(1)}→{m.group(2)}']+=1
w('**被换过的动词对**（只统计 note 里明写「动词：X→Y」的，实际换词比这多）：')
w('；'.join(f'{k} {v}' for k,v in vp.most_common() if v>=2) or '（无两次以上的）')
w('。出现一次的另有 ' + str(sum(1 for k,v in vp.items() if v==1)) + ' 对，逐条见各篇 `clauses.jsonl` 的 note。')
w()
SOFT=['同样存在','尚未根本改变','亟待','有待','补齐','补上','短板','不足','缺','弱','低','不够']
sf=Counter()
for i in IDS:
    for p in cards[i]['问题的写法']:
        for s0 in SOFT:
            if s0 in p.get('原句',''): sf[s0]+=1
w('**写问题时的软化说法**：' + '；'.join(f'{k} {v}' for k,v in sf.most_common() if v>=2))
w('。用得最多的是把缺点包进「……的短板／问题」当定语；整句照抄材料已软化好的说法（尚未根本改变、亟待优化、有待提高）次之。')
w()
role=[]
for i in IDS:
    d0=str(cards[i]['结尾'].get('点名',''))
    if '配角色词' in d0 and '不配' not in d0:
        m=re.search(r'[（(]([^：:）)]*)[：:]', d0)
        role.append((i, m.group(1) if m else d0[:24]))
w('**结尾点名用的角色词**（八篇配了词）：' + '；'.join(f'{i} {x}' for i,x in role))
w()
w('分两式，各四篇：**动词式**（筑基／赋能／守底／拓路／铸魂、固本／攻坚／转化／支撑）和**名词式**（之本／之势／之源／之土、本钱／转化／滋养／落点）。')
w('**落点词**见 4.2，就三种：走在（全国）前列、中国式现代化（广东实践的新篇章）、题干自己的目标词。')
w()
# ── 7
w('## 7. 四个待定的写法')
w()
w('前期只有三篇样本，这四种都只出现过一两次，被当成可能的过拟合搁置。')
w('**十二篇的结论：三种进最后那一页纸，一种不进。**')
w()
w('| 写法 | 篇数 | 进不进 | 在哪几篇 |')
w('|---|---|---|---|')
w('| 比喻式的收束句 | 5 | **进** | 2024一卷、2024二卷、2025县镇、2025省市、2026县镇 |')
w('| 结尾点名时给每项配角色词 | 8 | **进** | 2020县级、2021县级、2023县级、2024一卷、2024选调、2025选调、2026县镇、2026省市 |')
w('| 结尾说大一圈 | 5 | **进** | 2024一卷、2024选调、2025省市、2025选调、2026县镇 |')
w('| 引语后面接「不是……而是……」 | 2 | **不进** | 只有 2025省市、2026省市 真的紧接在引语后 |')
w()
w('**7.1 比喻式收束（5 篇，前期「只是 Fable 的习惯、不用学」推翻）。** 原句：`自立自强才有源头活水`（2024一卷）；')
w('`县域这块"潜力板"越做越大`（2024二卷）；`乡村由此有了源头活水`、`产业"壮骨"，乡风才能"铸魂"`（2025县镇）；')
w('`让创新的源头活水源源不断流向新质生产力`、`创新的雨林生态才能枝繁叶茂`（2025省市）；`这笔"绿色银行"存得越厚`（2026县镇）。')
w('比喻的来源是固定的：**顺着材料里已有的一个名词往下接**（源头→源头活水、三棵树→雨林、绿色银行→存得越厚）。')
w()
w('**7.2 点名配角色词（8 篇，前期「参考答案都没有、只有 Fable 两次、可选」推翻）。**')
w('十二篇**全部点名**，没有一篇不点；其中八篇给每项配了角色词，两式各四篇（词见 6 节）。这是本节改动最大的一条。')
w()
w('**7.3 说大一圈（5 篇）。** 原句：`不是一朝一夕之功，而是竞速赛、耐力赛、接力赛`（2024一卷，时间）；`青年的命运，从来同时代紧密相连`（2024选调）；')
w('`创新这篇大文章没有句号，只有连续不断的新起点`（2025省市，时间）；`海洋强省不是海边的事，而是全省的事`（2025选调，范围）；`绿美生态建设是持久战`（2026县镇）。')
w('**「……没有句号，只有连续不断的新起点」和「……不是 X 的事，而是 Y 的事」两个框可以直接背。**')
w()
w('**7.4 引语后面接「不是……而是……」（2 篇，不进）。** 全文出现这类纠偏句的有六篇：')
w('2020县级（道理句）、2024一卷（结尾起兴）、2025县镇（道理句）、2025省市（引语后）、2025选调（结尾）、2026省市（引语后）。')
w('**但真正紧接引语的只有两篇，不到门槛。** 该进那页纸的是它的上位写法：**纠偏式判断句，位置不限**')
w('（道理句、结尾起兴、收尾都行，六篇）。把它绑在「引语后面」是前期三篇样本造成的错觉。')
w()
# ── 8
w('## 8. 新候选')
w()
w('门槛：现有口径装不下，且在三套以上卷子的定稿里出现。')
w()
w('| 候选 | 材料的样子 | 改法 | 成品 | 证据 |')
w('|---|---|---|---|---|')
w('| **C13 两处拼一句** | 不相邻的两处（常跨自然段或跨材料），各有半句可用 | 各取半句，中间补一个动词 | 让制造强国梦后继有人／奋斗要有舞台，也要有本领 | 大作文 8 篇以上，O 类最大一族 |')
w('| **C14 反向指代**（从个例升到上位类） | 一个具体人名、企业名、设施名 | 换成它所属的类名，例子不留 | 园区最大的企业是一家粮油食品公司→龙头企业受困 | 小题 4 套 |')
w('| **C15 具体化** | 一句现成的方向性建议 | 往下落一层，补一个材料没有的工具 | 充分借助科技手段→用无人机巡山 | 小题 3 套 |')
w('| **C16 概括题版的 C12** | 一个成绩、机构名、既成事实 | 反推产生它的动作，补一个动词 | 累计 62 家组织获省政府质量奖→设立省政府质量奖 | 小题 3 套 |')
w()
w('**处理建议（不必都给新编号）：**')
w()
w('- **C13 值得单开**：它是改写手册动法 22，翻成十二种情况时漏掉了。它和 C8 长得像但不是一回事——**C8 要求材料里一句讲手段、一句讲效果，C13 的两半没有这层关系**；现在 C8 在兜底，把两者混在一起。')
w('- **C14 值得单开**：C7 正好是反方向（留住例子指代一类），这是 C7 的逆运算而非变体。小题里比大作文多，因为小题要的是类不是例。')
w('- **C15 不必新增**：补进去的字来自方法 4.5 那张「对策的工具」表，可以事先背；口径里写明**这种补词记进 `self_made_part`，case 按材料那句的形状标**即可。')
w('- **C16 不必新增编号**：把 C12 的限定从「策论和对策题」放宽成「策论、对策题和概括做法题」，**对策题加「要」，概括题不加**。形状本来一样，只差一个字。')
w('- **不够格的三条**：①「问题照抄成问题」（小题 4 套）就是 C1，只是 C11 的名字让人以为问题句都该归 C11，**改 C11 的说明即可**；②「把一段做法概括成对仗短语」（大作文 3 篇）本质是自造，归 Z 更诚实；③「主客翻转／判断句改使令句」（2 篇）不到三篇，且手册已判为低性价比写法。')
w()
# ── 9
w('## 9. 小题')
w()
w('第一批（2023–2026 省考七套＋两套选调前两题）做完后，最后三套仍在冒新情况（2026县镇报告「不够，三类装不下」），')
w('按规则触发第二批（2020–2022 三套）。**十二套全做了。**')
w()
KQ=[k for k in CASES if D['q_tot'].get(k,0)]
w('十二套合计 ' + str(sum(len(q1[i]) for i in IDS)) + ' 个要点、' + str(D['qn']) + ' 条分句：')
w()
w('| case | ' + ' | '.join(KQ) + ' |')
w('|---|' + '---|'*len(KQ))
w('| 条数 | ' + ' | '.join(str(D['q_tot'][k]) for k in KQ) + ' |')
w('| 占比 | ' + ' | '.join(pct(D['q_tot'][k],D['qn']) for k in KQ) + ' |')
w()
w('逐套的分句数：' + '；'.join(f'{i} {n}' for i,n,_ in D['q_rows']) + '。')
w()
w(f"表面覆盖率 {D['qcov']}/{D['qn']} = {pct(D['qcov'],D['qn'])}。**但这个数要打折看。**")
w()
w('**`q12.jsonl` 的 `body` 元素只有 `text / case / sources / glue / self_made_part` 五个字段，没有 `note`；**')
w('而口径规定「标 O 必须在 note 里说明它是怎么变的」——于是 **O 在小题里事实上不可用**。')
w('十二个 agent 里有五个独立报告了同一后果：判下来该标 O 的分句，因为写不了说明，只好就近挂到一个 C 上。')
w(f"所以小题的 {pct(D['qcov'],D['qn'])} **不能**和大作文的 {pct(D['cov_all'],D['n_all'])} 直接比。")
w('**建议给 `body` 加一个 `note` 字段，然后重跑一遍小题的 case。**')
w()
t3=D['q_tot'].get('C1',0)+D['q_tot'].get('C10',0)+D['q_tot'].get('C11',0)
w(f"- **C1＋C10＋C11 三种占 {t3}/{D['qn']} = {pct(t3,D['qn'])}**，比大作文集中得多。")
w(f"- **C2＋C7 合计只有 {D['q_tot'].get('C2',0)+D['q_tot'].get('C7',0)} 条，C9 只有 {D['q_tot'].get('C9',0)} 条。**")
w('  小题不引领导人的话、不用例子指代一类；**数字在小题里一律删光**，不像大作文那样改写成「稳居第一／四成」。')
w()
tls=sum(D['ls'].values())
w('**标签的来源和形式**（' + str(tls) + ' 个要点）：')
w()
w('| 来源 | ' + ' | '.join(k or '（无标签）' for k,_ in D['ls'].most_common()) + ' |')
w('|---|' + '---|'*len(D['ls']))
w('| 次数 | ' + ' | '.join(f'{v}（{pct(v,tls)}）' for _,v in D['ls'].most_common()) + ' |')
w()
w('| 形式 | ' + ' | '.join(k or '（无标签）' for k,_ in D['lf'].most_common()) + ' |')
w('|---|' + '---|'*len(D['lf']))
w('| 次数 | ' + ' | '.join(f'{v}（{pct(v,tls)}）' for _,v in D['lf'].most_common()) + ' |')
w()
w(f"**近六成标签的字能在材料里找到**（材料原词 {pct(D['ls'].get('材料原词',0),tls)}＋总结句或目的句 {pct(D['ls'].get('材料的总结句或目的句',0),tls)}），")
w('真正自己想的不到一半。判这三者有一条线好用，也是小题里最容易判错的一项：')
w('**字原样出现在材料里就算原词；是某句总结句或目的句压缩来的算第三类；两者都不是才算自己概括。**')
w()
w(f"**形式上动宾一种占 {pct(D['lf'].get('动宾',0),tls)}。题型决定形式**：做法题用动宾，问题题用名词＋坏词，作用／成效题用名词＋判断或主体＋作用。")
w()
dn=D['duice_n']; dc=D['duice']
w(f"**对策题里 C11 和 C12 各占多少**——只能用确有对策部分的八套算（{'、'.join(D['duice_ids'])}），共 {dn} 条：")
w()
w('| case | ' + ' | '.join(k for k,v in sorted(dc.items(), key=lambda x:-x[1]) if v) + ' |')
w('|---|' + '---|'*len([1 for k,v in dc.items() if v]))
w('| 条数 | ' + ' | '.join(f'{v}（{pct(v,dn)}）' for k,v in sorted(dc.items(), key=lambda x:-x[1]) if v) + ' |')
w()
w(f"**C11 {pct(dc.get('C11',0),dn)}、C12 {pct(dc.get('C12',0),dn)}，比约 {dc.get('C11',0)/max(dc.get('C12',1),1):.0f}∶1。**")
w('另外四套（2020县级、2021县级、2022县级、2023县级）**没有对策题**（它们是概括做法、分析作用、理解题），')
w('C11＋C12 合计只有 1 条，不该算进分母。C11 压倒 C12 是材料侧决定的：对策题的材料基本是一张问题清单')
w('（调研发现、座谈会发言），讲「已经做了什么」的段落很少。')
w()
w('**小题比大作文多出来的动作，不只「起标签」一种**，十二个 agent 反复报告了四种：')
w()
w('1. **起标签**，并判它的来源和形式（大作文完全没有这三个字段）。')
w('2. **要点的切分与编号**：大作文按句号分号切、切法机械；小题得自己判断哪几个字算一个独立采分点，没有标点可依，还要把跨段落甚至跨材料的碎片并进同一要点。')
w('3. **问题与对策的配对**：对策题里第 n 条对策镜像第 n 条问题，同一句材料常被拆开，一半进问题一半进对策，判 case 时得照配对关系一起看。')
w('4. **压缩强度高一档**：小题每分句 5–10 字、大作文 15–25 字；同样标 C1，小题删掉的成分多得多，这让 C1 与 C10 的边界在小题里更模糊。')
w()
w('反向的事实同样值得记：`body` 比 `clauses` 少了 `slot / para / sent / seg / note` 五个字段，')
w('所以标 O 的说明、动词近义替换（防控→控制、首次→第一次）在小题里**无处记录，信息是丢失的**。')

open('07_句子层/out/汇总.md','w',encoding='utf-8').write('\n'.join(L)+'\n')
print('写出 07_句子层/out/汇总.md：', len(L), '行')
