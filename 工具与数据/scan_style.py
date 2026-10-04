# -*- coding: utf-8 -*-
"""全卷虚词密度与高频句式扫描器
用法: python scan_style.py  (在 对照本与排版/ 目录下运行)
输出: data/虚词句式扫描明细.csv, data/四字句式频次.csv, 控制台摘要
"""
import re, os, csv, json
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
BOOKDIR = os.path.join(ROOT, "..", "完整版108回红楼梦")

# 核心监测词（密集即复核对象）
CORE = ["一时", "只见", "只听", "说道", "半日", "只得", "谁知"]
# 参考统计词
REF = ["笑道", "因道", "忙道", "不觉", "越发", "原来", "且说", "却说", "话说",
       "不在话下", "按下不表", "要知端的", "且听下回分解", "唬的", "越性", "猛可里"]
ALL = CORE + REF

def chapter_files():
    refined = {3,7,9,10,13,17,18,22,33,64,67,71,80}
    files = {}
    for n in range(1,81):
        p = os.path.join(BOOKDIR, "前八十回精修稿", "第%03d回.md" % n) if n in refined \
            else os.path.join(BOOKDIR, "前八十回润色稿", "第%03d回.md" % n)
        files[n] = p
    for n in range(81,109):
        files[n] = os.path.join(BOOKDIR, "精修稿", "第%03d回.md" % n)
    return files

def load_chapters():
    chapters = {}
    for n, p in chapter_files().items():
        t = open(p, encoding="utf-8").read()
        title = t.split("\n",1)[0].lstrip("# ").strip()
        body = t.split("\n",1)[1] if "\n" in t else ""
        # 段落切分（跨行块=诗行段，另行标记）
        paras = []
        for blk in body.split("\n\n"):
            blk = blk.strip()
            if not blk: continue
            is_verse = "\n" in blk
            txt = re.sub(r"\s+", "", blk) if not is_verse else blk.replace("\n","")
            paras.append({"text": txt, "verse": is_verse, "raw": blk})
        chapters[n] = {"title": title, "paras": paras,
                       "chars": sum(len(re.sub(r'\s','',p['raw'])) for p in paras)}
    return chapters

def main():
    chs = load_chapters()
    rows = []          # 段级明细
    ch_stats = []      # 回级统计
    gram = Counter()   # 四字句式
    for n in sorted(chs):
        c = chs[n]
        cnt = {w:0 for w in ALL}
        body_chars = 0
        for pi, para in enumerate(c["paras"]):
            if para["verse"]:
                continue
            t = para["text"]
            body_chars += len(t)
            hits = {w: t.count(w) for w in ALL}
            for w,v in hits.items(): cnt[w]+=v
            core_total = sum(hits[w] for w in CORE)
            flags = []
            if hits["一时"]>=2: flags.append("一时×%d"%hits["一时"])
            if hits["只见"]>=2: flags.append("只见×%d"%hits["只见"])
            if hits["说道"]>=3: flags.append("说道×%d"%hits["说道"])
            if core_total>=4: flags.append("核心合计×%d"%core_total)
            if any(hits[w]>=3 for w in CORE if w not in("一时","只见","说道")): flags.append("单词≥3")
            if flags:
                rows.append({"回":n,"段":pi,"旗标":"；".join(flags),"字符":len(t),
                             "正文":t[:80] + ("……" if len(t)>80 else "")})
            # 四字句式（跳过套语由事后过滤）
            for i in range(len(t)-3):
                g = t[i:i+4]
                if re.fullmatch(r'[\u4e00-\u9fff]{4}', g):
                    gram[g]+=1
        per1k = {w: round(cnt[w]/(body_chars/1000),2) for w in CORE}
        ch_stats.append({"回":n,"标题":c["title"],"正文字符":c["chars"],
                         "核心密度/千字": round(sum(cnt[w] for w in CORE)/(body_chars/1000),2),
                         **{w:cnt[w] for w in ALL}, **{w+"/千字":per1k[w] for w in CORE}})

    os.makedirs(os.path.join(ROOT,"data"), exist_ok=True)
    with open(os.path.join(ROOT,"data","虚词句式扫描明细.csv"),"w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f, fieldnames=["回","段","旗标","字符","正文"]); w.writeheader()
        for r in rows: w.writerow(r)
    with open(os.path.join(ROOT,"data","回级统计.csv"),"w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f, fieldnames=list(ch_stats[0].keys())); w.writeheader()
        for r in ch_stats: w.writerow(r)
    # 四字句式：过滤专名/套语后输出前120
    stop = set(["且听下回分解","要知端的","不在话下","按下不表","不知端的","不知怎么样","下回分解","姊妹两个","弟兄两个","两个丫头","两个婆子","两个小厮","两个人来","一个丫头","一个小厮","一家子的","一声儿不","一句话不","一步步的","一层层的"])
    grams = [(g,c) for g,c in gram.most_common(400) if g not in stop and c>=12][:120]
    with open(os.path.join(ROOT,"data","四字句式频次.csv"),"w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f); w.writerow(["四字句式","频次"]); w.writerows(grams)

    # 摘要
    total_core = {w: sum(s[w] for s in ch_stats) for w in CORE}
    total_chars = sum(s["正文字符"] for s in ch_stats)
    print("全卷正文字符:", total_chars)
    print("核心词全卷次数:", total_core)
    print("全卷核心密度/千字:", round(sum(total_core.values())/total_chars*1000,2))
    print("密集段数:", len(rows))
    print("\n密度最高的12回:")
    for s in sorted(ch_stats, key=lambda x:-x["核心密度/千字"])[:12]:
        print(f"  第{s['回']}回 密度{s['核心密度/千字']} 一时{s['一时']} 只见{s['只见']} 说道{s['说道']} 半日{s['半日']} | {s['标题'][:20]}")
    print("\n四字句式前20:", grams[:20])
    json.dump({"ch_stats":ch_stats,"rows":rows,"grams":grams}, open(os.path.join(ROOT,"data","scan.json"),"w",encoding="utf-8"), ensure_ascii=False)

if __name__ == "__main__":
    main()
