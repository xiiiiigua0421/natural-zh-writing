#!/usr/bin/env python3
"""Flag common AI-tone patterns in Chinese prose (Markdown or plain text).

Usage:
    python tone_lint.py FILE [FILE ...] [--genre report|letter|essay|post] [--json]

Only prose is checked: fenced code, tables, headings, image lines and $$ math
blocks are skipped, and inline `code` / $math$ is masked first. The output is
a list of hints, not a verdict; it cannot tell whether the text explains
cause and effect, which matters most. For essays, letters and social posts,
do not chase zero flags: a vivid line with a little contrast or emphasis is
welcome there.

The frame-cluster, em-dash, filler-list and written-grammar checks are adapted
from dsh-fish-tone, which measured frame density on 100k Bilibili comments.
dsh-fish-tone is MIT licensed: Copyright (c) 2026 dsh-fish-tone contributors.

The Taiwan-usage (中國用語) word list and a few empty discourse markers come from
de-ai-tone by Allen (https://github.com/allenloves/de-ai-tone), licensed
CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Only words
with little ambiguity in Taiwan were kept.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict

CLICHES = [
    "值得注意的是", "值得一提的是", "綜上所述", "總而言之", "總的來說", "不難看出",
    "不難發現", "由此可見", "扮演著", "扮演了", "至關重要", "具有重要意義", "具有深遠",
    "收穫良多", "深刻體會", "深刻地體會", "受益匪淺", "寶貴的機會", "寶貴的經驗",
    "衷心感謝", "百忙之中", "撥冗", "懇請", "深感抱歉", "賦能", "旨在", "深入探討",
    "全面提升", "顯著提升", "有效的溝通", "不斷提升", "獨特魅力", "充滿活力",
    "毫無疑問", "不得不說", "從某種意義上來說", "更重要的是", "更關鍵的是", "有趣的是",
    "揭示了", "不可或缺",
]
# 中國用語：字形是繁體、用法是大陸的詞。只收台灣幾乎不這樣用的；數據、質量、水平、通過、
# 項目、菜單、窗口、落地、優化這類看義項或台灣也常用的，不自動抓。
# 對照整理自 de-ai-tone（Allen，CC BY-SA 4.0，https://github.com/allenloves/de-ai-tone）。
ZHIYU = {
    "視頻": "影片／視訊", "音頻": "音訊", "軟件": "軟體", "硬件": "硬體", "網絡": "網路",
    "信息": "資訊／訊息", "服務器": "伺服器", "內存": "記憶體", "硬盤": "硬碟", "屏幕": "螢幕",
    "鼠標": "滑鼠", "打印": "列印", "默認": "預設", "缺省": "預設", "人工智能": "人工智慧",
    "用戶": "使用者", "兼容": "相容", "調試": "除錯", "文件夾": "資料夾", "加載": "載入",
    "粘貼": "貼上", "鏈接": "連結", "插件": "外掛", "博客": "部落格", "二維碼": "QR code",
    "U盤": "隨身碟", "充電寶": "行動電源", "復盤": "檢討、回顧", "閉環": "完整流程",
    "抓手": "著力點", "顆粒度": "細緻程度", "賽道": "領域、市場", "矢量": "向量", "標量": "純量",
    "概率": "機率", "隨機變量": "隨機變數", "仿真": "模擬", "渠道": "管道", "立馬": "馬上",
    "網課": "線上課程", "短信": "簡訊", "郵箱": "信箱", "考研": "考研究所", "答辯": "口試",
}
CLICHE_PATTERNS = [
    (r"進行了?(分析|比較|討論|評估|探討|處理|訓練|測試|預測|調整|說明|溝通|研究|整理)", "進行+動詞"),
    (r"對[^，。；]{1,12}進行", "對…進行"),
    (r"被[^，。；]{1,10}所(?![有以])", "被…所"),
    (r"透過[^，。；]{1,15}來", "透過…來"),
    (r"不僅[^。]{1,40}(更|而且|還)", "不僅…更…"),
    (r"首先[^。]{0,80}。[^。]*其次", "首先…其次"),
]
IDIOMS = [
    "滾瓜爛熟", "一目了然", "不言而喻", "顯而易見", "迎刃而解", "事半功倍", "恍然大悟",
    "茅塞頓開", "豁然開朗", "如虎添翼", "畫龍點睛", "相輔相成", "息息相關", "舉足輕重",
]
# rhetorical moves the author asked to keep out of reports
SIGNPOSTS = re.compile(
    r"接著看|接下來看|再來看|先來看|我們來看|來看看|各看一個|要注意的是|需要注意的是|換句話說|簡單來說|說白了|老實說"
)
CONTRASTS = [
    (r"而不是", "而不是"),
    (r"是兩回事", "是兩回事"),
    (r"一個是[^。]{1,30}一個是", "一個是…一個是"),
    (r"不是[^，。；]{1,20}，?而是", "不是…而是"),
    (r"只是[^，。；]{1,20}，不是", "只是…不是"),
]
ENUMS = [
    (r"[兩三四五幾]個(限制|教訓|原因|重點|問題|面向|層面|部分|關鍵)[。：:]", "預告列舉"),
    (r"[兩三四五幾]件事[：:]", "預告列舉"),
    (r"第一[，、][^。]{0,120}。[^。]{0,10}第二", "第一…第二"),
]
INTENSIFIERS = re.compile(r"整整|明顯得多|這才是|才是真正|根本")
# 「典型」與最高級鋪陳加「就是」揭曉：最典型的例子就是…、屬於典型的…、最大的差別就是…、我最大的收穫就是…
SUPERLATIVE_REVEAL = re.compile(
    r"最?(?:典型|經典)[^，。！？；：\n]{0,8}?就是|典型|最經典"
    r"|最[一-鿿]{1,3}的[^，。！？；：\n]{0,12}?就是|(?:例子|案例|範例)就是"
)
# 抽象名詞加「就是」當強調（只查報告）：原因就是… → 原因是…
NOUN_JIUSHI = re.compile(r"(?:原因|問題|關鍵|重點|差別|差異|目的|用意|核心|本質|答案|意思|代價|好處|結論)就是")
SPOKEN = re.compile(
    r"能不能|合不合|會不會|是不是|要不要|好不好|對不對|可不可以|夠不夠|有沒有可能|"
    r"想一想|看一看|試一試|試試看|安安靜靜|清清楚楚|一下子|那一下|大概"
)
REVEAL_WORDS = re.compile(r"同一件事|很直接|很簡單|很明顯|如下|是這樣|一個例子|關鍵在於|原因是|重點是|答案是|結論是|事實是")
FIRST_PERSON = re.compile(r"我們|我")
HEDGES = [
    "不能", "並非", "不代表", "不保證", "不建立", "不等同", "不證明", "仍需",
    "需一併", "需同時", "僅供參考", "偏樂觀", "不應視為", "不可視為",
]
KV = re.compile(r"(?<![\w$])[A-Za-z][\w\-]*(?: [A-Za-z][\w\-]*)?\s?=\s?[-+]?\d")
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z\-]*[A-Za-z]")
CJK = re.compile(r"[一-鿿]")
# 此/該/其 used as literary pronouns, excluding common compounds
LITERARY = re.compile(r"(?<![因如彼藉據就為於])此(?![外刻時後])|(?<!應)該(?![死])|其(?![實他中餘次它])|(?<![對關由屬等])於|亦|皆")

# ── 以下幾項來自 dsh-fish-tone ──
# 句式框架。strict 的真人密度每千字不到 0.1 個；扎堆看的是「100 字內出現幾種不同的」。
FRAMES = [
    ("不是…而是", "strict", re.compile(r"不是[^。！？\n]{1,24}?(?:，\s*(?:這|那|它|就)?是|而是)")),
    ("最…的是", "strict", re.compile(r"最[^，。\n]{1,8}的是")),
    ("先…再", "strict", re.compile(r"先[^，。\n]{1,10}再")),
    ("不僅…更", "strict", re.compile(r"不僅[^，。\n]{1,12}(?:更|還)")),
    ("X的是Y", "soft", re.compile(r"[^的，。！？\n]{1,8}的是[^，。\n]")),
    ("破折號", "soft", re.compile(r"——+|—")),
    ("越…越", "soft", re.compile(r"越[^，。\n]{1,8}越")),
    ("真正／本質上", "soft", re.compile(r"真正|本質上|歸根結底|歸根究柢|說到底")),
    ("首先／其次／綜上", "soft", re.compile(r"首先|其次|綜上所述|總而言之")),
]
EMDASH = re.compile(r"——+|—")
EMDASH_EXPLAINS = re.compile(r"^\s*(因為|就是|也就是|意思是|指的是|說白了|相當於|例如|比如|包括)")
ESSENCE = re.compile(r"本質上|歸根結底|歸根究柢|說到底|究其根本|真正的?(?:意義|關鍵|重點|價值|核心|重要)")
# 湊數並列：三個短詞用頓號串起來，其中至少兩個是空泛的抽象名詞
ABSTRACT_NOUNS = set(
    "效率 品質 穩定 穩定性 彈性 效能 可靠 可靠性 準確 準確性 準確度 安全 安全性 便利 便利性 多元 創新 價值 體驗 "
    "成本 速度 規模 深度 廣度 質量 效果 可讀性 可維護性 擴展性 可擴展性 一致性 完整性 透明度 靈活性 互動性 實用性 "
    "易用性 公平性 穩健性 泛化能力 表現 能力 潛力 競爭力 溝通 合作 責任感 專業 耐心 熱情 細心 成長 挑戰 機會".split()
)
TRIPLE = re.compile(r"[一-鿿]+(?:、[一-鿿]+){2,}")


def abstract_items(run):
    """頓號串的每一項。中文詞沒有邊界，第一項取結尾、最後一項取開頭去比對詞表。"""
    parts = run.split("、")
    out = []
    for idx, p in enumerate(parts):
        if idx == 0:
            cands = [p[-n:] for n in (4, 3, 2) if len(p) >= n]
        elif idx == len(parts) - 1:
            cands = [p[:n] for n in (4, 3, 2) if len(p) >= n]
        else:
            cands = [p]
        out.append(next((c for c in cands if c in ABSTRACT_NOUNS), None) or p)
    return out
# 書面語病：交出去的文字一律修掉
GRAMMAR = [
    (re.compile(r"(?:透過|通過|經過|由於)[^，。！？\n]{2,18}?使(?:得)?"), "介詞吃掉主詞（透過…使…）"),
    (re.compile(r"(?:防止|避免|杜絕|切忌|以免|以防)[^，。！？的\n]{0,8}?不(?!小心)(?:再|會|要|能)"), "否定疊加說反（防止…不…）"),
    (re.compile(r"一(?:個|位|名)[^，。兒\n]{0,3}?們"), "量詞撞複數（一個…們）"),
    (re.compile(r"(?:很多|好多|幾個|數個|一群)[^，。\n]{0,4}?們"), "量詞撞複數（很多…們）"),
    (re.compile(r"(?:原因是|根源是|是因為)[^，。！？\n]{1,24}?(?:造成的|所導致|引起的)"), "句式雜糅（原因是…造成的）"),
    (re.compile(r"(?:本著|根據|按照|基於)[^，。\n]{1,16}?(?:為原則|為宗旨|為基礎)"), "句式雜糅（本著…為原則）"),
    (re.compile(r"(?:大約|約|將近|差不多)[^，。\n]{0,8}?(?:左右|上下)"), "同義反覆（約…左右）"),
    (re.compile(r"(?:涉及|來自|付諸|見諸|截至|訴諸|蒞臨)(?:於|到)"), "介詞冗餘（涉及到、來自於）"),
    (re.compile(r"再次重申|重新再來|唯一僅有|各自分別|互相彼此|徹底根除|多次反覆|提前預支|過分溺愛"), "同義堆疊（再次重申）"),
    (re.compile(r"(?:非常|特別|十分|極其)太"), "程度撞絕對（非常太）"),
    (re.compile(r"因該|即然|必竟|以經|在接再厲|做為"), "同音字（因該、即然、做為）"),
    (re.compile(r"(?:跑|走|做|說|聽|寫|吃|睡|玩|笑|哭|長|變|飛|唱|講|畫|弄|搞)的(?:很|太|真|特別|非常|超)"), "補語該用「得」（做的很好）"),
]
MIXED_PUNCT = re.compile(r"[一-鿿](?:[,;:]|\.(?![.\d]))")


def frame_hits(text):
    """找出句式框架的位置；同一截字被兩種句式各算一次時，留 strict 或較長的那個。"""
    hits = []
    for name, tier, rx in FRAMES:
        for m in rx.finditer(text):
            hits.append((m.start(), m.end(), name, tier))
    hits.sort()
    kept = []
    for h in hits:
        clash = next((k for k in kept if h[0] < k[1] and k[0] < h[1]), None)
        if clash is None:
            kept.append(h)
            continue
        rank = lambda x: (2 if x[3] == "strict" else 1) * 100 + (x[1] - x[0])
        if rank(h) > rank(clash):
            kept[kept.index(clash)] = h
    return sorted(kept)


def frame_cluster(hits, width=100):
    """滑動 100 字窗口，回傳（最多幾種不同句式, 那幾種的名字）。"""
    best, names = 0, []
    for start, *_ in hits:
        win = [h for h in hits if start <= h[0] < start + width]
        kinds = sorted({h[2] for h in win})
        if len(kinds) > best:
            best, names = len(kinds), kinds
    return best, names


def mask_inline(text):
    text = re.sub(r"`[^`]*`", "〔c〕", text)
    text = re.sub(r"\$[^$]+\$", "〔m〕", text)
    return text


def drop_parens(text):
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"（[^（）]*）|\([^()]*\)", "", text)
    return text


def prose_lines(lines):
    """Yield (lineno, text) for prose lines; None marks a paragraph break."""
    in_fence = in_math = False
    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            yield i, None, False
            continue
        if s.startswith("$$"):
            if not (s.endswith("$$") and len(s) > 2):
                in_math = not in_math
            yield i, None, False
            continue
        if in_fence or in_math:
            continue
        if not s or s.startswith(("|", "#", "![", "<img", "---", "***")):
            yield i, None, False
            continue
        is_list = bool(re.match(r"^([-*+]|\d+\.)\s+", s))
        s = re.sub(r"^([-*+]|\d+\.)\s+", "", s)
        s = s.lstrip("> ")
        yield i, s, is_list


def normalize_template(sentence):
    t = mask_inline(sentence)
    t = re.sub(r"[A-Za-z][\w\-]*", "E", t)
    t = re.sub(r"[-+]?\d[\d.,%]*", "N", t)
    t = re.sub(r"\s+", "", t)
    return t


def lint(path, genre="report"):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    findings = defaultdict(list)
    paragraphs, cur = [], []
    prose_text = []
    list_lines = set()
    for no, text, is_list in prose_lines(lines):
        if text is None:
            if cur:
                paragraphs.append(cur)
            cur = []
            continue
        if is_list:
            list_lines.add(no)
        cur.append((no, text))
        prose_text.append(text)
    if cur:
        paragraphs.append(cur)

    sentences = []  # (lineno, sentence)
    for para in paragraphs:
        for no, text in para:
            masked = mask_inline(text)
            outside = drop_parens(masked)
            kv = KV.findall(outside)
            if kv:
                findings["key=value 寫在句子裡"].append((no, text, f"{len(kv)} 處"))
            if "；" in outside:
                findings["分號"].append((no, text, f"{outside.count('；')} 個"))
            for c in CLICHES:
                if c in masked:
                    findings["AI 套話"].append((no, text, c))
            for c in IDIOMS:
                if c in masked:
                    findings["花俏成語"].append((no, text, c))
            zy = [w for w in ZHIYU if w in masked]
            if zy:
                findings["中國用語（改台灣說法）"].append((no, text, "、".join(f"{w}→{ZHIYU[w]}" for w in zy)))
            for pat, label in CLICHE_PATTERNS:
                if re.search(pat, masked):
                    findings["翻譯腔句式"].append((no, text, label))
            m = SIGNPOSTS.search(masked)
            if m:
                findings["路標句"].append((no, text, m.group()))
            if genre == "report":  # 心得、信件允許一點對比與強調，避免磨平
                for pat, label in CONTRASTS:
                    if re.search(pat, masked):
                        findings["對比句型"].append((no, text, label))
            for pat, label in ENUMS:
                if re.search(pat, masked):
                    findings["預告列舉"].append((no, text, label))
            m = INTENSIFIERS.search(masked) if genre == "report" else None
            if m:
                findings["強調副詞"].append((no, text, m.group()))
            sup = SUPERLATIVE_REVEAL.findall(masked)
            if sup:
                findings["典型／最高級鋪陳＋就是"].append((no, text, "、".join(sup)))
            if genre == "report":
                nj = NOUN_JIUSHI.findall(SUPERLATIVE_REVEAL.sub("", masked))
                if nj:
                    findings["「X 就是」強調（報告改用「是」）"].append((no, text, "、".join(nj)))
            spoken = SPOKEN.findall(masked) if genre != "post" else []
            if spoken:
                findings["口語句式（書面可改「是否」等）"].append((no, text, "、".join(spoken)))
            if "「" in masked and genre != "post":
                findings["引號「」"].append((no, text, ""))
            for dm in EMDASH.finditer(masked):
                if not EMDASH_EXPLAINS.match(masked[dm.end():]):
                    findings["破折號（後面不是解釋就改逗號）"].append((no, text, preview(masked[max(0, dm.start() - 8):dm.end() + 8], 24)))
                    break
            ess = ESSENCE.findall(masked)
            if ess:
                findings["真正／本質上（加重語氣，刪掉通常不影響）"].append((no, text, "、".join(ess)))
            for tm in TRIPLE.finditer(masked):
                items = abstract_items(tm.group())
                if sum(i in ABSTRACT_NOUNS for i in items) >= 2:
                    findings["湊數並列（三個抽象詞）"].append((no, text, "、".join(items)))
                    break
            gram = [label for rx, label in GRAMMAR if rx.search(masked)]
            if gram:
                findings["書面語病"].append((no, text, "、".join(gram)))
            mp = MIXED_PUNCT.findall(masked)
            if mp:
                findings["中英標點混用"].append((no, text, " ".join(mp)))
            if genre == "report":
                fp = FIRST_PERSON.findall(masked)
                if fp:
                    findings["第一人稱（報告不用）"].append((no, text, "、".join(fp)))
                if re.search(r"？", outside):
                    findings["自問自答"].append((no, text, ""))
            # reveal colon: a short or meta clause followed by a colon mid-line
            body = re.sub(r"^\*\*[^*]{1,40}\*\*\s*(?:（[^（）]{0,40}）|\([^()]{0,40}\))?\s*[：:]?", "", masked.strip())
            body = re.sub(r"^\**(主旨|收件人|寄件人|副本|日期|Subject|To|Cc)\**\s*[：:]\**", "", body)  # email headers
            for cm in re.finditer(r"[：:]", body):
                after = body[cm.end():].strip()
                if not after or re.match(r"^\$\$", after):
                    continue  # colon introduces a list, table or formula
                before = re.split(r"[。！？]", body[:cm.start()])[-1]
                clause = drop_parens(before)
                if len(CJK.findall(clause)) <= 14 or REVEAL_WORDS.search(clause):
                    findings["冒號揭曉"].append((no, text, preview(clause.strip(), 20)))
                    break
            for s in re.split(r"(?<=[。！？])", text):
                s = s.strip()
                if len(CJK.findall(s)) >= 8:
                    sentences.append((no, s))
        # hedge density per paragraph
        ptext = mask_inline(" ".join(t for _, t in para))
        hits = [h for h in HEDGES if h in ptext]
        count = sum(ptext.count(h) for h in HEDGES)
        if count >= 2:
            findings["但書過密（一段 ≥2 個）"].append((para[0][0], ptext, "、".join(hits)))
        # frame cluster: 100 字內換用 ≥2 種不同句式（真人長評論 5.6%，AI 19.6%）
        fh = frame_hits(ptext)
        n_kinds, kinds = frame_cluster(fh)
        if n_kinds >= 2:
            label = "句式扎堆（100 字內 ≥3 種，整段重寫）" if n_kinds >= 3 else "句式扎堆（100 字內 2 種，留一處）"
            findings[label].append((para[0][0], ptext, "、".join(kinds)))
        # staccato: >=3 consecutive lines that are each one short sentence
        run = 0
        for no, text in (para if genre != "post" else []):
            one = (no not in list_lines and len(re.findall(r"[。！？]", text)) == 1
                   and text.rstrip().endswith(("。", "！", "？")))
            run = run + 1 if one else 0
            if run == 3:
                findings["電報體（連續 ≥3 行各一句）"].append((no, text, ""))

    groups = defaultdict(list)
    for no, s in sentences:
        groups[normalize_template(s)].append((no, s))
    for key, items in groups.items():
        if len(items) >= 2 and len(key) >= 12:
            lines_ = sorted({n for n, _ in items})
            findings["重複句型"].append((lines_[0], items[0][1], f"×{len(items)}，行 {', '.join(map(str, lines_))}"))

    joined = mask_inline("\n".join(prose_text))
    cjk_count = len(CJK.findall(joined))
    literary = len(LITERARY.findall(joined))
    latin_words = LATIN_WORD.findall(joined)
    hedge_total = sum(joined.count(h) for h in HEDGES)
    stats = {
        "prose_cjk_chars": cjk_count,
        "latin_words_per_100_cjk": round(100 * len(latin_words) / max(cjk_count, 1), 1),
        "hedges_per_1000_cjk": round(1000 * hedge_total / max(cjk_count, 1), 1),
        "literary_function_words_per_1000_cjk": round(1000 * literary / max(cjk_count, 1), 1),
        "top_latin_words": Counter(w.lower() for w in latin_words).most_common(12),
    }
    flag_total = sum(len(v) for v in findings.values())
    stats["flags_total"] = flag_total
    stats["flags_per_1000_cjk"] = round(1000 * flag_total / max(cjk_count, 1), 1)
    return findings, stats


def preview(text, n=70):
    text = text.replace("\n", " ")
    return text if len(text) <= n else text[:n] + "…"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true", help="print machine-readable results")
    ap.add_argument("--genre", choices=["report", "letter", "essay", "post"], default="report",
                    help="report（報告／作業，預設）、letter（信件）、essay（心得、部落格）、post（社群貼文、留言）；"
                         "報告才檢查第一人稱與自問自答，post 不查口語句式、引號與電報體")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    out = {}
    for path in args.files:
        findings, stats = lint(path, args.genre)
        out[path] = {"stats": stats, "findings": {k: [{"line": n, "text": t, "note": note} for n, t, note in v] for k, v in findings.items()}}
        if args.json:
            continue
        print(f"== {path} ==")
        print(f"prose 中文字數 {stats['prose_cjk_chars']}｜flags {stats['flags_total']}（每千字 {stats['flags_per_1000_cjk']}）"
              f"｜但書每千字 {stats['hedges_per_1000_cjk']}｜文言虛詞每千字 {stats['literary_function_words_per_1000_cjk']}"
              f"｜英文單字每百字 {stats['latin_words_per_100_cjk']}")
        for name, items in findings.items():
            print(f"\n[{name}] {len(items)}")
            for n, t, note in items[:8]:
                print(f"  L{n}: {preview(t)}" + (f"  ← {note}" if note else ""))
            if len(items) > 8:
                print(f"  …還有 {len(items) - 8} 筆")
        top = "、".join(f"{w}({c})" for w, c in stats["top_latin_words"])
        print(f"\n[正文最常出現的英文單字] {top}")
        print("  → 一般詞彙（samples、rows、part…）考慮改成中文；術語和識別字照留。\n")
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
