# -*- coding: utf-8 -*-
"""fish_judge.py 和 fish_tone.py 共用的小工具：可重現的亂數、繁簡兩用的正則、切句、保護區。"""
import re
import sys


def setup_stdio():
    """Windows 主控台預設 cp950，印簡體或特殊字會炸，統一換成 UTF-8。"""
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def read_input(path):
    if path in (None, "-"):
        return sys.stdin.read()
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


# ───────────── 可重現的亂數（跟原作同一套 mulberry32） ─────────────

def mulberry32(seed):
    a = int(seed) & 0xFFFFFFFF

    def imul(x, y):
        return (x * y) & 0xFFFFFFFF

    def rng():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = imul(t ^ (t >> 15), t | 1)
        t = (t ^ ((t + imul(t ^ (t >> 7), t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rng


# ───────────── 繁簡兩用：規則用繁體寫，自動補上簡體寫法 ─────────────

_T = ("這個說為麼們還覺發現試寫實際與對於經過應該畢從來後並僅當時點種樣嗎誰幾樂會讓給認識學讀買歡夠煩難長變飛講畫聽開關間問題結論總綜雖據進幹無離譜尷貴遠強舒靠閒鬧頭帶亮乾淨簡單複雜穩暢刪裝別賊誤導致則禮礎約將諸見訴蒞臨申徹預愛極質歸換話準確數務錯誒倆擺邊廢緊鬆話麗態愛")
_S = ("这个说为么们还觉发现试写实际与对于经过应该毕从来后并仅当时点种样吗谁几乐会让给认识学读买欢够烦难长变飞讲画听开关间问题结论总综虽据进干无离谱尴贵远强舒靠闲闹头带亮干净简单复杂稳畅删装别贼误导致则礼础约将诸见诉莅临申彻预爱极质归换话准确数务错诶俩摆边废紧松话丽态爱")
T2S = {t: s for t, s in zip(_T, _S) if t != s}


def cc(pattern, flags=0):
    """把只用繁體寫的正則展開成繁簡都認：「這」→「[這这]」，字元類裡就直接補一個字。"""
    out = []
    in_class = False
    esc = False
    for ch in pattern:
        if esc:
            out.append(ch)
            esc = False
            continue
        if ch == "\\":
            out.append(ch)
            esc = True
            continue
        if in_class:
            out.append(ch)
            if ch == "]":
                in_class = False
            elif ch in T2S:
                out.append(T2S[ch])
            continue
        if ch == "[":
            in_class = True
            out.append(ch)
            continue
        if ch in T2S:
            out.append("[" + ch + T2S[ch] + "]")
        else:
            out.append(ch)
    return re.compile("".join(out), flags)


# ───────────── 切句與保護區 ─────────────

CJK = re.compile(r"[㐀-䶿一-鿿]")
SEP_CHARS = "。！？!?…；;"
_SENT = re.compile(r"([^。！？!?…；;]*)([。！？!?…；;]*)")


def split_sentences(line):
    """切成（句子本體, 後面的標點）。開頭若是一串標點，本體為空字串，重組時不會掉字。"""
    out = []
    for m in _SENT.finditer(line):
        if m.group(0) == "":
            continue
        out.append([m.group(1), m.group(2)])
    return out


# 標題、清單、表格、引用、程式碼圍欄
STRUCTURAL = re.compile(r"^\s*(#{1,6}\s|[-*+]\s|\d+[.)]\s|\||>|```|~~~)")
# 看起來像指令或路徑的行
LOOKS_LIKE_CODE = re.compile(r"^\s*(\$|\.{0,2}/|~/|[A-Za-z]:\\|npm |pnpm |git |node |python|uv |pip )")
# 一句裡出現這些就不碰：行內程式碼、網址、路徑、命令列參數、@某人
PROTECTED_SPAN = re.compile(r"(```|~~~|`[^`]+`|https?://\S+|/[\w.-]+/[\w./-]+|[A-Za-z]:\\\S+|--[\w-]{2,}|@[A-Za-z0-9_-]+)")


def is_structural_line(line):
    return bool(STRUCTURAL.search(line) or LOOKS_LIKE_CODE.search(line))


def make_line_skipper():
    """回傳一個會記住圍欄狀態的判斷函式：這一行要不要整行跳過。"""
    state = {"fence": False}

    def skip(line):
        if re.match(r"^\s*(```|~~~)", line):
            state["fence"] = not state["fence"]
            return True
        if state["fence"]:
            return True
        if "`" in line or "http" in line:
            return True
        return is_structural_line(line)

    return skip


def body_chars(text):
    """數字數：只算非空白字元。"""
    return len(re.sub(r"\s", "", text))
