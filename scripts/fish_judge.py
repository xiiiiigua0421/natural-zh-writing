#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判一段中文有沒有 AI 腔。不數總數，看每一處該不該有。

用法：
    python fish_judge.py 檔案.txt            # 印出判斷
    python fish_judge.py 檔案.txt --json     # 結構化結果
    echo "……" | python fish_judge.py -       # 從 stdin 讀

它給三樣東西：這段是什麼文體、真人在這種文體裡寫幾個句式；每一處命中的處境
（前文有沒有那個誤會、那幾個候選、那兩步動作）；以及要寫的人自己回答的問題。
它不替你決定，也不改字。比總數更準的信號是扎堆：同樣 100 字裡出現兩種以上不同句式，
真人長篇只有 5.6% 這樣，AI 評論 19.6%。

改寫自 dsh-fish-tone 的 fish_judge（MIT，Copyright (c) 2026 dsh-fish-tone contributors）。
"""
import argparse
import json
import re
import sys

from _common import cc, read_input, setup_stdio
from structures import FRAMES, mark_density
import grammar

REGISTERS = {
    "chat": {"label": "閒聊", "per1k": 0.8, "hint": "短、口語；這種長度裡框架基本是憑空多出來的"},
    "note": {"label": "隨手記", "per1k": 1.3, "hint": "不長的一段話，一兩個框架就到頂了"},
    "explain": {"label": "解釋", "per1k": 2.0, "hint": "在說明一件事；框架有事做，但也不是越多越好"},
    "argue": {"label": "論證", "per1k": 2.4, "hint": "在跟某個說法較勁；對比和糾正本來就需要框架"},
    "steps": {"label": "步驟", "per1k": 2.6, "hint": "在排動作；先…再…在這裡是真的在做事"},
}

CASUAL = cc(r"哈哈|笑死|草|emmm|嗯嗯|欸|誒|啊這|233|awsl|好耶|XD|xd|ㄏㄏ|der|齁|喔喔|啦")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")
PAREN_EMOTE = re.compile(r"[（(][^)）]{0,6}[)）]")
STEPS = cc(r"然後|接著|第一步|第二步|之後|再來|最後|先是")
ARGUE = cc(r"但是|可是|其實|問題是|然而|不過|反而|恰恰|我覺得|我認為|說句|不是這樣")
EXPLAIN = cc(r"因為|所以|也就是說|相當於|意思是|本質上|原因|意味著|換句話說")


def register_of(text):
    """猜文體。規則很土，但每條都說得出為什麼。"""
    n = len(text)
    casual = len(CASUAL.findall(text)) + len(EMOJI.findall(text)) + len(PAREN_EMOTE.findall(text))
    if casual >= 2:
        return "chat"
    if len(STEPS.findall(text)) >= 3:
        return "steps"  # 短的排動作也算步驟
    if n < 40:
        return "chat"
    if len(ARGUE.findall(text)) >= 2:
        return "argue"
    if len(EXPLAIN.findall(text)) >= 2:
        return "explain"
    if n < 150:
        return "note"
    return "explain"


def hits(text):
    out = []
    for f in FRAMES:
        for m in f["re"].finditer(text):
            out.append({"id": f["id"], "name": f["name"], "tier": f["tier"], "at": m.start(), "span": m.group(0)})
    out.sort(key=lambda h: h["at"])
    # 同一截字別被兩個句式各算一次（「最值得的是」同時像 最…的是 和 X的是Y），留更具體的那個
    rank = lambda h: (2 if h["tier"] == "strict" else 1) * 100 + len(h["span"])
    kept = []
    for h in out:
        end = h["at"] + len(h["span"])
        clash = next((k for k in kept if h["at"] < k["at"] + len(k["span"]) and k["at"] < end), None)
        if clash is None:
            kept.append(h)
        elif rank(h) > rank(clash):
            kept[kept.index(clash)] = h
    return sorted(kept, key=lambda h: h["at"])


def cluster(hs, width=100):
    best_hits = best_distinct = 0
    at = -1
    for h in hs:
        a = h["at"]
        win = [x for x in hs if a <= x["at"] < a + width]
        if len(win) > best_hits:
            best_hits, at = len(win), a
        d = len({x["id"] for x in win})
        if d > best_distinct:
            best_distinct, at = d, a
    return {"width": width, "max_hits": best_hits, "max_distinct": best_distinct, "at": at}


SENT_END = re.compile(r"[。！？!?\n]")


def sentence_at(text, at):
    s = at
    while s > 0 and not SENT_END.match(text[s - 1]):
        s -= 1
    e = at
    while e < len(text) and not SENT_END.match(text[e]):
        e += 1
    return text[s:min(len(text), e + 1)].strip()


def overlap(a, b):
    """兩串字的重複度 0～1：取字級包含率與二字組包含率的較大值。

    先拿掉兩半共同的開頭和結尾（「在追求速度／在追求穩定」只比「速度／穩定」）；
    拿掉後有一邊空了，代表一邊整個包含另一邊（慢／慢吞吞），算完全重複。
    """
    x = re.sub(r"[\s，。！？、]", "", a or "")
    y = re.sub(r"[\s，。！？、]", "", b or "")
    if not x or not y:
        return 0.0
    i = 0
    while i < min(len(x), len(y)) and x[i] == y[i]:
        i += 1
    x, y = x[i:], y[i:]
    j = 0
    while j < min(len(x), len(y)) and x[-1 - j] == y[-1 - j]:
        j += 1
    if j:
        x, y = x[:-j], y[:-j]
    if not x or not y:
        return 1.0

    def cont(sa, sb):
        return sum(1 for g in sa if g in sb) / len(sa) if sa else 0.0

    cx, cy = set(x), set(y)
    chars = max(cont(cx, cy), cont(cy, cx))
    if len(x) < 2 or len(y) < 2:
        return chars
    gx = {x[i:i + 2] for i in range(len(x) - 1)}
    gy = {y[i:i + 2] for i in range(len(y) - 1)}
    return max(chars, cont(gx, gy), cont(gy, gx))


MISCONCEPTION = cc(r"以為|覺得|聽說|很多人|別人說|常說|有人|都說|看上去|看起來|好像|不少人|總有人|認為|被當成|被說成")
NOT_BUT_PARTS = cc(r"不是([^，。！？]{1,24}?)(?:，\s*)?(?:這|那|它|就)?(?:是|而是)([^，。！？]{1,24})")
# 候選要真的被列過：頓號、和、跟、或、還有、第一第二。逗號不算，否則幾乎每句都會過關
LIST_MARKS = cc(r"、|和|跟|或|還有|一是|二是|第一|第二|比起|相較")
DASH_EXPLAINS = cc(r"^(因為|就是|也就是|意思是|指的是|說白了|相當於)")
ROADMAP = cc(r"首先|其次|綜上所述|總而言之")
ABSTRACT_NOUNS = set(
    "效率 品質 穩定 穩定性 彈性 效能 可靠 可靠性 準確 準確性 準確度 安全 安全性 便利 便利性 多元 創新 價值 體驗 "
    "成本 速度 規模 深度 廣度 質量 效果 可讀性 可維護性 擴展性 可擴展性 一致性 完整性 透明度 靈活性 互動性 實用性 "
    "易用性 公平性 穩健性 表現 能力 潛力 競爭力 溝通 合作 責任感 專業 耐心 熱情 細心 成長 挑戰 機會".split()
)


def necessity(hit, text, reg):
    """這一處有沒有事做：keep（有）／ask（看不出來，要寫的人答）／cut（大概率是擺設）。"""
    prev = text[max(0, hit["at"] - 80):hit["at"]]
    hid = hit["id"]
    if hid == "not-but":
        m = NOT_BUT_PARTS.search(text[hit["at"]:hit["at"] + 60])
        if not m:
            return {"verdict": "ask", "why": "看不出成對的兩半", "ask": "這個「不是」否定的是誰的說法？"}
        x, y = m.group(1).strip(), m.group(2).strip()
        if overlap(x, y) > 0.55:
            return {"verdict": "cut", "why": f"「{y}」只是把「{x}」換個說法，不是真的對立",
                    "ask": f"「{y}」和「{x}」是兩件事嗎？"}
        if MISCONCEPTION.search(prev):
            return {"verdict": "keep", "why": "前面確實種下了一個可能被誤解的說法，這個對比有事做"}
        return {"verdict": "ask", "why": "前面沒有人這麼想過，這個對立是自己造的",
                "ask": "前半句否定的是真有人持有的看法嗎？說得出是誰嗎？"}
    if hid == "most-de":
        near = text[max(0, hit["at"] - 120):hit["at"]]
        if len(LIST_MARKS.findall(near)) >= 2:
            return {"verdict": "keep", "why": "前面列過幾個候選，這個「最」是比出來的"}
        return {"verdict": "ask", "why": "前面沒有候選，「最」沒有可比的東西",
                "ask": "跟什麼比出來的「最」？比的東西在文中出現過嗎？"}
    if hid == "first-then":
        if reg == "steps":
            return {"verdict": "keep", "why": "這段在排動作，先後是真的"}
        if len(text) < 150:
            return {"verdict": "cut", "why": "這麼短的文字裡，「先…再…」多半只是順口", "ask": "這兩步真的分先後嗎？"}
        return {"verdict": "ask", "why": "看不出這兩步有沒有硬先後",
                "ask": "把「先」和「再」對調，意思會變嗎？不會變就是多餘的"}
    if hid == "emdash":
        after = text[hit["at"] + len(hit["span"]):hit["at"] + len(hit["span"]) + 40].strip()
        if DASH_EXPLAINS.match(after):
            return {"verdict": "keep", "why": "破折號後面是真的解釋"}
        if len(text) < 120:
            return {"verdict": "cut", "why": "短話裡的破折號基本都是換氣", "ask": "換成逗號，意思會丟嗎？"}
        return {"verdict": "ask", "why": "破折號後面不是解釋",
                "ask": "這裡需要一個停頓，還是只想讓句子顯得重一點？"}
    if hid == "roadmap":
        if len(text) < 300:
            return {"verdict": "cut", "why": "不到 300 字的文字不需要目錄", "ask": "這段真的分了好幾層嗎？"}
        if len(ROADMAP.findall(text)) >= 3:
            return {"verdict": "ask", "why": "短文裡排了一整套目錄", "ask": "這三層各自解決的是不同的問題嗎？"}
        return None
    if hid == "triple":
        parts = hit["span"].split("、")
        heads = [parts[0][-n:] for n in (4, 3, 2)] + parts[1:-1] + [parts[-1][:n] for n in (4, 3, 2)]
        abstract = sum(1 for p in set(heads) if p in ABSTRACT_NOUNS)
        if abstract >= 2 or all(len(p) <= 2 for p in parts):
            return {"verdict": "ask", "why": "並列的多半是空泛的抽象詞，像湊數",
                    "ask": "這三樣後文都有講到嗎？只留真的有講的那一兩個"}
        return None
    return None


BANDS = {
    "clean": ("像人", "密度和扎堆程度都在真人範圍裡。"),
    "slight": ("略重", "稍微多了一點，還不刺眼。"),
    "heavy": ("重", "已經看得出來了，讀的人會覺得這人在端著。"),
    "template": ("模板腔", "這段不是寫出來的，是套出來的。"),
}


def assess(text):
    src = str(text or "")
    chars = len(src)
    reg = register_of(src)
    base = REGISTERS[reg]
    hs = hits(src)
    cl = cluster(hs)
    denom = max(chars, 120)  # 短文的比率沒有統計意義，按 120 字起算
    per1k = round(len(hs) / denom * 1000, 1)
    ratio = round(per1k / base["per1k"], 1)
    expected = round(base["per1k"] * denom / 1000, 2)
    over = round(len(hs) - expected, 2)
    # 閾值取自 10 萬條真人評論的分布：「窗口裡 ≥2 種不同句式」真人 2.2%、AI 29.6%；≥3 種 真人 0.4%、AI 7.4%
    short = chars < 150
    if not hs:
        band = "clean"
    elif cl["max_distinct"] >= 3:
        band = "template"
    elif cl["max_distinct"] >= 2 or over >= 3 or (short and len(hs) >= 2):
        band = "heavy"
    elif over >= 1.5 or (short and len(hs) >= 1):
        band = "slight"
    else:
        band = "clean"

    rows = []
    for h in hs:
        v = necessity(h, src, reg) or {}
        rows.append({**h, "sentence": sentence_at(src, h["at"]), "verdict": v.get("verdict", "count"),
                     "why": v.get("why", ""), "ask": v.get("ask", "")})
    questions = [r["ask"] for r in rows if r["ask"]][:3]
    if cl["max_distinct"] >= 2:
        questions.insert(0, f"最擠的那 {cl['width']} 字裡擠了 {cl['max_distinct']} 種不同句式，它們是不是在解決同一件事？是的話留一處就夠。")

    body_len = len(re.sub(r"\s", "", src))
    g_hits = grammar.scan(src)
    g_budget = grammar.budget_for(body_len)
    return {
        "band": band, "band_label": BANDS[band][0], "band_tone": BANDS[band][1],
        "register": reg, "register_label": base["label"], "baseline": base["per1k"],
        "chars": chars, "per1k": per1k, "ratio": ratio, "expected": expected, "over": over,
        "cluster": cl, "hits": rows, "marks": mark_density(src),
        "grammar": {
            "minor": sum(1 for g in g_hits if g["severity"] == "minor"),
            "major": sum(1 for g in g_hits if g["severity"] == "major"),
            "budget": g_budget,
            "items": [{k: g[k] for k in ("note", "text", "severity")} for g in g_hits],
        },
        "questions": questions[:3],
        "blind": "這一步只認句式。換個說法把同一句再說一遍、每段都收個小結論、語氣齊得不像人，這些它看不見，得自己讀一遍。",
    }


def render(v):
    L = [f"[判斷] {v['band_label']}：{v['band_tone']}",
         f"[文體] {v['register_label']}｜真人同文體基線 {v['baseline']}／千字",
         f"[個數] 這個長度真人大概寫 {v['expected']} 個，這段寫了 {len(v['hits'])} 個（{v['per1k']}／千字，{v['ratio']} 倍）"]
    cl = v["cluster"]
    if cl["max_distinct"] >= 2:
        L.append(f"[扎堆] 最擠的 {cl['width']} 字裡有 {cl['max_distinct']} 種不同句式，這比總數更說明問題")
    else:
        L.append("[扎堆] 沒有段內的句式輪換")
    if v["hits"]:
        L.append("[逐處]")
        name = {"keep": "可以留", "ask": "要你判", "cut": "建議刪", "count": "只計數"}
        for i, h in enumerate(v["hits"], 1):
            L.append(f"  {i}. 「{h['span']}」 {h['name']} → {name[h['verdict']]}" + (f"：{h['why']}" if h["why"] else ""))
    m = v["marks"]
    L.append(f"[微標記] 關係類（也／還／反正）{m['relate']}／千字，留白類（好像／應該／感覺／可能）{m['hedge']}／千字，"
             f"加強類 {m['intensify']}／千字。真人留白類約 2／千字，一個都沒有就是句句在下斷言")
    g = v["grammar"]
    L.append(f"[語病] 不明顯 {g['minor']} 個、明顯 {g['major']} 個；這個長度允許留不明顯 {g['budget']['minor']} 個、明顯 {g['budget']['major']} 個")
    for it in g["items"][:5]:
        L.append(f"  - 「{it['text']}」{it['note']}")
    if v["questions"]:
        L.append("[要你自己答]")
        L += [f"  - {q}" for q in v["questions"]]
    L.append("[不動] 比喻、句長參差、一般被動句、名詞化：實測真人用得不比 AI 少，一律不改")
    L.append(f"[看不見] {v['blind']}")
    return "\n".join(L)


def main():
    setup_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", default="-", help="要判斷的文字檔，- 代表 stdin")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    text = read_input(args.file)
    if not text.strip():
        print("沒有收到文字。")
        return 1
    v = assess(text)
    print(json.dumps(v, ensure_ascii=False, indent=1) if args.json else render(v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
