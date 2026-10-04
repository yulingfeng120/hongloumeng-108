# -*- coding: utf-8 -*-
"""电子书导出：EPUB（全本/脂批对照本）、TXT、单文件HTML
从《红楼梦全本一百零八回（开源共享版）.md》驱动，批语从 data/脂批对位.json 嵌入。
"""
import re, os, json, zipfile, html

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "..")
MD = os.path.join(OUT, "红楼梦全本一百零八回（开源共享版）.md")

def clean(t):
    return re.sub(r'\s+', '', t.replace('&nbsp;','').replace('&quot;','"'))

def esc(t):
    return html.escape(t, quote=False)

def parse_md():
    t = open(MD, encoding="utf-8").read()
    i = re.search(r'^# 第[零〇一二三四五六七八九十百]+回', t, re.M).start()
    body = t[i:]
    parts = re.split(r'^(# 第[零〇一二三四五六七八九十百]+回 .+)$', body, flags=re.M)
    chapters = []
    for k in range(1, len(parts), 2):
        title = parts[k].lstrip('# ').strip()
        content = re.sub(r'^-{3,}\s*', '', parts[k+1].strip()).strip()
        blocks = []
        for blk in content.split("\n\n"):
            blk = blk.strip()
            if not blk or re.fullmatch(r'-{3,}', blk): continue
            is_verse = "\n" in blk
            if is_verse:
                lines = [l.strip().lstrip('　') for l in blk.split("\n") if l.strip()]
                blocks.append({"verse": True, "text": clean(blk), "lines": lines})
            else:
                blocks.append({"verse": False, "text": clean(blk), "lines": [clean(blk)]})
        chapters.append({"title": title, "blocks": blocks})
    # 序言
    j = t.find("# 序")
    xu = t[j:t.find("## 目录")].strip()
    xu_paras = [l.strip() for l in xu.split("\n") if l.strip() and not l.startswith("# 序")]
    return xu_paras, chapters

def cn_num(n):
    d="零一二三四五六七八九十"
    if n<10: return d[n]
    if n==10: return "十"
    if n<20: return "十"+d[n-10]
    if n<100:
        a,b=divmod(n,10); return d[a]+"十"+(d[b] if b else "")
    if n==100: return "一百"
    return "一百零"+d[n-100]

CSS = """body{font-family:serif;line-height:1.8;margin:1em;color:#1a1a1a}
h1{text-align:center;font-size:1.6em;margin:1.2em 0}
h2{text-align:center;font-size:1.25em;margin:1.5em 0 1em}
p{text-indent:2em;margin:0.35em 0;text-align:justify}
p.verse{text-indent:0;text-align:center;font-family:KaiTi,serif;margin:0.5em 0}
span.anno{color:#8b0000;font-size:0.85em;font-family:KaiTi,serif}
.hint{color:#666;font-size:0.85em;text-indent:0}
p.byline{text-align:center;font-family:KaiTi,serif;text-indent:0}
nav ol{list-style:none;padding-left:0} nav a{text-decoration:none;color:#1a1a1a}"""

def chapter_xhtml(idx, ch, annos=None):
    n = idx
    p = []
    p.append('<?xml version="1.0" encoding="utf-8"?>')
    p.append('<!DOCTYPE html>')
    p.append('<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN"><head>')
    p.append('<meta charset="utf-8"/><title>%s</title><link rel="stylesheet" href="../style.css" type="text/css"/></head>' % esc(ch["title"]))
    p.append('<body><h2 id="ch%d">%s</h2>' % (n, esc(ch["title"])))
    ai = 0; cursor = 0
    annos = annos or []
    for blk in ch["blocks"]:
        start, end = cursor, cursor+len(blk["text"]); cursor = end
        in_range = [a for a in annos[ai:] if a["pos"] < end]
        ai += len(in_range)
        if blk["verse"]:
            for ln in blk["lines"]:
                p.append('<p class="verse">%s</p>' % esc(ln))
            for a in in_range:
                p.append('<p class="verse anno">〔批：%s〕</p>' % esc(a["batch"]))
            continue
        cuts = [max(0, min(a["pos"]-start, len(blk["text"]))) for a in in_range]
        segs=[]; last=0
        for cp in cuts: segs.append(blk["text"][last:cp]); last=cp
        segs.append(blk["text"][last:])
        p.append('<p>')
        for k, seg in enumerate(segs):
            if seg: p.append(esc(seg))
            if k < len(in_range):
                p.append('<span class="anno">〔%s〕</span>' % esc(in_range[k]["batch"]))
        p.append('</p>')
    p.append('</body></html>')
    return "\n".join(p)

