# -*- coding: utf-8 -*-
"""cost：成本账本 —— 记录、汇总与预测各技能的读取开销（零依赖）。

用法：
    # 记一笔（大读取完成后，由技能流程调用）
    python scripts/cost.py log --skill style-analyze --chars 32000 --files 8 \
        [--project <项目目录>] [--note "采样精读"]

    # 汇总出账
    python scripts/cost.py report [--project <项目目录>] [--top 10]

    # 剩余成本预测（记账历史 × 章节进度，字符量代理估算）
    python scripts/cost.py forecast --chapters-total 100 [--project <项目目录>] \
        [--chapters-done K] [--avg-chapter-chars M]

账本位置：<project>/style/cost.jsonl（每行一个 JSON 事件）。
预测口径：生成 token 走宿主账单、插件不可见，故以"读取字符 + 生成字符"为代理量，
按中文 ≈1 token/字折算并给出 0.6~1.5 倍区间（误差约 ±40%）。
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402

# 逐章重复发生的技能（其读取量按章均摊计入预测）；其余视为一次性已沉没成本
PER_CHAPTER_SKILLS = {"style-apply", "style-critique", "consistency-check"}


def ledger_path(project: Path) -> Path:
    return project / "style" / "cost.jsonl"


def log_entry(project: Path, skill: str, chars: int, files: int = 0, note: str = "") -> dict:
    entry = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "skill": skill,
        "chars": int(chars),
        "files": int(files),
        "note": note,
    }
    path = ledger_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_ledger(project: Path) -> list[dict]:
    path = ledger_path(project)
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def report(project: Path, top: int = 10) -> list[str]:
    entries = read_ledger(project)
    if not entries:
        return ["账本为空（尚未记录任何条目）"]
    totals: dict[str, dict] = {}
    for e in entries:
        t = totals.setdefault(e.get("skill", "?"), {"chars": 0, "files": 0, "events": 0})
        t["chars"] += int(e.get("chars", 0))
        t["files"] += int(e.get("files", 0))
        t["events"] += 1

    lines = [f"{'技能':<20}{'次数':>6}{'文件':>8}{'读取字符':>12}", "-" * 46]
    ranked = sorted(totals.items(), key=lambda kv: kv[1]["chars"], reverse=True)
    for skill, t in ranked[: max(1, top)]:
        lines.append(f"{skill:<20}{t['events']:>6}{t['files']:>8}{t['chars']:>12}")
    total_chars = sum(t["chars"] for t in totals.values())
    lines.append("-" * 46)
    lines.append(f"合计读取：{total_chars} 字符（约 {total_chars // 1000}k 字）")
    return lines


def forecast(project: Path, chapters_total: int, chapters_done: int | None = None,
             avg_chapter_chars: int | None = None) -> list[str]:
    ms = project / "manuscript"
    if chapters_done is None:
        chapters_done = len(list(ms.glob("*.md"))) if ms.is_dir() else 0
    if avg_chapter_chars is None:
        if chapters_done:
            sizes = []
            for p in sorted(ms.glob("*.md")):
                text, _ = splib.read_text(p)
                sizes.append(sum(1 for c in text if not c.isspace()))
            avg_chapter_chars = round(sum(sizes) / len(sizes))
        else:
            return ["无法预测：没有已完成章节且未提供 --avg-chapter-chars。",
                    "先写至少一章，或用 --avg-chapter-chars 指定单章平均字数。"]

    entries = read_ledger(project)
    recurring = [e for e in entries if e.get("skill") in PER_CHAPTER_SKILLS]
    sunk = sum(int(e.get("chars", 0)) for e in entries if e.get("skill") not in PER_CHAPTER_SKILLS)
    read_per_chapter = (round(sum(int(e.get("chars", 0)) for e in recurring) / chapters_done)
                        if chapters_done else 0)

    remaining = max(0, chapters_total - chapters_done)
    est_write = avg_chapter_chars * remaining
    est_read = read_per_chapter * remaining
    total = est_write + est_read

    lines = [
        f"进度：已完成 {chapters_done} / {chapters_total} 章，剩余 {remaining} 章",
        f"生成侧：单章平均 {avg_chapter_chars} 字 × {remaining} 章 ≈ {est_write} 字",
        f"读取侧：单章均摊 {read_per_chapter} 字（apply/critique/consistency 记账均值）"
        f"× {remaining} 章 ≈ {est_read} 字",
        f"合计 ≈ {total} 字 ≈ {int(total * 0.6):,} ~ {int(total * 1.5):,} tokens"
        f"（分词器不同会浮动）",
        f"一次性已沉没成本（建档等，不计入上式）：{sunk} 字",
        "注：生成 token 走宿主账单、插件不可见；本表为字符量代理估算，误差约 ±40%。",
    ]
    if not entries:
        lines.insert(5, "提示：账本无记录（cost.jsonl 缺失），读取侧按 0 计；让技能落账后预测更准。")
    return lines


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="成本账本")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_log = sub.add_parser("log", help="记一笔")
    p_log.add_argument("--skill", required=True)
    p_log.add_argument("--chars", type=int, required=True)
    p_log.add_argument("--files", type=int, default=0)
    p_log.add_argument("--note", default="")
    p_log.add_argument("--project", default=".", help="项目目录（默认当前目录）")

    p_rep = sub.add_parser("report", help="汇总出账")
    p_rep.add_argument("--project", default=".")
    p_rep.add_argument("--top", type=int, default=10)

    p_fc = sub.add_parser("forecast", help="剩余成本预测")
    p_fc.add_argument("--chapters-total", type=int, required=True)
    p_fc.add_argument("--project", default=".")
    p_fc.add_argument("--chapters-done", type=int, help="已完成章数（默认数 manuscript/*.md）")
    p_fc.add_argument("--avg-chapter-chars", type=int, help="单章平均字数（默认按已完成章节统计）")

    args = ap.parse_args()
    project = Path(args.project)

    if args.cmd == "log":
        e = log_entry(project, args.skill, args.chars, args.files, args.note)
        print(f"已记账：{e['skill']} +{e['chars']} 字符 → {ledger_path(project)}")
        return 0
    if args.cmd == "report":
        for line in report(project, args.top):
            print(line)
        return 0
    for line in forecast(project, args.chapters_total, args.chapters_done, args.avg_chapter_chars):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
