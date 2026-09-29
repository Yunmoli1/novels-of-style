# -*- coding: utf-8 -*-
"""StylePack 共享库：编码探测、文本切分、风格指标计算、指纹比对。

仅依赖 Python 标准库。所有函数输入/输出均为 str（UTF-8）。
被 fp_extract / fp_check / ingest / validate_pack / export_pack 共用。
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------- 常量

PACK_FILES = [
    "pack.json",
    "card.md",
    "profile.md",
    "fingerprint.json",
    "exemplars.md",
    "lexicon.md",
    "limits.md",
]

PROFILE_SECTIONS = [
    "三百字精华",
    "叙事视角与人称",
    "句式与节奏",
    "词汇与用典",
    "对话风格",
    "场景与结构",
    "情感与氛围",
    "生成指导",
    "禁用清单",
]

CJK = r"\u4e00-\u9fff"
CJK_RE = re.compile(rf"[{CJK}]")

PUNCT_KEYS = ["，", "。", "？", "！", "；", "：", "、", "…", "—", "“", "”", "《", "》", "（", "）"]

DIALOGUE_STARTERS = "“\"「‘‘"

SENT_END = "。！？!?…"
_SENT_RE = re.compile(rf"[^{SENT_END}\n]*[{SENT_END}]+|[^{SENT_END}\n]+$")
_REDO_RE = re.compile(rf"([{CJK}])\1")
_FOURGRAM_RE = re.compile(rf"[{CJK}]{{4}}")

# 常见网文广告 / 站点水印行（ingest 清洗用；按行匹配，命中即丢弃）
AD_PATTERNS = [
    re.compile(p)
    for p in [
        r"^\s*(本章未完|未完待续|作者的话|PS[:：]|ps[:：])",
        r"^\s*(最新章节|本书来自|首发于|请记住本书|最快更新|正版首发)",
        r"^\s*(求收藏|求推荐|求月票|求订阅|求鲜花|求打赏)",
        r"(https?://|www\.)",
        r"(笔趣阁|顶点小说|看书网|书友群|无弹窗|手机阅读|天才一秒|一秒记住)",
        r"^\s*[-=_*·——]{3,}\s*$",
    ]
]

CHAPTER_RE = re.compile(
    r"^\s*(?:"
    r"第\s*[0-9〇零一二三四五六七八九十百千万两]+\s*[章回节卷部篇][^\n]{0,40}"
    r"|Chapter\s+\d+[^\n]{0,60}"
    r"|(?:序章|楔子|引子|尾声|后记|终章|番外)[^\n]{0,30}"
    r")\s*$",
    re.IGNORECASE,
)

# ---------------------------------------------------------------- 编码与读取


def detect_and_decode(data: bytes) -> tuple[str, str]:
    """探测编码并解码。返回 (text, encoding_name)。顺序：BOM > UTF-8 > GB18030 > Big5。"""
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16"), "utf-16"
    for enc in ("utf-8", "gb18030", "big5"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8(replace)"


def read_text(path: str | Path) -> tuple[str, str]:
    data = Path(path).read_bytes()
    return detect_and_decode(data)


# ---------------------------------------------------------------- 切分


def split_paragraphs(text: str) -> list[str]:
    """非空行即段落（中文 txt 的普遍约定）。"""
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def split_sentences(text: str) -> list[str]:
    out: list[str] = []
    for para in split_paragraphs(text):
        for m in _SENT_RE.finditer(para):
            s = m.group(0).strip()
            if s:
                out.append(s)
    return out


def _clen(s: str) -> int:
    return sum(1 for c in s if not c.isspace())


def _percentile(sorted_vals: list[int | float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, round(q * (len(sorted_vals) - 1))))
    return float(sorted_vals[idx])


def is_dialogue_para(para: str) -> bool:
    return bool(para) and para[0] in DIALOGUE_STARTERS


_QUOTE_PAIRS = re.compile(r"[“\"]([^”\"]*)[”\"]|「([^」]*)」")


def quote_chars_len(text: str) -> int:
    total = 0
    for m in _QUOTE_PAIRS.finditer(text):
        total += len(m.group(1) or m.group(2) or "")
    return total


# ---------------------------------------------------------------- 指标


def compute_metrics(text: str) -> dict:
    """计算风格指纹原始指标（嵌套结构，与 fingerprint.json 的 metrics 对齐）。"""
    paras = split_paragraphs(text)
    sents = split_sentences(text)
    sent_lens = sorted(_clen(s) for s in sents)
    para_lens = sorted(_clen(p) for p in paras)
    chars_total = _clen(text)

    def per_1k(n: int) -> float:
        return round(n / chars_total * 1000, 3) if chars_total else 0.0

    punct_counter = Counter(c for c in text if c in PUNCT_KEYS)
    cjk_chars = CJK_RE.findall(text)
    top_chars = [
        {"char": ch, "per_1k": per_1k(n)}
        for ch, n in Counter(cjk_chars).most_common(30)
    ]

    grams = Counter(g for g in _FOURGRAM_RE.findall(text) if grams_ok(g))
    fourgram_top = [g for g, n in grams.most_common(40) if n >= 2][:20]

    dialogue_paras = sum(1 for p in paras if is_dialogue_para(p))

    return {
        "chars_total": chars_total,
        "sentence_length": {
            "count": len(sents),
            "mean": round(sum(sent_lens) / len(sent_lens), 2) if sent_lens else 0.0,
            "p25": round(_percentile(sent_lens, 0.25), 1),
            "p50": round(_percentile(sent_lens, 0.50), 1),
            "p75": round(_percentile(sent_lens, 0.75), 1),
        },
        "paragraph": {
            "count": len(paras),
            "p50_len": round(_percentile(para_lens, 0.50), 1),
            "dialogue_para_ratio": round(dialogue_paras / len(paras), 3) if paras else 0.0,
        },
        "quote_char_ratio": round(quote_chars_len(text) / chars_total, 3) if chars_total else 0.0,
        "punctuation_per_1k": {ch: per_1k(n) for ch, n in sorted(punct_counter.items())},
        "reduplication_per_1k": per_1k(len(_REDO_RE.findall(text))),
        "top_chars": top_chars,
        "fourgram_top": fourgram_top,
    }


def grams_ok(g: str) -> bool:
    return True  # 占位：四字格已由正则保证全 CJK


# ---------------------------------------------------------------- 指纹比对


def iter_target_leaves(node, path=()):
    """深度优先遍历 metrics 树，产出 (path_tuple, leaf)；叶 = 含 target 的 dict。"""
    if isinstance(node, dict):
        if "target" in node:
            yield path, node
        else:
            for k, v in node.items():
                yield from iter_target_leaves(v, path + (k,))


def get_path(metrics: dict, path) -> "float | None":
    node = metrics
    for k in path:
        if not isinstance(node, dict) or k not in node:
            return None
        node = node[k]
    return node if isinstance(node, (int, float)) else None


def compare_metrics(actual: dict, fingerprint: dict) -> list[dict]:
    """逐叶比对，返回行列表。叶字段：target + tolerance_abs 或 tolerance_rel。"""
    rows = []
    for path, leaf in iter_target_leaves(fingerprint.get("metrics", {})):
        target = leaf["target"]
        act = get_path(actual, path)
        if act is None:
            rows.append({"path": ".".join(path), "target": target, "actual": None,
                         "tolerance": None, "diff": None, "ok": False, "note": "指标缺失"})
            continue
        if "tolerance_abs" in leaf:
            tol = leaf["tolerance_abs"]
            ok = abs(act - target) <= tol
        elif "tolerance_rel" in leaf:
            rel = leaf["tolerance_rel"]
            if target == 0:
                ok = act == 0
                tol = 0.0
            else:
                tol = abs(target) * rel
                ok = abs(act - target) <= tol
        else:
            ok, tol = True, None
        rows.append({"path": ".".join(path), "target": target, "actual": act,
                     "tolerance": tol, "diff": round(act - target, 3), "ok": bool(ok),
                     "note": ""})
    return rows


def all_ok(rows: list[dict]) -> bool:
    return bool(rows) and all(r["ok"] for r in rows)


def baseline_diff(rows: list[dict], baseline: dict) -> list[dict]:
    """本次 vs 基线实测指标的逐项对比（基线为某次 --save-metrics 的输出）。

    回归 = 该指标基线在容差内、本次超出容差（revise 模式的回滚依据）。
    """
    out = []
    for r in rows:
        if r["actual"] is None:
            continue
        base = get_path(baseline, tuple(r["path"].split(".")))
        if not isinstance(base, (int, float)):
            continue
        tol = r["tolerance"]
        base_ok = (abs(base - r["target"]) <= tol) if tol is not None else True
        out.append({
            "path": r["path"],
            "baseline": base,
            "actual": r["actual"],
            "delta": round(r["actual"] - base, 3),
            "regression": bool(base_ok and not r["ok"]),
        })
    return out


# ---------------------------------------------------------------- 语料清洗


def strip_ads(text: str) -> tuple[str, int]:
    """按行丢弃广告/水印行。返回 (clean_text, removed_count)。"""
    kept, removed = [], 0
    for line in text.splitlines():
        if any(p.search(line) for p in AD_PATTERNS):
            removed += 1
            continue
        kept.append(line)
    return "\n".join(kept), removed


_FENCE_RE = re.compile(r"^\s*```")
_SIG_RE = re.compile(r"^\s*[·•]\s*.{1,12}\s*[·•]\s*$")


def unwrap_text(text: str) -> tuple[str, int]:
    """合并硬换行排版（旧电子版常见）：空行分段的块内各行直接拼接；
    剔除代码围栏行与「·作者·」居中署名行。返回 (text, dropped_lines)。"""
    blocks: list[str] = []
    cur: list[str] = []
    dropped = 0
    for line in text.splitlines():
        s = line.strip().strip("\u3000").strip()
        if _FENCE_RE.match(s) or _SIG_RE.match(s):
            dropped += 1
            continue
        if s:
            cur.append(s)
        elif cur:
            blocks.append("".join(cur))
            cur = []
    if cur:
        blocks.append("".join(cur))
    return "\n\n".join(blocks), dropped


def split_chapters(text: str) -> list[tuple[str, str]]:
    """按章节标题切分；无标题则整体作为单一章节。返回 [(title, body)]。"""
    chapters: list[tuple[str | None, list[str]]] = []
    cur_title: str | None = None
    cur: list[str] = []

    def flush():
        body = "\n".join(cur).strip()
        if cur_title is not None or body:
            chapters.append((cur_title, cur.copy()))

    for line in text.splitlines():
        m = CHAPTER_RE.match(line)
        if m:
            flush()
            cur_title, cur = m.group(0).strip(), []
        else:
            cur.append(line)
    flush()

    result = []
    for i, (title, lines) in enumerate(chapters, 1):
        body = "\n".join(lines).strip()
        if not body and not title:
            continue
        if title is None:
            first = next((l.strip() for l in lines if l.strip()), "")
            title = first if 0 < len(first) <= 30 else f"第{i}部分"
            body = "\n".join(l for l in lines if l.strip() != first).strip()
        result.append((title, body))
    return result


# ---------------------------------------------------------------- Burrows Delta

def char_rates(text: str, chars: list[str]) -> dict[str, float]:
    """给定字符集合在 text 中的频率（次/千字）。"""
    total = _clen(text)
    want = set(chars)
    cnt = Counter(c for c in text if c in want)
    return {c: (cnt.get(c, 0) / total * 1000) for c in chars}


def build_delta_profile(samples: list[str], top_n: int = 150) -> dict:
    """Burrows Delta 作者档案：最高频 CJK 字的 (均值, 标准差) 表。

    samples = 语料中的各作品/章节文本；至少 2 个样本标准差才有意义，
    单样本时 std 置 1e-6（距离退化为均值偏差）。
    """
    agg: Counter = Counter()
    for s in samples:
        agg.update(c for c in s if CJK_RE.match(c))
    chars = [c for c, _ in agg.most_common(top_n)]
    rates = [char_rates(s, chars) for s in samples]
    prof: dict[str, list[float]] = {}
    for c in chars:
        vals = [r[c] for r in rates]
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals) if len(vals) > 1 else 0.0
        std = round(var ** 0.5, 4)
        prof[c] = [round(mean, 4), std if std > 0 else 1e-4]  # 仅防除零，不改既有数值
    return {"chars": prof, "n_samples": len(samples), "top_n": len(chars)}


def delta_distance(text: str, profile: dict) -> float:
    """候选文本对作者档案的 Burrows Delta 距离（各字 z-score 绝对值均值，越小越像）。"""
    chars = list(profile.get("chars", {}).keys())
    if not chars:
        return 999.0
    rates = char_rates(text, chars)
    diffs = []
    for c, (mean, std) in profile["chars"].items():
        diffs.append(abs((rates[c] - mean) / std))
    return round(sum(diffs) / len(diffs), 3) if diffs else 999.0


# ---------------------------------------------------------------- 文体分层

GENRE_DIALOGUE_BOUNDARY = 0.15   # 段首引号段占比 ≥ 此值 → narrative 信号
GENRE_QUOTE_BOUNDARY = 0.12      # 引号字占比 ≥ 此值 → narrative 信号（对话嵌入叙述段的小说靠它识别）
GENRE_CONFIDENCE_MARGIN = 0.10   # 判定信号距边界不足此值 → 置信度 medium
DELTA_MIN_CHARS = 800            # 低于此字数 Delta 不进判定（短文统计噪声）
DELTA_STABLE_CHARS = 1200        # 低于此字数 Delta 标"置信中"


def detect_genre(text: str) -> dict:
    """文体检测：双信号启发式——段首引号段占比、引号字占比，任一越界即 narrative。

    实测（luxun+zhuziqing 语料）：小说 引号字占比 19.7–28.4%，散文 0–2.1%，
    边界 0.12 居间；《背影》（含对话的散文）8.1% 落在模糊带，由置信度如实表达。
    返回 {genre, dialogue_para_ratio, quote_char_ratio, confidence}。
    """
    paras = split_paragraphs(text)
    dr = (round(sum(1 for p in paras if is_dialogue_para(p)) / len(paras), 3)
          if paras else 0.0)
    total = _clen(text)
    qr = round(quote_chars_len(text) / total, 3) if total else 0.0
    d_dist = abs(dr - GENRE_DIALOGUE_BOUNDARY)
    q_dist = abs(qr - GENRE_QUOTE_BOUNDARY)
    if dr >= GENRE_DIALOGUE_BOUNDARY or qr >= GENRE_QUOTE_BOUNDARY:
        genre = "narrative"
        if dr >= GENRE_DIALOGUE_BOUNDARY and qr >= GENRE_QUOTE_BOUNDARY:
            dist = max(d_dist, q_dist)   # 双信号同向 → 取较强者
        else:
            dist = d_dist if dr >= GENRE_DIALOGUE_BOUNDARY else q_dist
    else:
        genre = "essay"
        dist = min(d_dist, q_dist)       # 双信号均未越界 → 离边界最近的那个做主
    conf = "high" if dist >= GENRE_CONFIDENCE_MARGIN else "medium"
    # 连续值一并给出：报告可展示距边界的 margin，软化决策留给后续调参
    return {"genre": genre, "dialogue_para_ratio": dr, "quote_char_ratio": qr,
            "confidence": conf, "boundary_margin": round(dist, 3)}


def derive_thresholds(samples: list[str]) -> dict:
    """从层内各篇实测推导阈值树：target = 层内合并文本的指标值，
    tolerance_abs = 1.2 × 层内各篇对该值的最大偏离（下限按指标类别）。

    固定比例容差会被罕见指标的跨篇波动击穿（真迹挂自己层线），
    故容差必须来自数据：线 = 真迹观测包络再放宽 20%。层内各篇都没出现的
    稀疏标点不入树（合并占比 < 0.5/千字），避免「指标缺失」误杀。
    """
    pooled = compute_metrics("\n\n".join(samples))
    per_work = [compute_metrics(s) for s in samples]
    tree = {
        "sentence_length": {k: {"target": pooled["sentence_length"][k]}
                            for k in ("p25", "p50", "p75")},
        "paragraph": {
            "p50_len": {"target": pooled["paragraph"]["p50_len"]},
            "dialogue_para_ratio": {"target": pooled["paragraph"]["dialogue_para_ratio"]},
        },
        "quote_char_ratio": {"target": pooled["quote_char_ratio"]},
        "punctuation_per_1k": {ch: {"target": v}
                               for ch, v in pooled["punctuation_per_1k"].items()
                               if ch in ("…", "—", "？", "！", "；") and v >= 0.5},
        "reduplication_per_1k": {"target": pooled["reduplication_per_1k"]},
    }
    floors = {"sentence_length": 2.0, "p50_len": 2.0, "dialogue_para_ratio": 0.03,
              "quote_char_ratio": 0.03, "punctuation_per_1k": 0.3,
              "reduplication_per_1k": 0.5}
    for path, leaf in iter_target_leaves(tree):
        vals = [get_path(pm, path) for pm in per_work]
        # 频率语义下「没写」= 0（键缺失 ≠ 指标缺失），散布必须把 0 计入
        devs = [abs((0.0 if v is None else v) - leaf["target"]) for v in vals]
        dev = max(devs) if devs else 0.0
        floor = floors[path[-1] if path[0] == "paragraph" else path[0]]
        leaf["tolerance_abs"] = max(floor, round(1.2 * dev, 3))
    return tree


def fill_missing_rates(metrics: dict, tree: dict) -> dict:
    """阈值树涉及的频率/占比路径若实测缺失（字符零出现、段落无对话），补 0.0。

    「没写」在频率语义下就是 0，不该按「指标缺失」判死；只在树内路径上补，
    不引入树外噪声键。
    """
    for path, _leaf in iter_target_leaves(tree):
        if get_path(metrics, path) is None:
            node = metrics
            for k in path[:-1]:
                node = node.setdefault(k, {})
            node[path[-1]] = 0.0
    return metrics


def build_genre_layers(named_texts: list[tuple[str, str]], top_n: int = 150) -> dict:
    """按文体分层构建层档案（阈值树 + Delta 档案）。

    named_texts = [(作品名, 文本)]；返回 {"genres": {...}, "assignment": {...}}。
    """
    strata: dict[str, list[tuple[str, str]]] = {}
    assignment: dict[str, dict] = {}
    for name, text in named_texts:
        det = detect_genre(text)
        strata.setdefault(det["genre"], []).append((name, text))
        assignment[name] = det
    genres = {}
    for g, items in strata.items():
        pooled = "\n\n".join(t for _, t in items)
        m = compute_metrics(pooled)
        # n=2 的层 Delta 档案是数学退化（总体 std 下任意文本距离恒为 1.0），
        # 不入库——运行时回退混合档案作参考值
        genres[g] = {
            "samples": [n for n, _ in items],
            "chars_total": m["chars_total"],
            "metrics": derive_thresholds([t for _, t in items]),
            "delta_profile": (build_delta_profile([t for _, t in items], top_n=top_n)
                              if len(items) >= 3 else None),
        }
    return {"genres": genres, "assignment": assignment}


def leave_one_out(named_texts: list[tuple[str, str]], top_n: int = 150) -> dict:
    """层内留一：层内每篇对其余篇目所建档案算 Delta，最差篇即该层及格线。

    绝不跨层（跨层底线会把散文线拉到小说的高度）。层内 n<3 时留一档案
    退化为单样本（std 无意义），delta_max 置 None 并注明——线待语料扩充。
    返回 {genre: {n, delta_loo: [...], delta_max, delta_p50}}。
    """
    strata: dict[str, list[tuple[str, str]]] = {}
    for name, text in named_texts:
        g = detect_genre(text)["genre"]
        strata.setdefault(g, []).append((name, text))
    out: dict[str, dict] = {}
    for g, items in strata.items():
        rows = []
        for i, (name, text) in enumerate(items):
            others = [t for j, (_, t) in enumerate(items) if j != i]
            if len(others) < 2:
                rows.append({"work": name, "delta": None,
                             "note": f"留一档案仅 {len(others)} 样本，距离不可标定"})
                continue
            prof = build_delta_profile(others, top_n=top_n)
            rows.append({"work": name, "delta": delta_distance(text, prof)})
        deltas = sorted(r["delta"] for r in rows if r["delta"] is not None)
        out[g] = {
            "n": len(items),
            "delta_loo": rows,
            "delta_max": deltas[-1] if deltas else None,
            "delta_p50": deltas[len(deltas) // 2] if deltas else None,
        }
        if not deltas:
            out[g]["note"] = "层内 n<3：留一 Delta 线不可标定，待语料扩充后重算"
    return out


def layered_check(text: str, fingerprint: dict, genre: str | None = None,
                  delta_max_override: float | None = None) -> dict:
    """统一验收路径（fp_check CLI 与 MCP fp.check 共用）。

    1) 文体判定（auto 或 --genre 指定）；2) 选对应层阈值（无层降级混合 + 明示）；
    3) 逐项比对；4) Delta 及格线：显式 --delta-max > 层内留一 delta_max（n≥3）；
    短文（<800 字）Delta 只作参考不进判定；800–1200 字进判定但标"置信中"。
    """
    det = detect_genre(text)
    notes: list[str] = []
    genres = fingerprint.get("genres", {})
    g = det["genre"] if genre in (None, "auto") else genre
    if not genres or g == "all":
        tree = fingerprint.get("metrics", {})
        layer_used = "all(混合)"
        prof = fingerprint.get("delta_profile")
        sc = None
    elif g in genres:
        tree = genres[g]["metrics"]
        layer_used = g
        prof = genres[g].get("delta_profile") or fingerprint.get("delta_profile")
        sc = fingerprint.get("self_check", {}).get(g)
    else:
        tree = fingerprint.get("metrics", {})
        layer_used = f"all(混合，包无 {g} 层)"
        prof = fingerprint.get("delta_profile")
        sc = None
        notes.append(f"包无 {g} 层指纹，降级混合阈值")

    metrics = compute_metrics(text)
    fill_missing_rates(metrics, tree)
    # compare_metrics(实测, 指纹形)：第二参才是阈值树
    rows = compare_metrics(metrics, {"metrics": tree})

    chars = metrics["chars_total"]
    delta = None
    line = None
    counted = False
    dnote = ""
    if prof is not None:
        delta = delta_distance(text, prof)
    if chars < DELTA_MIN_CHARS:
        dnote = f"短文（{chars} 字 < {DELTA_MIN_CHARS}），Delta 仅为参考不进判定"
    elif prof is None:
        dnote = "包无 delta_profile，Delta 不可用"
    elif delta_max_override is not None:
        line, counted = delta_max_override, True
        dnote = "及格线=命令行显式指定"
    elif sc and sc.get("delta_max") is not None:
        line, counted = sc["delta_max"], True
        dnote = f"及格线=层内真迹留一最差篇（{sc['n']} 篇）"
    elif sc is not None:
        dnote = f"该层 n={sc.get('n')}（<3），留一 Delta 线待语料扩充，仅参考"
    else:
        dnote = "该层无 self_check，Delta 仅参考"
    if counted and chars < DELTA_STABLE_CHARS:
        dnote += "；字数偏少，置信中"
    if counted and delta is not None:
        if line and delta > 0.8 * line:
            dnote += "；已接近及格线（>80%），仅供判读留意，不影响判定"
        rows.append({"path": "delta.distance", "target": line, "actual": delta,
                     "tolerance": line, "diff": round(delta - line, 3),
                     "ok": delta <= line, "note": dnote})

    return {
        "genre": det, "layer_used": layer_used, "notes": notes,
        "chars_total": chars, "rows": rows, "metrics": metrics,
        "delta": delta, "delta_line": line, "delta_counted": counted,
        "delta_note": dnote,
        "ok": all_ok(rows),
    }


# ---------------------------------------------------------------- IO


def force_utf8_stdio() -> None:
    """入口统一调用：把标准流重配为 UTF-8。

    Windows 默认 cp936 控制台/管道下，emoji 报告与 ensure_ascii=False 的 JSON
    载荷会 UnicodeEncodeError 或被按本地代码页污染。reconfigure 仅 3.7+ 的
    TextIOWrapper 提供，流被宿主替换时静默跳过；errors 容错保输出不断流。
    """
    for stream, err in ((sys.stdout, "replace"), (sys.stderr, "replace"),
                        (sys.stdin, "strict")):
        try:
            stream.reconfigure(encoding="utf-8", errors=err)
        except (AttributeError, ValueError, OSError):
            pass


def load_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(obj, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def collect_text_files(inputs: list[str | Path]) -> list[Path]:
    """把文件/目录参数展开为文本文件列表（.txt/.md，按文件名排序）。"""
    files: list[Path] = []
    for inp in inputs:
        p = Path(inp)
        if p.is_dir():
            files.extend(sorted(q for q in p.rglob("*") if q.suffix.lower() in (".txt", ".md")))
        elif p.is_file():
            files.append(p)
        else:
            raise FileNotFoundError(f"路径不存在：{p}")
    return files
