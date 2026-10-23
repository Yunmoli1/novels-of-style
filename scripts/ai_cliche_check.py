# -*- coding: utf-8 -*-
"""ai_cliche_check：AI 腔检测（v0.9.1，创作环第四道 advisory 门）。

用法：
    python scripts/ai_cliche_check.py <文本> [--pack <风格包目录>]

词表 = scripts/ai_cliche_words.txt（三档：口头禅/句式模板/意象套话，可扩充）。
包级豁免：风格包 limits.md `## AI 腔豁免` 节逐行词——该作者本就常用的词免报。

判定（advisory，不是门；退出码 0=通过 1=偏高 2=参数错）：
    密度（次/千字，三档合计，豁免扣除）< 1.0 通过；1.0–2.0 提示；> 2.0 警告。
零第三方依赖；引擎层纪律同 fp_check（提案是模型的，数字是脚本的）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402

WORDS_PATH = Path(__file__).parent / "ai_cliche_words.txt"
TIERS = ("tier1", "tier2", "tier3")
TIER_NAMES = {"tier1": "口头禅", "tier2": "句式模板", "tier3": "意象套话"}


def load_words(extra_path: Path | None = None) -> dict[str, list[str]]:
    """解析词表文件（## tierN 分节，每行一词，# 注释忽略）。"""
    words: dict[str, list[str]] = {t: [] for t in TIERS}
    for path in ([WORDS_PATH] + ([extra_path] if extra_path else [])):
        if not path or not path.is_file():
            continue
        tier = None
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("## "):
                t = s[3:].strip().split()[0] if s[3:].strip() else ""
                tier = t if t in TIERS else None
            elif s and not s.startswith("#") and tier:
                words[tier].append(s)
    return words


def load_pack_exemptions(pack: Path | None) -> set[str]:
    """limits.md 的 `## AI 腔豁免` 节：逐行词。"""
    if not pack:
        return set()
    limits = Path(pack) / "limits.md"
    if not limits.is_file():
        return set()
    out: set[str] = set()
    in_sec = False
    for line in limits.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_sec = "AI 腔豁免" in s
        elif in_sec and s.startswith(("-", "*", "·")):
            w = s.lstrip("-*· ").strip()
            if w:
                out.add(w)
    return out


def check(text: str, words: dict[str, list[str]],
          exempt: set[str]) -> dict:
    """返回 {density, per_tier: {tier: {词: 次数}}, verdict}。"""
    total_chars = splib._clen(text) or 1
    per_tier: dict[str, dict[str, int]] = {}
    hits = 0
    for tier in TIERS:
        per_tier[tier] = {}
        for w in words.get(tier, []):
            if w in exempt:
                continue
            n = text.count(w)
            if n:
                per_tier[tier][w] = n
                hits += n
    density = round(hits / total_chars * 1000, 2)
    verdict = ("ok" if density < 1.0
               else "warn" if density > 2.0 else "notice")
    return {"density": density, "per_tier": per_tier, "hits": hits,
            "verdict": verdict, "chars": total_chars}


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="AI 腔检测（advisory）")
    ap.add_argument("input", help="待检文本（.txt/.md）")
    ap.add_argument("--pack", default=None, help="风格包目录（读 limits.md 豁免节）")
    args = ap.parse_args()
    src = Path(args.input)
    if not src.is_file():
        print(f"错误：文件不存在：{src}", file=sys.stderr)
        return 2
    text, _ = splib.read_text(src)
    if not text.strip():
        print("错误：文本为空", file=sys.stderr)
        return 2
    words = load_words()
    exempt = load_pack_exemptions(Path(args.pack) if args.pack else None)
    r = check(text, words, exempt)
    mark = {"ok": "✅", "notice": "⚠️", "warn": "❌"}[r["verdict"]]
    print(f"AI 腔检测：{mark} 密度 {r['density']} 次/千字（命中 {r['hits']} 处/"
          f"{r['chars']} 字；阈值 通过<1.0 / 提示≤2.0 / 警告>2.0）")
    if exempt:
        print(f"包级豁免：{len(exempt)} 词（limits.md·AI 腔豁免）")
    for tier in TIERS:
        if r["per_tier"][tier]:
            detail = "、".join(f"{w}×{n}" for w, n in
                               sorted(r["per_tier"][tier].items(),
                                      key=lambda kv: -kv[1]))
            print(f"  [{TIER_NAMES[tier]}] {detail}")
    return 0 if r["verdict"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
