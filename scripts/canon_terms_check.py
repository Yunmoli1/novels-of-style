# -*- coding: utf-8 -*-
"""canon_terms_check：二创术语保真检查（脚本侧）。

用法：
    python scripts/canon_terms_check.py --terms <canon-terms.json> <正文文件或目录...>
    python scripts/canon_terms_check.py --terms ... --per-chapter --report <报告.md> <正文...>

terms.json 格式（canon 包 / 项目 canon/canon-terms.json）：
    {
      "must":   [{"term": "艾莫号", "wrong": ["埃尔莫"], "note": "..."}, ...],
      "ban":    [{"term": "埃尔莫", "reason": "错译"}, ...],
      "thresholds": {"must_scope": "volume|chapter", "must_min_distinct": 5,
                     "concentration_advisory_per_1k": 1.0, "ban_zero": true}
    }

判定（三项）：
    1) 禁用：ban 词命中 = 0 容忍；must 术语的 wrong 变体（错译 / 错写）同罪；
    2) 覆盖：must 术语 distinct 命中数须达 must_min_distinct——
       scope=volume 按全文计，scope=chapter 逐章计；
    3) 千字浓度（must 命中 / 千字）只作 advisory，不进判定（防硬塞指标，
       见计划书 v0.5 §8——锚点是选场景的理由，不是贴标签）。
退出码：0 = 通过；1 = 禁用命中或覆盖不足；2 = 用法错误。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402


def char_count(text: str) -> int:
    return sum(1 for c in text if not c.isspace())


def count_hits(text: str, term: str) -> int:
    return len(re.findall(re.escape(term), text))


def ban_excerpts(path: Path, text: str, term: str, limit: int = 3) -> list[str]:
    """禁用命中的定位清单：文件:行号 + ≤30 字摘录。"""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if term in line:
            excerpt = line.strip()
            pos = excerpt.find(term)
            start = max(0, pos - 8)
            excerpt = ("…" if start else "") + excerpt[start:start + 30] + "…"
            out.append(f"{path.name}:{i}  {excerpt}")
            if len(out) >= limit:
                break
    return out


def check_unit(text: str, terms: dict, scope_note: str = "") -> dict:
    """对一个文本单元（全稿或单章）执行三类统计。"""
    chars = char_count(text)
    must_rows, wrong_hits, ban_hits = [], 0, []
    for m in terms["must"]:
        hits = count_hits(text, m["term"])
        wrongs = {w: count_hits(text, w) for w in m.get("wrong", [])}
        wrong_hits += sum(wrongs.values())
        must_rows.append({"term": m["term"], "hits": hits,
                          "wrong": {k: v for k, v in wrongs.items() if v},
                          "ok": hits > 0})
    for b in terms["ban"]:
        n = count_hits(text, b["term"])
        if n:
            ban_hits.append({"term": b["term"], "hits": n,
                             "reason": b.get("reason", "")})
    # wrong 变体也按禁用统计（错译即禁用），不重复计入 must 覆盖
    distinct = sum(1 for r in must_rows if r["ok"])
    total_hits = sum(r["hits"] for r in must_rows)
    conc = round(total_hits / chars * 1000, 2) if chars else 0.0
    return {"scope_note": scope_note, "chars": chars, "must_rows": must_rows,
            "distinct": distinct, "total_hits": total_hits, "conc": conc,
            "wrong_hits": wrong_hits, "ban_hits": ban_hits}


def render_report(units: list[dict], terms: dict, files: list[Path],
                  per_chapter: bool) -> tuple[str, bool]:
    """生成人读报告；返回 (markdown, 是否通过)。"""
    th = terms.get("thresholds", {})
    scope = th.get("must_scope", "volume")
    min_distinct = int(th.get("must_min_distinct", 1))
    conc_line = float(th.get("concentration_advisory_per_1k", 0.0) or 0.0)

    lines = [f"# canon_terms_check 报告", "",
             f"- 作品包：{terms.get('work', '?')}（{terms.get('version', '?')}）",
             f"- 检查对象：{', '.join(f.name for f in files[:5])}"
             f"{' 等' if len(files) > 5 else ''}（共 {len(files)} 文件）",
             f"- 模式：{'逐章' if per_chapter else '整卷'}；"
             f"must 覆盖 ≥ {min_distinct}（{scope}）；禁用 0 容忍；"
             f"浓度 advisory {conc_line}/千字", ""]

    total_ban = sum(len(u["ban_hits"]) for u in units)
    total_wrong = sum(u["wrong_hits"] for u in units)
    scope = th.get("must_scope", "volume")
    coverage_fail = [u for u in units
                     if u["distinct"] < min_distinct
                     and not (scope == "volume" and u["scope_note"] == "全卷")]

    lines.append("## must 术语覆盖（整卷汇总）")
    lines.append("")
    lines.append("| 术语 | 命中 | 状态 |")
    lines.append("|---|---|---|")
    agg: dict[str, int] = {}
    for u in units:
        for r in u["must_rows"]:
            agg[r["term"]] = agg.get(r["term"], 0) + r["hits"]
    for m in terms["must"]:
        n = agg.get(m["term"], 0)
        lines.append(f"| {m['term']} | {n} | {'✅' if n else '⚠️ 零出现'} |")
    pooled = units[-1]  # main() 末尾追加的全卷单元
    lines.append("")
    lines.append(f"- 全卷 distinct 覆盖：**{pooled['distinct']} / {len(terms['must'])}**"
                 f"（阈值 {min_distinct}）")
    lines.append(f"- 全卷 must 命中 {pooled['total_hits']} 次 / {pooled['chars']} 字"
                 f" ≈ **{pooled['conc']}/千字**"
                 + (f"（advisory 线 {conc_line}，未达仅提示）"
                    if conc_line and pooled["conc"] < conc_line else ""))

    if per_chapter:
        lines.append("")
        lines.append("## 逐章明细")
        lines.append("")
        lines.append("| 章 | 字数 | distinct | 命中 | 浓度/千字 | 禁用 |")
        lines.append("|---|---|---|---|---|---|")
        for u in units:
            lines.append(f"| {u['scope_note']} | {u['chars']} | {u['distinct']} | "
                         f"{u['total_hits']} | {u['conc']} | {len(u['ban_hits'])} |")

    lines.append("")
    lines.append("## 禁用与错写")
    lines.append("")
    if total_ban == 0 and total_wrong == 0:
        lines.append("✅ 无 ban 命中，无 must 错写变体。")
    else:
        lines.append(f"❌ ban 命中 {total_ban} 类，错写变体 {total_wrong} 次：")
        lines.append("")
        for f in files:
            text = splib.read_text(f)[0]
            for b in terms["ban"]:
                for ex in ban_excerpts(f, text, b["term"]):
                    lines.append(f"- `{b['term']}`（{b.get('reason', '')}）→ {ex}")
            for m in terms["must"]:
                for w in m.get("wrong", []):
                    for ex in ban_excerpts(f, text, w):
                        lines.append(f"- `{w}`（{m['term']} 的错写）→ {ex}")

    if coverage_fail:
        lines.append("")
        lines.append("## 覆盖不足单元")
        lines.append("")
        for u in coverage_fail:
            missing = "、".join(r["term"] for r in u["must_rows"] if not r["ok"])
            lines.append(f"- {u['scope_note'] or '全卷'}：缺 {missing}")

    ok = (total_ban == 0 and total_wrong == 0
          and pooled["distinct"] >= (min_distinct if scope == "volume" else 0)
          and (scope == "volume" or not coverage_fail))
    lines.append("")
    lines.append(f"## 结论：{'✅ 通过' if ok else '❌ 不通过'}")
    lines.append("")
    lines.append("浓度与覆盖是体检表，不是写作目标：缺口靠选场景补（委托结算、"
                 "任务分级、装备与制度语），禁止为凑数在句子里塞词。")
    return "\n".join(lines) + "\n", ok


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="二创术语保真检查")
    ap.add_argument("--terms", required=True, help="canon-terms.json 路径")
    ap.add_argument("--per-chapter", action="store_true", help="逐章统计（按文件；"
                    "单文件输入时按章节标题切分）")
    ap.add_argument("--report", help="报告输出路径（.md）")
    ap.add_argument("inputs", nargs="+", help="正文文件或目录")
    args = ap.parse_args()

    try:
        terms = splib.load_json(args.terms)
    except (OSError, json.JSONDecodeError) as e:
        print(f"错误：terms 文件不可读：{e}", file=sys.stderr)
        return 2
    if not terms.get("must"):
        print("错误：terms.json 缺 must 列表", file=sys.stderr)
        return 2

    try:
        files = splib.collect_text_files(args.inputs)
    except FileNotFoundError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 2
    if not files:
        print("错误：未找到正文文件", file=sys.stderr)
        return 2

    units: list[dict] = []
    if args.per_chapter:
        for f in files:
            text, _ = splib.read_text(f)
            if len(files) == 1:
                for title, body in splib.split_chapters(text):
                    if body:
                        units.append(check_unit(body, terms, scope_note=title or "未分章"))
            else:
                units.append(check_unit(text, terms, scope_note=f.stem))
    else:
        full = "\n".join(splib.read_text(f)[0] for f in files)
        units = [check_unit(full, terms)]
    units.append(check_unit("\n".join(splib.read_text(f)[0] for f in files), terms,
                            scope_note="全卷"))

    report, ok = render_report(units, terms, files, args.per_chapter)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(report, encoding="utf-8", newline="\n")
        print(f"报告已写入 {args.report}")
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
