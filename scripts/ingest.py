# -*- coding: utf-8 -*-
"""ingest：语料清洗入库 —— 编码转换、去广告、章节切分、按章落盘、统计缓存。

用法：
    python scripts/ingest.py --input <原始txt> --out <语料根目录>/<作者> --work <作品名>
                             [--source-url URL] [--source-date 2026-09-28]
                             [--notes 备注] [--no-strip-ads]

产物：
    <out>/<work>/chapters/001-<标题>.md   按章正文（UTF-8，首行为 # 标题）
    <out>/<work>/provenance.json          来源记录（URL、抓取日期、原编码等）
    <out>/<work>/stats.json               全作统计缓存 + 逐章指标（增量分析的基础）

重复运行同一 --out/--work 会覆盖重建该作品目录（增量新增作品用新 --work 即可）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402


def slugify(title: str, fallback: str) -> str:
    keep = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", title.strip())
    keep = keep.strip("-")
    return keep[:24] if keep else fallback


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="语料清洗入库")
    ap.add_argument("--input", required=True, help="原始 txt 文件（任意常见编码）")
    ap.add_argument("--out", required=True, help="输出作者目录，如 corpus/luxun")
    ap.add_argument("--work", required=True, help="作品名，如 故乡")
    ap.add_argument("--source-url", default="")
    ap.add_argument("--source-date", default="")
    ap.add_argument("--notes", default="")
    ap.add_argument("--no-strip-ads", action="store_true", help="跳过去广告")
    ap.add_argument("--unwrap", action="store_true",
                    help="合并硬换行排版（旧电子版常见），剔除代码围栏与署名行")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.is_file():
        print(f"错误：输入文件不存在：{src}", file=sys.stderr)
        return 2

    raw_text, enc = splib.read_text(src)
    removed = 0
    if args.unwrap:
        raw_text, unwrapped = splib.unwrap_text(raw_text)
        print(f"硬换行合并：剔除 {unwrapped} 行（围栏/署名）")
    if not args.no_strip_ads:
        raw_text, removed = splib.strip_ads(raw_text)

    chapters = splib.split_chapters(raw_text)
    if not chapters:
        print("错误：清洗后没有可用正文", file=sys.stderr)
        return 1

    work_dir = Path(args.out) / args.work
    ch_dir = work_dir / "chapters"
    ch_dir.mkdir(parents=True, exist_ok=True)

    chapter_metrics = []
    total_chars = 0
    for i, (title, body) in enumerate(chapters, 1):
        fname = f"{i:03d}-{slugify(title, f'ch{i}')}.md"
        (ch_dir / fname).write_text(f"# {title}\n\n{body}\n", encoding="utf-8", newline="\n")
        m = splib.compute_metrics(body)
        chapter_metrics.append({"file": fname, "title": title, "chars": m["chars_total"],
                                "metrics": m})
        total_chars += m["chars_total"]

    splib.dump_json({
        "work": args.work,
        "source_url": args.source_url,
        "fetched_at": args.source_date,
        "source_file": str(src),
        "original_encoding": enc,
        "ads_removed_lines": removed,
        "notes": args.notes,
        "chapter_count": len(chapters),
        "total_chars": total_chars,
        "ingested_at": "runtime",
    }, work_dir / "provenance.json")

    full_metrics = splib.compute_metrics("\n\n".join(body for _, body in chapters))
    splib.dump_json({"work": args.work, "total_chars": total_chars,
                     "chapters": chapter_metrics, "overall": full_metrics},
                    work_dir / "stats.json")

    print(f"入库完成：{args.work}")
    print(f"  原编码：{enc}；去广告行：{removed}；章节数：{len(chapters)}；总字符：{total_chars}")
    print(f"  目录：{work_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
