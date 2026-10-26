# -*- coding: utf-8 -*-
"""語病層：掃掉大部分，按配額留一點。台灣用語版。

語病分五台機器：
  typo   輸入法手滑：同音字、補語「得」寫成「的」
  speed  手速重複：同一個字或標點連打兩次
  tone   語氣加載：語氣詞、副詞疊用
  format 格式混用：中文裡夾半形標點
  formal 書面語病：成分殘缺、句式雜糅、成分贅餘（學校教的那套）

配額來自原作量的 B 站評論：真正算語病的大約每千字 1.2 個，也就是每 800 字一個；
書面語病在真人短評裡幾乎是零。所以 300 字以內一個都不留。
台灣版拿掉了「慢慢的說 → 慢慢地說」這條：台灣書面語也常用「的」當副詞詞尾，不算錯。
"""
import re

from _common import cc, mulberry32

FRAMES = {
    "typo": "輸入法手滑",
    "speed": "手速重複",
    "tone": "語氣加載",
    "format": "格式混用",
    "formal": "書面語病",
}

HOMOPHONES = {"因該": "應該", "即然": "既然", "必竟": "畢竟", "以經": "已經", "做為": "作為", "在接再厲": "再接再厲"}
REDUNDANT = {
    "再次重申": "重申", "重新再來": "再來", "唯一僅有": "唯一", "各自分別": "各自", "互相彼此": "互相",
    "徹底根除": "根除", "多次反覆": "多次", "提前預支": "預支", "過分溺愛": "溺愛",
}
CN_PUNCT = {",": "，", ";": "；", ":": "：", ".": "。"}


def _rule(rid, frame, severity, note, pattern, fix, run_aware=False):
    return {"id": rid, "frame": frame, "severity": severity, "note": note,
            "re": cc(pattern), "fix": fix, "run_aware": run_aware}


RULES = [
    _rule("typo-homophone", "typo", "minor", "同音字上屏",
          r"(因該|即然|必竟|以經|做為|在接再厲)", lambda m: HOMOPHONES.get(m.group(1), m.group(1))),
    _rule("de-de", "typo", "minor", "補語前面該用「得」",
          r"(跑|走|做|說|看|聽|寫|吃|睡|玩|笑|哭|長|變|飛|唱|講|畫|弄|搞|整|來|去)的(很|太|真|特別|好|快|慢)",
          lambda m: m.group(1) + "得" + m.group(2)),
    _rule("dup-adverb", "tone", "minor", "副詞重複",
          r"(很|非常|特別|挺|太|超級|十分)\1+", lambda m: m.group(1)),
    _rule("dup-punct", "speed", "major", "標點連打（。。／，，）",
          r"([，。；：])\1+", lambda m: m.group(1)),
    _rule("dup-func", "speed", "minor", "虛詞或代詞連打",
          r"(我|你|他|她|它|這|那|是|不|就|都|也|很|太|在|有|和|的|了)\1(?!\1)", lambda m: m.group(1), run_aware=True),
    _rule("dup-particle", "tone", "minor", "語氣詞疊用",
          r"([的吧啦嘛啊呀哦喔了呢欸耶])\1(?!\1|隊)", lambda m: m.group(1), run_aware=True),
    _rule("mixed-punct", "format", "minor", "中文裡夾了半形標點",
          r"([一-鿿])([,;:]|\.(?![.\d]))", lambda m: m.group(1) + CN_PUNCT.get(m.group(2), m.group(2))),
    _rule("through-make", "formal", "major", "「透過…使…」吃掉主詞",
          r"(透過|通過|經過|由於)([^，。！？\n]{2,18}?)使(得)?", lambda m: m.group(2) + "使" + (m.group(3) or "")),
    _rule("double-negative", "formal", "major", "「防止…不…」把意思說反",
          r"(防止|避免|杜絕|切忌|以免|以防)([^，。！？的\n]{0,8}?)不(?!小心)(再|會|要|能)",
          lambda m: m.group(1) + m.group(2) + m.group(3)),
    _rule("measure-people", "formal", "major", "量詞和「們」打架",
          r"一(個|位|名)([^，。兒\n]{0,3}?)們", lambda m: "這些" + m.group(2)),
    _rule("measure-plural", "formal", "minor", "「很多／幾個」已經是複數，不用再加「們」",
          r"(很多|好多|幾個|數個|一群)([^，。\n]{0,4}?)們", lambda m: m.group(1) + m.group(2)),
    _rule("reason-blend", "formal", "major", "「原因是…造成的」句式雜糅",
          r"(原因是|根源是|是因為)([^，。！？\n]{1,24}?)(造成的|所導致|引起的)", lambda m: m.group(1) + m.group(2)),
    _rule("blend-basis", "formal", "major", "「本著…為原則」句式雜糅",
          r"(本著|根據|按照|基於)([^，。\n]{1,16}?)(為原則|為宗旨|為基礎)", lambda m: "以" + m.group(2) + m.group(3)),
    _rule("redundant-approx", "formal", "minor", "「約…左右」同義反覆",
          r"(大約|約|將近|差不多)([^，。\n]{0,8}?)(左右|上下)", lambda m: m.group(1) + m.group(2)),
    _rule("redundant-prep", "formal", "minor", "介詞冗餘（涉及到／來自於）",
          r"(涉及|來自|付諸|見諸|截至|訴諸|蒞臨)(於|到)", lambda m: m.group(1)),
    _rule("redundant-synonym", "formal", "minor", "同義堆疊（再次重申／徹底根除）",
          r"(再次重申|重新再來|唯一僅有|各自分別|互相彼此|徹底根除|多次反覆|提前預支|過分溺愛)",
          lambda m: REDUNDANT.get(m.group(1), m.group(1))),
    _rule("degree-absolute", "formal", "minor", "程度副詞撞上「太」（非常太）",
          r"(非常|特別|十分|極其)太", lambda m: "太"),
]

