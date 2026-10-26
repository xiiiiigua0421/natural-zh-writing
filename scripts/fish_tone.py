#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一段已經寫好的中文往「人」的方向掰一點點。台灣用語版。

用法：
    python fish_tone.py 檔案.txt                      # light，直接印出掰過的文字
    python fish_tone.py 檔案.txt --strength normal    # off | light | normal | max
    python fish_tone.py 檔案.txt --flavor cute        # 性格層：cute | abstract | shock
    python fish_tone.py 檔案.txt --json               # 多給一份統計
    echo "……" | python fish_tone.py -

依序做五件事，全部可重現（同一個 --seed 加同一段字，結果一樣）：
  1. 語尾與猶豫：正反兩遍掃描，每句只跟前後兩句「握手」。鄰居掛了尾巴，自己更容易掛；
     鄰居猶豫了，自己更容易猶豫。所以人味會局部傳開，不會整段平均撒。
  2. 語病層：修掉大部分語病，按配額（每 800 字一個不明顯的）留一點，乾淨的長文補一點手滑。
  3. 微標記：補「也／還」「好像」和加強詞（根本、超、有夠…），只挑語法上不會塌的位置。
  4. 結構腔：判成模板腔才動手，把多出來的破折號改逗號。
  5. 性格層（選用）：可愛的軟語尾、～和顏文字，抽象的網路用語尾巴，震驚的「？！」。

它只加字（語病層例外，會修掉語病），不改數字，不碰程式碼、行內程式碼、網址、路徑、表格、
標題、清單。這是一支機械的腳本：它保證不寫出病句，保證不了每一處都恰到好處，
掰完一定要自己讀一遍。