def xu_xhtml(xu_paras):
    p = ['<?xml version="1.0" encoding="utf-8"?>','<!DOCTYPE html>',
         '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN"><head>',
         '<meta charset="utf-8"/><title>序</title><link rel="stylesheet" href="../style.css" type="text/css"/></head>',
         '<body><h1>序</h1>']
    for l in xu_paras:
        if re.match(r'^第[\d零〇一二三四五六七八九十百]+回　', l): continue
        if l == "西域吃沙的峰兄":
            p.append('<p class="byline">%s</p>' % esc(l))
        else:
            p.append('<p>%s</p>' % esc(l))
    p.append('</body></html>')
    return "\n".join(p)

def build_epub(out_path, annos_mode=False):
    xu_paras, chapters = parse_md()
    data = json.load(open(os.path.join(ROOT,"data","脂批对位.json"), encoding="utf-8")) if annos_mode else None
    unm = json.load(open(os.path.join(ROOT,"data","未对位批语.json"), encoding="utf-8")) if annos_mode else None
    book_id = "hlm108-open-share" + ("-piping" if annos_mode else "")
    title = "红楼梦（一百零八回足本）" + ("·前八十回脂批对照" if annos_mode else "")
    zf = zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED)
    zf.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
    zf.writestr("META-INF/container.xml",
        '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    zf.writestr("OEBPS/style.css", CSS)
    zf.writestr("OEBPS/text/xu.xhtml", xu_xhtml(xu_paras))
    files = ["text/xu.xhtml"]
    for idx, ch in enumerate(chapters):
        n = idx+1
        annos = data[str(n)]["annos"] if annos_mode and n<=80 and str(n) in data else []
        fn = "text/ch%03d.xhtml" % n
        zf.writestr("OEBPS/"+fn, chapter_xhtml(n, ch, annos))
        files.append(fn)
    if annos_mode:
        ap = ['<?xml version="1.0" encoding="utf-8"?>','<!DOCTYPE html>',
              '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN"><head>',
              '<meta charset="utf-8"/><title>附录：未对位批语辑录</title><link rel="stylesheet" href="../style.css" type="text/css"/></head>',
              '<body><h2>附录：未对位批语辑录（229条）</h2>',
              '<p class="hint">以下批语因正文对应段被鬼本织入文字替换或锚文变动，未能随文排出；每条后注所系前后句，供在脂本原书中复核。</p>']
        from collections import defaultdict
        by = defaultdict(list)
        for u in unm: by[u["回"]].append(u)
        for n2 in sorted(by):
            ap.append('<h2>第%d回</h2>' % n2)
            for x in by[n2]:
                ap.append('<p><span class="anno">〔%s〕</span></p>' % esc(x["batch"]))
                hint = ("系于「%s」句后" % x["before"]) if x["before"] else ""
                if x["after"]: hint += ("、「%s」句前" % x["after"]) if hint else ("系于「%s」句前" % x["after"])
                if hint: ap.append('<p class="hint">%s</p>' % esc(hint))
        ap.append('</body></html>')
        zf.writestr("OEBPS/text/appendix.xhtml", "\n".join(ap))
        files.append("text/appendix.xhtml")
    # nav.xhtml
    nav = ['<?xml version="1.0" encoding="utf-8"?>','<!DOCTYPE html>',
           '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN"><head>',
           '<meta charset="utf-8"/><title>目录</title></head><body><nav epub:type="toc" id="toc"><h1>目录</h1><ol>',
           '<li><a href="text/xu.xhtml">序</a></li>']
    for idx, ch in enumerate(chapters):
        nav.append('<li><a href="text/ch%03d.xhtml">%s</a></li>' % (idx+1, esc(ch["title"])))
    if annos_mode: nav.append('<li><a href="text/appendix.xhtml">附录：未对位批语辑录</a></li>')
    nav.append('</ol></nav></body></html>')
    zf.writestr("OEBPS/nav.xhtml", "\n".join(nav))
    # toc.ncx
    ncx = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head>',
           '<meta name="dtb:uid" content="urn:uuid:%s"/>' % book_id,
           '<meta name="dtb:depth" content="1"/><meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>',
           '<docTitle><text>%s</text></docTitle>' % esc(title), '<navMap>']
    np = [("序","text/xu.xhtml")] + [(ch["title"], "text/ch%03d.xhtml"%(i+1)) for i,ch in enumerate(chapters)]
    if annos_mode: np.append(("附录：未对位批语辑录","text/appendix.xhtml"))
    for i,(t2,src) in enumerate(np):
        ncx.append('<navPoint id="np%d" playOrder="%d"><navLabel><text>%s</text></navLabel><content src="%s"/></navPoint>' % (i, i+1, esc(t2), src))
    ncx.append('</navMap></ncx>')
    zf.writestr("OEBPS/toc.ncx", "\n".join(ncx))
    # content.opf
    manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
                '<item id="css" href="style.css" media-type="text/css"/>',
                '<item id="xu" href="text/xu.xhtml" media-type="application/xhtml+xml"/>']
    spine = ['<itemref idref="xu"/>']
    for i in range(1,109):
        manifest.append('<item id="c%03d" href="text/ch%03d.xhtml" media-type="application/xhtml+xml"/>' % (i,i))
        spine.append('<itemref idref="c%03d"/>' % i)
    if annos_mode:
        manifest.append('<item id="appendix" href="text/appendix.xhtml" media-type="application/xhtml+xml"/>')
        spine.append('<itemref idref="appendix"/>')
    opf = ['<?xml version="1.0" encoding="utf-8"?>',
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="zh-CN">',
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">',
           '<dc:identifier id="bookid">urn:uuid:%s</dc:identifier>' % book_id,
           '<dc:title>%s</dc:title>' % esc(title),
           '<dc:creator>西域吃沙的峰兄</dc:creator>',
           '<dc:language>zh-CN</dc:language>',
           '<dc:description>以《吴氏石头记》（癸酉本）剧情框架为骨的一百零八回足本整理版。前八十回以脂评本文字为骨干，后二十八回为精修定稿；文字执行由GLM-5.3-Flash完成。</dc:description>',
           '<meta property="dcterms:modified">2026-10-02T00:00:00Z</meta>',
           '</metadata>',
           '<manifest>'+"\n".join(manifest)+'</manifest>',
           '<spine toc="ncx">'+"\n".join(spine)+'</spine>',
           '</package>']
    zf.writestr("OEBPS/content.opf", "\n".join(opf))
    zf.close()
    print("saved:", out_path, os.path.getsize(out_path)//1024, "KB")

def build_txt(out_path):
    xu_paras, chapters = parse_md()
    L = ["红楼梦（一百零八回足本）","撰次：西域吃沙的峰兄",""]
    L.append("序")
    for l in xu_paras:
        if re.match(r'^第[\d零〇一二三四五六七八九十百]+回　', l): continue
        L.append(l)
    L.append("")
    for idx, ch in enumerate(chapters):
        L.append(ch["title"]); L.append("")
        for blk in ch["blocks"]:
            if blk["verse"]:
                L.extend(blk["lines"]); L.append("")
            else:
                L.append("　　"+blk["text"]); L.append("")
    open(out_path,"w",encoding="utf-8-sig").write("\n".join(L))
    print("saved:", out_path, os.path.getsize(out_path)//1024, "KB")

def build_html(out_path):
    xu_paras, chapters = parse_md()
    p = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1">',
         '<title>红楼梦（一百零八回足本·开源共享版）</title>',
         '<style>'+CSS+'nav{border:1px solid #ccc;padding:1em;margin:1em}nav a{color:#333}</style></head><body>',
         '<h1>红楼梦</h1><p class="byline">一百零八回足本（开源共享版）<br/>西域吃沙的峰兄　撰次</p>',
         '<p class="hint">成书说明：本项目由西域吃沙的峰兄发起并主持，文字执行由GLM-5.3-Flash大语言模型完成，累计消耗tokens约6460万。</p>',
         '<nav><b>目录</b><ol start="0"><li><a href="#xu">序</a></li>']
    for idx, ch in enumerate(chapters):
        p.append('<li><a href="#ch%d">%s</a></li>' % (idx+1, esc(ch["title"])))
    p.append('</ol></nav>')
    p.append('<h1 id="xu">序</h1>')
    for l in xu_paras:
        if re.match(r'^第[\d零〇一二三四五六七八九十百]+回　', l): continue
        if l == "西域吃沙的峰兄": p.append('<p class="byline">%s</p>' % esc(l))
        else: p.append('<p>%s</p>' % esc(l))
    for idx, ch in enumerate(chapters):
        p.append('<h2 id="ch%d">%s</h2>' % (idx+1, esc(ch["title"])))
        for blk in ch["blocks"]:
            if blk["verse"]:
                for ln in blk["lines"]: p.append('<p class="verse">%s</p>' % esc(ln))
            else:
                p.append('<p>%s</p>' % esc(blk["text"]))
    p.append('</body></html>')
    open(out_path,"w",encoding="utf-8").write("\n".join(p))
    print("saved:", out_path, os.path.getsize(out_path)//1024, "KB")

if __name__ == "__main__":
    build_epub(os.path.join(OUT,"红楼梦全本一百零八回（开源共享版）.epub"), annos_mode=False)
    build_epub(os.path.join(OUT,"红楼梦前八十回（脂批对照本·开源共享版）.epub"), annos_mode=True)
    build_txt(os.path.join(OUT,"红楼梦全本一百零八回（开源共享版）.txt"))
    build_html(os.path.join(OUT,"红楼梦全本一百零八回（开源共享版）.html"))