PROTECT = [
    re.compile(r"```[\s\S]*?```"),
    re.compile(r"~~~[\s\S]*?~~~"),
    re.compile(r"`[^`\n]+`"),
    re.compile(r"https?://[^\s)>\]]+"),
    re.compile(r"(?:^|\s)(?:\.{0,2}/|~/)[\w./-]+"),
    re.compile(r"[A-Za-z]:\\\S+"),
    re.compile(r"--[a-z][\w-]*"),
    re.compile(r"[ \t]*(?:#{1,6}[ \t]|\|)[^\n]*"),
]


def protected_ranges(src):
    out = []
    for rx in PROTECT:
        for m in rx.finditer(src):
            if m.group(0):
                out.append((m.start(), m.end()))
    return out


def scan(text, protect=True):
    src = str(text or "")
    ranges = protected_ranges(src) if protect else []
    hits = []
    for rule in RULES:
        for m in rule["re"].finditer(src):
            if not m.group(0):
                continue
            a, b = m.start(), m.end()
            if any(a < e and b > s for s, e in ranges):
                continue
            # 三次以上（我我我、不不不）是情緒，只有剛好兩次才算手滑
            if rule["run_aware"] and a > 0 and src[a - 1] == m.group(0)[0]:
                continue
            hits.append({"rule": rule["id"], "frame": rule["frame"], "severity": rule["severity"],
                         "note": rule["note"], "start": a, "end": b, "text": m.group(0),
                         "fixed": rule["fix"](m)})
    hits.sort(key=lambda h: (h["start"], 0 if h["severity"] == "major" else 1))
    out, last_end = [], -1
    for h in hits:
        if h["start"] < last_end:
            continue
        out.append(h)
        last_end = max(last_end, h["end"])
    return out


def frame_stats(hits):
    out = {k: 0 for k in FRAMES}
    for h in hits:
        out[h["frame"]] = out.get(h["frame"], 0) + 1
    return out


