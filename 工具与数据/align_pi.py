# -*- coding: utf-8 -*-
"""脂批提取与对位：把gitbook脂评本中的批语按原位置映射回终稿前80回文本
输出: data/脂批对位.json, data/脂批对位统计.csv
"""
import re, os, json, csv

ROOT = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.join(ROOT, "..", "完整版108回红楼梦")
GIT = os.path.join(ROOT, "..", "gitbook-hongloumeng-master", "ch")
REFINED = {3,7,9,10,13,17,18,22,33,64,67,71,80}
CN='零一二三四五六七八九十'

def strip_ws(t): return re.sub(r'\s+','',t)

def batch_pat(t):
    # 批语块：```( ... )```，允许多行
    return [(m.start(), m.end(), m.group(1).strip()) for m in re.finditer(r'```\s*\((.+?)\)\s*```', t, re.S)]

results = {}
tot=0; mapped=0; unmapped=[]
for n in range(1,81):
    raw = open(os.path.join(GIT, "%03d.md"%n), encoding="utf-8").read()
    # 正文=去批语后的文本（与净本口径一致），批语锚点取批语前后各25字
    spans = batch_pat(raw)
    plain_parts = []
    pos = 0
    items = []
    plain = ""
    for s,e,txt in spans:
        seg = raw[pos:s]
        plain += seg
        before = strip_ws(plain)[-25:]
        after_seg = raw[e:e+60]
        after = strip_ws(after_seg)[:25]
        items.append({"before":before, "after":after, "batch":re.sub(r'\s+','',txt)})
        plain += after_seg  # after也并入plain以维持相对位置
        pos = e
    plain += raw[pos:]
    tot += len(items)
    # 终稿文本
    p = os.path.join(BOOK, "前八十回精修稿", "第%03d回.md"%n) if n in REFINED \
        else os.path.join(BOOK, "前八十回润色稿", "第%03d回.md"%n)
    full = open(p, encoding="utf-8").read()
    head, _, body = full.partition("\n\n")
    our = strip_ws(body)
    # 段落边界（用于DOCX嵌入）：记录每段起止在strip文本中的位置
    paras = []
    cur = 0
    for blk in body.split("\n\n"):
        b = strip_ws(blk)
        if b:
            paras.append({"start":cur, "end":cur+len(b), "text":b})
            cur += len(b)
    mapped_list = []
    last = -1
    for it in items:
        pos = -1
        b4, af = it["before"], it["after"]
        if len(b4) >= 6:
            i = our.find(b4)
            while i >= 0:
                j = i + len(b4)
                k = our.find(af[:10], j) if af else j
                if af == "" or (k == j) or (0 <= k-j <= 30 and af[:10]==our[j:j+min(10,len(af))] if False else True):
                    # 宽松验证：after前6字出现在批语位之后30字内
                    k6 = our.find(af[:6], j) if af else j
                    if af=="" or (k6!=-1 and k6-j<=30):
                        pos = j; break
                i = our.find(b4, i+1)
        if pos < 0 and len(af) >= 8:
            # 仅用后锚
            i = our.find(af[:8])
            if i >= 0:
                pos = i
        if pos < 0 and len(b4) < 6 and len(b4) > 0:
            i = our.find(b4)
            if i >= 0: pos = i + len(b4)
        if pos < 0 or (last>=0 and pos < last):
            unmapped.append({"回":n, "before":b4[-12:], "after":af[:12], "batch":it["batch"][:40]})
            continue
        mapped += 1; last = pos
        mapped_list.append({"pos":pos, "batch":it["batch"], "type": it["batch"][:4]})
    results[n] = {"head": head, "paras": paras, "annos": sorted(mapped_list, key=lambda x:x["pos"])}

json.dump(results, open(os.path.join(ROOT,"data","脂批对位.json"),"w",encoding="utf-8"), ensure_ascii=False)
with open(os.path.join(ROOT,"data","脂批对位统计.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(["回","批语数","对位数"])
    for n in range(1,81):
        w.writerow([n, len(results[n]["annos"]), ""])
    w.writerow(["合计", tot, f"对位{mapped} / 未对位{len(unmapped)}"])
print("批语总数:", tot, " 对位:", mapped, " 未对位:", len(unmapped))
per_ch = {n: len(results[n]["annos"]) for n in results}
print("批语最多10回:", sorted(per_ch.items(), key=lambda x:-x[1])[:10])
print("未对位样例:", unmapped[:5])