改寫自 dsh-fish-tone 與 dsh-fish-tone-flavor（MIT，Copyright (c) 2026 dsh-fish-tone contributors）。
"""
import argparse
import json
import sys

from _common import (CJK, PROTECTED_SPAN, cc, is_structural_line, make_line_skipper, mulberry32,
                     read_input, setup_stdio, split_sentences)
import grammar
from structures import mark_density, thin as thin_structures, density as structure_density
from fish_judge import assess

# ───────────── 第一步：語尾與猶豫 ─────────────

LEVELS = {
    "off": {"tail": 0, "hes_first": 0, "hes_other": 0, "filler": 0},
    "light": {"tail": 0.15, "hes_first": 0.4, "hes_other": 0.03, "filler": 0},
    "normal": {"tail": 0.32, "hes_first": 0.7, "hes_other": 0.08, "filler": 0.12},
    "max": {"tail": 0.55, "hes_first": 0.9, "hes_other": 0.15, "filler": 0.35},
}

WH_WORD = cc(r"什麼|甚麼|怎麼|怎樣|啥|哪|誰|為啥|為什麼|多少|幾|幹嘛|何時")
SUGGEST_HEAD = cc(r"^\s*(那就|就這樣|先|不如|要不|還是|乾脆|直接|我們|建議|不妨|再|快|一起)")
SUGGEST_TAIL = cc(r"(一下|看看|試試|試試看|想想|再說|加油)$")
TRAILING_EMOJI = cc(r"(\[[^\]]{1,12}\]|\([^)]{1,12}\)|（[^）]{1,12}）|[´｀ω･∇^_]{2,}|[\U0001F300-\U0001FAFF]+)$")


def is_suggestion(s):
    s = TRAILING_EMOJI.sub("", s).strip()
    return bool(SUGGEST_HEAD.search(s) or SUGGEST_TAIL.search(s))


# 台灣常用的句尾。權重是判斷給的，不是量的（原作量的是 B 站：的 > 啊 > 吧 > 呢 > 呀 > 啦 > 嘛）。
# 「吧」只掛在建議句；問「什麼、怎麼、哪、誰」的句子不掛「吧」「嘛」「喔」「欸」「耶」。
PARTICLES = [
    ("啦", 3, None),
    ("喔", 3, lambda s: not WH_WORD.search(s)),
    ("欸", 2, lambda s: not WH_WORD.search(s)),
    ("啊", 1, None),
    ("耶", 1, lambda s: not WH_WORD.search(s)),
    ("嘛", 1, lambda s: not WH_WORD.search(s)),
    ("吧", 2, lambda s: not WH_WORD.search(s) and is_suggestion(s)),
]

ADJ_TAIL = set("好對行差快慢大小多少難易累忙怪冷熱香甜苦遠近高低久早晚真假強弱貴扯順")
ADJ_TAIL_WORDS = set("麻煩 好看 好聽 好玩 好吃 好用 舒服 離譜 抽象 噁心 省事 靠譜 煩人 有趣 漂亮 乾淨 簡單 複雜 穩定 流暢 "
                     "粗糙 無聊 可愛 方便 難用 誇張 實用 划算".split())
DEGREE = cc(r"挺|很|蠻|滿|超|有夠|特別|非常|太|真|有點|夠")


def can_take_de(s):
    """「的」只掛在「程度副詞＋形容詞」的評價句後面：這家超難訂位的 ✓、音質比預期好的 ✗。"""
    if s[-1:] not in ADJ_TAIL and s[-2:] not in ADJ_TAIL_WORDS:
        return False
    if not DEGREE.search(s):
        return False
    if cc(r"比|不如|一樣").search(s):
        return False
    return "的" not in s


def tail_candidates(body):
    s = TRAILING_EMOJI.sub("", body).strip()
    out = []
    for ch, weight, ok in PARTICLES:
        if ok and not ok(s):
            continue
        out += [ch] * weight
    if can_take_de(s):
        out += ["的"] * 4
    return out


HESITATIONS = ["嗯……", "呃，", "……", "欸，"]
FILLERS = ["反正差不多啦", "大概就這樣", "說不太上來"]
ALREADY_SOFT = set("吧的啦嘛啊呀哦喔呢麼嗎吗么唄呗欸耶捏唷齁咧囉嘍")


def can_take_particle(sentence):
    s = TRAILING_EMOJI.sub("", (sentence or "").strip()).strip()
    if len(s) < 4 or not CJK.search(s) or PROTECTED_SPAN.search(s):
        return False
    last = s[-1]
    if last in ALREADY_SOFT or last in "：:，,、；;（(【[「" or last.isascii() and last.isalnum():
        return False
    return True


def apply_tone(text, strength="light", seed=7, protect=True):
    level = LEVELS.get(strength, LEVELS["light"])
    rng = mulberry32(seed)
    src = str(text or "")
    if not src.strip() or strength == "off":
        return src, _empty_stats(src, strength, seed)

    lines = src.split("\n")
    units, per_line = [], []
    in_fence = False
    for line in lines:
        if line.strip().startswith(("```", "~~~")):
            in_fence = not in_fence
            per_line.append(None)
            continue
        structural = protect and (in_fence or is_structural_line(line))
        if structural:
            per_line.append(None)
            continue
        slice_ = []
        for body, sep in split_sentences(line):
            u = {"body": body, "sep": sep, "tail": None, "hes": None, "filler": None}
            units.append(u)
            slice_.append(u)
        per_line.append(slice_)
    if not units:
        return src, _empty_stats(src, strength, seed)

    short = len(src) < 40  # 二十個字的短句，真人不會先「……」再開口
    eligible = [can_take_particle(u["body"]) for u in units]
    hes_ok = []
    for u in units:
        b = u["body"].strip()
        hes_ok.append(len(b) >= 4 and bool(CJK.search(b)) and not PROTECTED_SPAN.search(b) and not b.endswith(("：", ":")))

    # 正向：只跟前一條魚握手。鄰居已經掛了尾巴，我也更容易掛。
    prev_tail = False
    for i, u in enumerate(units):
        if not eligible[i]:
            prev_tail = False
            continue
        if rng() < level["tail"] + (0.25 if prev_tail else 0):
            cands = tail_candidates(u["body"])
            u["tail"] = cands[int(rng() * len(cands))] if cands else None
            prev_tail = bool(u["tail"])
        else:
            prev_tail = False

    # 反向：只跟後一條魚握手。握完就學會了猶豫。
    next_hes = False
    for i in range(len(units) - 1, -1, -1):
        u = units[i]
        if not hes_ok[i]:
            next_hes = False
            continue
        p = level["hes_first"] if i == 0 else level["hes_other"]
        if short:
            p *= 0.4
        if next_hes:
            p += 0.2
        if level["filler"] > 0 and len(u["body"]) >= 12 and rng() < level["filler"]:
            u["filler"] = FILLERS[int(rng() * len(FILLERS))]
        if rng() < p:
            hes = HESITATIONS[int(rng() * len(HESITATIONS))]
            bare = hes.strip("，,…")
            if not u["body"].strip().startswith(bare):  # 本來就以「嗯」開頭，再加一次像結巴
                u["hes"] = hes
                next_hes = True
            else:
                next_hes = False
        else:
            next_hes = False

    for i, slice_ in enumerate(per_line):
        if not slice_:
            continue
        rebuilt = ""
        for u in slice_:
            body = u["body"]
            if u["hes"]:
                body = u["hes"] + body.lstrip()
            if u["filler"]:
                t = body.rstrip()
                m = TRAILING_EMOJI.search(t)
                body = (t[:m.start()].rstrip("，,") + "，" + u["filler"] + m.group(0)) if m else t + "，" + u["filler"]
            if u["tail"]:
                t = body.rstrip()
                m = TRAILING_EMOJI.search(t)
                body = (t[:m.start()] + u["tail"] + m.group(0)) if m else t + u["tail"]
            rebuilt += body + u["sep"]
        lines[i] = rebuilt
    out = "\n".join(lines)
    return out, _stats(units, eligible, src, out, strength, seed)


def _empty_stats(src, strength, seed):
    return {"strength": strength, "seed": seed, "units": 0, "eligible": 0, "tails": 0, "hesitations": 0,
            "fillers": 0, "particles": {}, "inserted_chars": 0, "source_chars": len(src), "uselessness": 0}


def _stats(units, eligible, src, out, strength, seed):
    particles = {}
    for u in units:
        if u["tail"]:
            particles[u["tail"]] = particles.get(u["tail"], 0) + 1
    inserted = len(out) - len(src)
    return {"strength": strength, "seed": seed, "units": len(units), "eligible": sum(eligible),
            "tails": sum(1 for u in units if u["tail"]), "hesitations": sum(1 for u in units if u["hes"]),
            "fillers": sum(1 for u in units if u["filler"]), "particles": particles,
            "inserted_chars": inserted, "source_chars": len(src),
            # 「越沒用越像人」：插進去的字佔原文的比例
            "uselessness": round(min(1, inserted / max(1, len(src))), 3)}


# ───────────── 第三步：微標記 ─────────────

MARK_LEVELS = {"off": 0, "light": 0.3, "normal": 0.55, "max": 0.85}
PRON_VERB = cc(r"(我|你|妳|咱)(們)?(?=(?:試|用|寫|看|覺得|以為|發現|跑|玩|弄|改|刪|裝|做|算|說|想|買|學|讀|翻|遇到|踩|卡))")
TAKEN = cc(r"[也還就才都又倒]")
HEDGE_HEAD = cc(r"挺|有點|很|太|蠻|超")
OCCUPIED = cc(r"好像|估計|感覺|可能|大概|應該|搞不好|說不定")
INTENSIFIED = cc(r"根本|全都|簡直|特別|超|有夠|非常|十分|極其|爆")
NOT_PLAIN = cc(r"不(是|但|過|管|僅|同|少|斷|久|光|如|乏|及|去|要|好|然|錯|一)")
VERB_BEFORE = cc(r"[分說看聽數受弄搞用做想覺拿找算變長來去動忙夠值愛恨怕差像要敢能會]$")
QUAN_NOUN = cc(r"全(部|國|球|文|班|體|新|程|家|員|局|網|校|年|天|月|台|面|力|場|身|額|職|速|聯)")
QUAN_VERB = cc(r"全(?=[刪改看用給扔換清跑丟忘寫說吃拿做整是有在沒])")
XIANG = cc(r"(?<![好不想圖影頭偶肖雕佛畫錄鏡映])像(?=[一-鿿])(?!不|是)")
DEG_WORD = cc(r"很|非常")
BARE_ADJ = cc(r"(麻煩|彆扭|離譜|尷尬|抽象|誇張|好看|好聽|好玩|好用|難用|(?<![困災])難(?![道過怪免得])|"
              r"(?<![愉加飛趕減勤涼])快(?![要點去來樂遞取速捷門照])|慢(?!慢)|貴|(?<![餅])乾(?![淨脆杯])|累|扯|煩|怪(?![物獸]))")
# 句子已經在斷言（其實、確實、一定），再補「好像」語意會打架
ASSERTIVE = cc(r"其實|確實|真的|一定|絕對|肯定")
HAS_DEGREE = cc(r"(挺|很|太|特別|超|有夠|非常|十分|極其|有點|有些|最|更|這麼|那麼|蠻|滿|好)$")


def _clauses(line):
    out, buf = [], ""
    for ch in line:
        if ch in "，。！？；\n \t":
            out.append([buf, ch])
            buf = ""
        else:
            buf += ch
    if buf:
        out.append([buf, ""])
    return out


def insert_marks(text, level="light", seed=7, skip=None):
    """補「也／還」「好像」和加強詞，各挑語法上不會塌的位置。

    每一類都有上限，大約每 150 字一個（加強詞每 200 字一個）：真人的留白詞約 2／千字，
    一段話補兩個「好像」就從人味變成口頭禪。
    """
    rate = MARK_LEVELS.get(level, 0)
    rng = mulberry32((int(seed) ^ 0x5F356495) & 0xFFFFFFFF)
    chars = len(text)
    quota = {"relate": max(1, chars // 150), "hedge": max(1, chars // 150), "intensify": max(1, chars // 200)}
    used = {k: 0 for k in quota}
    lines = text.split("\n")
    hits = []
    for li, line in enumerate(lines):
        if skip and skip(line):
            continue
        rebuilt = ""
        for body, sep in _clauses(line):
            if len(body) >= 4 and rng() < rate:
                blocked = {k for k in quota if used[k] >= quota[k]}
                new, kind = _mark_clause(body, rng, blocked)
                if kind:
                    used[kind] += 1
                    hits.append(new[:20])
                body = new
            rebuilt += body + sep
        lines[li] = rebuilt
    return "\n".join(lines), hits


def _insert(body, at, word):
    return body[:at] + word + body[at:]


def _mark_clause(body, rng, blocked=frozenset()):
    """回傳（新子句, 補的類別）；沒補就回傳（原子句, None）。"""
    # 一、第一二人稱＋動作 → 補「也／還」：「我試過」→「我也試過」
    m = PRON_VERB.search(body)
    if m and "relate" not in blocked:
        at = m.end()
        word = "也" if rng() < 0.8 else "還"
        if TAKEN.match(body[at:at + 1] or " "):
            return body, None
        return _insert(body, at, word), "relate"
    # 二、評價副詞前面 → 補「好像」：「挺麻煩」→「好像挺麻煩」
    h = HEDGE_HEAD.search(body)
    if h and h.start() > 0 and "hedge" not in blocked and not OCCUPIED.search(body) and not ASSERTIVE.search(body):
        return _insert(body, h.start(), "好像"), "hedge"
    # 三、加強語氣。人一激動就往下加詞，AI 從頭到尾同一個音量。
    if INTENSIFIED.search(body) or "intensify" in blocked:
        return body, None
    new = _intensify(body, rng)
    return new, ("intensify" if new != body else None)


def _intensify(body, rng):
    neg = body.find("不")
    if neg > 0 and len(body) >= 6:
        dup = neg + 1 < len(body) and body[neg + 1] == body[neg - 1]           # 像不像
        in_word = bool(VERB_BEFORE.search(body[:neg])) or body[neg + 1:neg + 2] == "了"  # 分不清、受不了
        if not dup and not in_word and not NOT_PLAIN.match(body[neg:neg + 2]):
            word = "根本" if rng() < 0.75 else "完全"
            at = neg
            while at > 0 and body[at - 1] in "都也還就才又":  # 「根本都不敢」才對，「都根本不敢」是病句
                at -= 1
            return _insert(body, at, word)
    q = QUAN_VERB.search(body)
    if q and not QUAN_NOUN.match(body[q.start():q.start() + 2]):
        return _insert(body, q.start() + 1, "都")
    x = XIANG.search(body)
    if x and x.start() > 0:
        return _insert(body, x.start(), "簡直")
    d = DEG_WORD.search(body)
    if d and d.start() > 0:
        word = ["超", "有夠", "超級"][int(rng() * 3)]
        if word == "有夠" and len(body) < 10:
            word = "超"
        return body[:d.start()] + word + body[d.end():]
    a = BARE_ADJ.search(body)
    if a and a.start() > 0 and not HAS_DEGREE.search(body[:a.start()]):
        return _insert(body, a.start(), ["超", "有夠"][int(rng() * 2)])
    return body


# ───────────── 第五步：性格層 ─────────────

FLAVOR_RATES = {"low": 0.07, "normal": 0.16, "high": 0.3}
# 可愛檔要讓人一眼看出來：命中率調高，也不設上限
CUTE_RATES = {"low": 0.25, "normal": 0.4, "high": 0.6}
CUTE_TAILS = ["呀", "啦", "喔", "唷", "捏", "嘿", "嘛", "～", "喔～", "啦～"]
KAOMOJI = ["(๑•̀ㅂ•́)و✧", "(ﾉ>ω<)ﾉ", "(｡･ω･｡)", "ヽ(✿ﾟ▽ﾟ)ノ"]
# 抽象檔的網路用語尾巴，按句子的情緒挑：正面接讚嘆，負面接吐槽，看不出來就「笑死」
POS_TAILS = ["太神啦", "很可以"]
NEG_TAILS = ["好扯", "傻眼", "真的會謝", "不意外"]
NEUTRAL_TAILS = ["笑死"]
POS_CUE = cc(r"不錯|好吃|好看|好聽|厲害|讚|喜歡|推|神|好玩|舒服|順|成功|過了|修好|搞定")
NEG_CUE = cc(r"拖|尷尬|怪|離譜|扯|難|不行|爛|雷|慢|貴|累|煩|麻煩|失敗|壞|錯|卡|又")
JUDGE = cc(r"有點|有一點|挺|太|真的|感覺|覺得|難|不錯|拖|尷尬|怪|離譜|扯|普通|不行|還行|還好|超|有夠|蠻|滿")
SOFT_ENDS = ALREADY_SOFT


def _abstract_tail(body, rng):
    pool = NEG_TAILS if NEG_CUE.search(body) else POS_TAILS if POS_CUE.search(body) else NEUTRAL_TAILS
    return pool[int(rng() * len(pool))]


def flavorize(text, mode="cute", rate="low", seed=7, protect=True):
    if mode == "shock":
        return wrap_shock(text, seed, protect)
    p_base = FLAVOR_RATES.get(rate, FLAVOR_RATES["low"])
    rng = mulberry32((int(seed) ^ 0x9E3779B9) & 0xFFFFFFFF)
    lines = text.split("\n")
    hits = []
    prose_lines = []
    skip = make_line_skipper()
    for li, line in enumerate(lines):
        if protect and (skip(line) or PROTECTED_SPAN.search(line)):
            continue
        parts = split_sentences(line)
        if not parts:
            continue
        if CJK.search(line) and not line.rstrip().endswith(("：", ":")):
            prose_lines.append(li)
        eligible = []
        for i, (body, _sep) in enumerate(parts):
            t = body.rstrip()
            ok = (len(t) >= 5 and bool(CJK.search(t[-1:])) and t[-1] not in SOFT_ENDS
                  and t[-2:-1] not in SOFT_ENDS)
            if ok:
                eligible.append(i)
        targets = {}
        if mode == "abstract":
            # 梗掛在最後一個評價句上才順（「後面那段有點拖，傻眼」），掛在陳述句中間像硬塞
            judged = [i for i in eligible if JUDGE.search(parts[i][0])]
            order = list(reversed(judged or eligible))
            p = min(0.85, p_base * 2.5)  # 只挑評價句，能掛的句子少，命中率調高一點
        else:
            order, p = eligible, CUTE_RATES.get(rate, CUTE_RATES["low"])
        for i in order:
            draw = rng()
            if mode == "abstract":
                tail = _abstract_tail(parts[i][0], rng)
            else:
                tail = CUTE_TAILS[int(rng() * len(CUTE_TAILS))]
                if tail == "嘛" and WH_WORD.search(parts[i][0]):
                    continue
                # 「～」只拿來取代句號，接在問號、驚嘆號前面就怪
                if tail.endswith("～") and parts[i][1][:1] not in ("。", ""):
                    tail = tail.rstrip("～") or "啦"
            # 可愛檔、抽象檔都不設上限
            if draw < p:
                targets[i] = tail
        rebuilt = ""
        for i, (body, sep) in enumerate(parts):
            if i in targets:
                t = body.rstrip()
                joined = t + targets[i] if mode == "cute" else t + "，" + targets[i]
                if targets[i].endswith("～") and sep.startswith("。"):
                    sep = sep[1:]
                hits.append({"mode": mode, "tail": targets[i], "body": t[-14:]})
                rebuilt += joined + body[len(t):] + sep
            else:
                rebuilt += body + sep
        lines[li] = rebuilt
    if mode == "cute" and prose_lines:
        # 最後一行文字掛一個顏文字收尾，程式碼和表格不碰
        li = prose_lines[-1]
        face = KAOMOJI[int(rng() * len(KAOMOJI))]
        last = lines[li].rstrip()
        if last.endswith("。"):
            last = last[:-1]
        lines[li] = last + " " + face
        hits.append({"mode": mode, "tail": face, "body": last.strip()[-14:]})
    return "\n".join(lines), hits


def wrap_shock(text, seed=7, protect=True):
    """震驚檔：挑一句把句號換成「？！」（14.69？！）。「！？X？！」那種加碼版不自動加。"""
    rng = mulberry32((int(seed) ^ 0x85EBCA6B) & 0xFFFFFFFF)
    lines = text.split("\n")
    for li in range(len(lines) - 1, -1, -1):
        line = lines[li]
        if not line.strip() or (protect and (is_structural_line(line) or PROTECTED_SPAN.search(line))):
            continue
        parts = split_sentences(line)
        idxs = [i for i, (b, _s) in enumerate(parts) if len(b.strip()) >= 4]
        if not idxs:
            continue
        k = idxs[min(len(idxs) - 1, int(rng() * len(idxs)))]
        parts[k][1] = "？！" + parts[k][1].lstrip("。！？!?…；;")
        lines[li] = "".join(b + s for b, s in parts)
        return "\n".join(lines), [{"mode": "shock", "tail": "？！", "body": parts[k][0].strip()[-14:]}]
    return text, []


# ───────────── 串起來 ─────────────

def run(text, strength="light", seed=7, marks="light", use_grammar=True, flavor=None, flavor_rate="low"):
    out, stats = apply_tone(text, strength, seed)
    g = None
    if use_grammar and strength != "off":
        r = grammar.repair(out, seed=seed, inject=True)
        out = r["text"]
        g = {k: r[k] for k in ("found", "fixed", "kept", "injected", "budget")}
    micro = None
    if marks != "off":
        out, mh = insert_marks(out, marks, seed, make_line_skipper())
        micro = {"inserted": len(mh), "hits": mh, "density": mark_density(out)}
    # 判斷歸判斷：只有判成模板腔才動手壓，平時一兩處留給寫的人自己判
    before = assess(out)
    if before["band"] == "template":
        st = thin_structures(out, make_line_skipper())
    else:
        st = {"text": out, "thinned": 0, "over": []}
    out = st["text"]
    structures = {"thinned": st["thinned"], "over": st["over"], "judged": before["band"],
                  "density": {k: v for k, v in structure_density(out).items() if k != "rows"}}
    fl = None
    if flavor:
        out, fh = flavorize(out, flavor, flavor_rate, seed)
        fl = {"mode": flavor, "rate": flavor_rate, "hits": fh}
    return out, {"tone": stats, "grammar": g, "micro": micro, "structures": structures, "flavor": fl}


def main():
    setup_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", default="-", help="要掰的文字檔，- 代表 stdin")
    ap.add_argument("--strength", choices=list(LEVELS), default="light")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--marks", choices=list(MARK_LEVELS), default="light", help="微標記：off | light | normal | max")
    ap.add_argument("--grammar", choices=["on", "off"], default="on", help="語病層：on 修掉大部分、按配額留一點")
    ap.add_argument("--flavor", choices=["cute", "abstract", "shock"], default=None, help="性格層，預設不開")
    ap.add_argument("--flavor-rate", choices=list(FLAVOR_RATES), default="low")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    text = read_input(args.file)
    if not text.strip():
        print("沒有收到文字。")
        return 1
    out, info = run(text, args.strength, args.seed, args.marks, args.grammar == "on", args.flavor, args.flavor_rate)
    if args.json:
        print(json.dumps({"text": out, **info}, ensure_ascii=False, indent=1))
    else:
        print(out, end="" if out.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
