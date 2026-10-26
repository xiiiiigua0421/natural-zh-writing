# -*- coding: utf-8 -*-
"""結構腔與微標記：句式框架表、配額、真人密度基線。

per1k 是原作拿 10 萬條 B 站評論（其中 3,000 條 ≥150 字的長評論，96 萬字）量的真人密度，
同一批句式在 AI 評論裡是這些數的 5～37 倍。
"""
import re

from _common import cc

# tier=strict 的基本只在長文裡允許出現，soft 的每幾百字允許一個
FRAMES = [
    {"id": "not-but", "name": "不是X而是Y", "tier": "strict", "per1k": 0.06,
     "re": cc(r"不是[^。！？\n]{1,24}?(?:，\s*(?:這|那|它|就)?是|而是)")},
    {"id": "most-de", "name": "最…的是", "tier": "strict", "per1k": 0.05, "re": cc(r"最[^，。\n]{1,8}的是")},
    {"id": "first-then", "name": "先…再…", "tier": "strict", "per1k": 0.01, "re": cc(r"先[^，。\n]{1,10}再")},
    {"id": "notonly", "name": "不僅…更", "tier": "strict", "per1k": 0.01, "re": cc(r"不僅[^，。\n]{1,12}(?:更|還)")},
    {"id": "de-copula", "name": "X的是Y", "tier": "soft", "per1k": 0.37, "re": cc(r"[^的，。！？\n]{1,8}的是[^，。\n]")},
    {"id": "triple", "name": "三段並列", "tier": "soft", "per1k": 0.23, "re": re.compile(r"[^，。、\n]{2,8}、[^，。、\n]{2,8}、[^，。、\n]{2,8}")},
    {"id": "emdash", "name": "破折號", "tier": "soft", "per1k": 0.22, "re": re.compile(r"——+|—"), "fix": "comma"},
    {"id": "yue", "name": "越…越", "tier": "soft", "per1k": 0.16, "re": cc(r"越[^，。\n]{1,8}越")},
    {"id": "really", "name": "真正／本質上", "tier": "soft", "per1k": 0.17, "re": cc(r"(?:真正|本質上|歸根結底)")},
    {"id": "roadmap", "name": "首先／其次／綜上", "tier": "soft", "per1k": 0.5, "re": cc(r"(?:首先|其次|綜上所述|總而言之)")},
]
BY_ID = {f["id"]: f for f in FRAMES}


def budget(chars):
    """一篇多長就允許多少個：soft 滿 200 字起碼給 1 個，strict 照真人密度算（通常是 0）。"""
    out = {}
    for f in FRAMES:
        raw = f["per1k"] * chars / 1000
        out[f["id"]] = max(1 if chars >= 200 else 0, round(raw * 2)) if f["tier"] == "soft" else round(raw)
    return out


def scan(text):
    rows = []
    for f in FRAMES:
        spans = [m.group(0) for m in f["re"].finditer(text)]
        if spans:
            rows.append({"id": f["id"], "name": f["name"], "tier": f["tier"], "count": len(spans), "spans": spans})
    return rows


def thin(text, skip=None):
    """只有判成模板腔才呼叫：超出配額的破折號改逗號，其他句式只回報、不動手。"""
    lines = text.split("\n")
    ok = [not (skip and skip(l)) for l in lines]
    chars = len("".join(l for l, o in zip(lines, ok) if o))
    if chars < 80:
        return {"text": text, "thinned": 0, "over": []}
    allow = budget(chars)
    counts = {}
    for l, o in zip(lines, ok):
        if o:
            for row in scan(l):
                counts[row["id"]] = counts.get(row["id"], 0) + row["count"]
    over, thinned = [], 0
    for fid, count in counts.items():
        allowed = allow.get(fid, 0)
        if count <= allowed:
            continue
        f = BY_ID[fid]
        over.append({"id": fid, "name": f["name"], "count": count, "allowed": allowed})
        if f.get("fix") != "comma":
            continue
        surplus = count - allowed
        for i, l in enumerate(lines):
            if not ok[i] or surplus <= 0:
                continue

            def sub(m):
                nonlocal surplus, thinned
                if surplus <= 0:
                    return m.group(0)
                surplus -= 1
                thinned += 1
                return "，"

            lines[i] = f["re"].sub(sub, l)
    return {"text": "\n".join(lines), "thinned": thinned, "over": over}