def budget_for(chars):
    """這段字數允許留幾個語病。300 字以內 0；之後每 800 字一個不明顯的、每 2000 字一個明顯的。"""
    n = max(0, int(chars))
    return {"minor": max(1, n // 800) if n >= 300 else 0, "major": n // 2000}


def count_sentences(text):
    parts = [p for p in re.split(r"[。！？…]+", str(text or "")) if p.strip()]
    return max(1, len(parts))


def _sentence_index(text, pos):
    return sum(1 for ch in text[:pos] if ch in "。！？…")


def repair(text, seed=7, keep_rate=0.1, inject=False, protect=True):
    """修掉大部分語病，按配額留幾個；inject=True 時，乾淨的稿子會補一點手滑。"""
    rng = mulberry32((int(seed) ^ 0x5F3759DF) & 0xFFFFFFFF)
    src = str(text or "")
    ranges = protected_ranges(src) if protect else []
    found = scan(src, protect)
    budget = budget_for(len(re.sub(r"\s", "", src)))
    max_dirty = max(1, int(count_sentences(src) * 0.4))  # 最多四成的句子帶毛病

    wanted = []
    for h in found:
        p = keep_rate * 0.4 if h["severity"] == "major" else keep_rate
        if rng() < p:
            wanted.append(h)
    wanted.sort(key=lambda h: 0 if h["severity"] == "minor" else 1)

    kept, dirty = [], set()
    kept_minor = kept_major = 0
    for h in wanted:
        s_idx = _sentence_index(src, h["start"])
        if h["severity"] == "major":
            if kept_major >= budget["major"]:
                continue
            kept_major += 1
        else:
            if kept_minor >= budget["minor"]:
                continue
            kept_minor += 1
        if sum(1 for k in kept if _sentence_index(src, k["start"]) == s_idx) >= 2:
            continue
        if s_idx not in dirty and len(dirty) >= max_dirty:
            continue
        dirty.add(s_idx)
        kept.append(h)

    keep_keys = {(k["start"], k["end"]) for k in kept}
    fixed = 0
    for h in reversed(found):
        if (h["start"], h["end"]) in keep_keys:
            continue
        if h["fixed"] != h["text"]:
            src = src[:h["start"]] + h["fixed"] + src[h["end"]:]
            fixed += 1

    injected = 0
    if inject and budget["minor"] > 0:
        want = min(3, max(0, budget["minor"] - len(kept)))
        if want > 0:
            src, injected = _inject_slips(src, rng, want, protected_ranges(src) if protect else [])

    return {
        "text": src,
        "found": len(found),
        "fixed": fixed,
        "kept": [{k: h[k] for k in ("rule", "frame", "severity", "note", "text")} for h in kept],
        "injected": injected,
        "budget": budget,
        "frames": frame_stats(found),
    }


def _inject_slips(text, rng, count, ranges):
    """補最小、最像手滑的毛病：語氣詞疊用、虛詞連打、句號連打（最扎眼，權重壓低）。"""
    def usable(at):
        return at > 6 and not any(s <= at < e for s, e in ranges)

    cands = []

    def add(rx, weight):
        for m in rx.finditer(text):
            at = m.end(1)
            if usable(at):
                cands.append({"at": at, "ch": m.group(1), "weight": weight})

    add(cc(r"([我你他她這那])(?=[一-鿿])"), 2)
    add(cc(r"([的吧啦嘛啊呀喔了呢欸耶])(?=[，。！？…\s]|$)"), 3)
    add(re.compile(r"(。)(?=\n|$)", re.M), 1)
    if not cands:
        return text, 0

    pool, picked = cands[:], []
    while len(picked) < count and pool:
        total = sum(c["weight"] for c in pool)
        r = rng() * total
        idx = 0
        for idx, c in enumerate(pool):
            r -= c["weight"]
            if r <= 0:
                break
        pick = pool.pop(min(idx, len(pool) - 1))
        if any(abs(p["at"] - pick["at"]) < 40 for p in picked):
            continue
        picked.append(pick)
    for p in sorted(picked, key=lambda x: -x["at"]):
        text = text[:p["at"]] + p["ch"] + text[p["at"]:]
    return text, len(picked)