def density(text):
    chars = max(1, len(text))
    rows = scan(text)
    total = sum(r["count"] for r in rows)
    return {"chars": chars, "total": total, "per1k": round(total / chars * 1000, 2), "rows": rows}


# ───────────── 微標記：一個詞換一種關係 ─────────────
# human / ai 是原作量的每千字次數（B 站評論）。台灣版把「賊、巨」換成「超、有夠」，那兩個沒有量過。
MARKS = [
    {"ch": "也", "kind": "relate", "human": 3.4, "ai": 2.87, "why": "把對方拉進來：你也是", "re": cc(r"也")},
    {"ch": "還", "kind": "relate", "human": 3.37, "ai": 3.22, "why": "在已有的基礎上再添一層", "re": cc(r"還")},
    {"ch": "反正", "kind": "relate", "human": 0.06, "ai": 0.02, "why": "不打算解釋了，收口", "re": cc(r"反正")},
    {"ch": "好像", "kind": "hedge", "human": 0.25, "ai": 0.09, "why": "不確定就說不確定", "re": cc(r"好像")},
    # 「你應該先…」是叫人做事，不是在猜，不算留白
    {"ch": "應該", "kind": "hedge", "human": 0.41, "ai": 0.08, "why": "推斷，不是斷言", "re": cc(r"(?<![你妳您])應該")},
    {"ch": "感覺", "kind": "hedge", "human": 0.7, "ai": 0.24, "why": "標出這是感受不是結論", "re": cc(r"感覺")},
    {"ch": "可能", "kind": "hedge", "human": 0.53, "ai": 0.17, "why": "留個口子", "re": cc(r"可能")},
    {"ch": "大概", "kind": "hedge", "human": None, "ai": None, "why": "台灣常用的估計", "re": cc(r"大概")},
    {"ch": "搞不好", "kind": "hedge", "human": None, "ai": None, "why": "台灣口語的猜測", "re": cc(r"搞不好|說不定")},
    {"ch": "根本", "kind": "intensify", "human": 0.15, "ai": 0.03, "why": "把描述改成吐槽", "re": cc(r"根本")},
    {"ch": "全都", "kind": "intensify", "human": 0.04, "ai": 0.0, "why": "範圍說滿", "re": cc(r"全都")},
    {"ch": "簡直", "kind": "intensify", "human": 0.07, "ai": 0.01, "why": "誇張一步", "re": cc(r"簡直")},
    {"ch": "特別", "kind": "intensify", "human": 0.17, "ai": 0.02, "why": "程度往上抬一格", "re": cc(r"特別")},
    {"ch": "超", "kind": "intensify", "human": None, "ai": None, "why": "台灣口語的程度詞",
     "re": cc(r"超(?![過出越市商載車時額標前齡音])")},
    {"ch": "有夠", "kind": "intensify", "human": None, "ai": None, "why": "台灣口語的極端程度", "re": cc(r"有夠")},
    {"ch": "竟然", "kind": "intensify", "human": 0.07, "ai": 0.01, "why": "反預期", "re": cc(r"竟然")},
    {"ch": "到底", "kind": "intensify", "human": 0.14, "ai": 0.02, "why": "問句裡的追問", "re": cc(r"到底")},
    {"ch": "明明", "kind": "intensify", "human": 0.08, "ai": 0.02, "why": "先擺事實再反駁", "re": cc(r"明明")},
]


def mark_density(text):
    chars = max(1, len(text))
    sums = {"relate": 0, "hedge": 0, "intensify": 0}
    for m in MARKS:
        sums[m["kind"]] += len(m["re"].findall(text))
    return {
        "chars": chars,
        "relate": round(sums["relate"] / chars * 1000, 2),
        "hedge": round(sums["hedge"] / chars * 1000, 2),
        "intensify": round(sums["intensify"] / chars * 1000, 2),
        # 真人：關係約 5／千字，留白約 2／千字，加強約 0.9／千字
        "relate_line": 6.8, "hedge_line": 2.0, "intensify_line": 0.9,
    }
