# -*- coding: utf-8 -*-
"""motif_count：验证 thought.md 提案 motif 的语料频率，并可写回 motif_stats 节。

用法：
    python scripts/motif_count.py <语料目录> --pack <风格包目录> [--min-rate 1.5] [--write]

读取包内 thought.md 的「motif 词表：」行，统计各 motif 在语料目录（递归收集
*.txt / *.md，适配项目 chapters/ 结构）中的出现频率（次/千字）。频率 <
--min-rate 的 motif 判为剔除——提案是模型的，数字是脚本的（防幻觉意象）。
--write 将达标词表写回词表行、重写 motif_stats 节，并按版本联动纪律 bump
pack.json patch 位。
退出码：0 成功；1 全部 motif 低于剔除线；2 用法错误。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402
from build_delta import _bump_pack_meta  # noqa: E402


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="motif 词表频率验证（思想层 advisory）")
    ap.add_argument("corpus", help="语料目录（*.txt，一个文件 = 一个样本）")
    ap.add_argument("--pack", required=True, help="风格包目录（含 thought.md）")
    ap.add_argument("--min-rate", type=float, default=1.5,
                    help="剔除线（次/千字，默认 1.5）")
    ap.add_argument("--write", action="store_true",
                    help="达标词表写回词表行 + 重写 motif_stats 节 + pack.json 版本联动")
    args = ap.parse_args()

    pack_dir = Path(args.pack)
    thought_path = pack_dir / "thought.md"
    if not thought_path.is_file():
        print(f"错误：找不到 {thought_path}", file=sys.stderr)
        return 2
    text = thought_path.read_text(encoding="utf-8")
    motifs = splib.parse_motif_list(text)
    if not motifs:
        print("错误：thought.md 缺少「motif 词表：」行", file=sys.stderr)
        return 2

    corpus_dir = Path(args.corpus)
    files = sorted(p for p in corpus_dir.rglob("*")
                   if p.is_file() and p.suffix in {".txt", ".md"})
    if not files:
        print(f"错误：{corpus_dir} 下没有 .txt/.md 语料", file=sys.stderr)
        return 2
    total = 0
    counts = dict.fromkeys(motifs, 0)
    for f in files:
        t = f.read_text(encoding="utf-8", errors="replace")
        total += len(t)
        for w in motifs:
            counts[w] += t.count(w)

    rows = sorted(((w, counts[w] / total * 1000) for w in motifs), key=lambda x: -x[1])
    keep = [w for w, r in rows if r >= args.min_rate]
    drop = [w for w, r in rows if r < args.min_rate]

    print(f"语料：{len(files)} 篇 / {total} 字｜剔除线 {args.min_rate}/千字")
    print("| motif | 次/千字 | 判定 |")
    print("|---|---|---|")
    for w, r in rows:
        print(f"| {w} | {r:.2f} | {'保留' if r >= args.min_rate else '❌ 剔除'} |")
    if drop:
        print(f"剔除（低于线）：{'、'.join(drop)}")

    if args.write:
        if not keep:
            print("全部 motif 低于剔除线，不写回", file=sys.stderr)
            return 1
        text = splib.MOTIF_LIST_RE.sub("motif 词表：" + "、".join(keep), text, count=1)
        lines = [f"## {splib.MOTIF_STATS_SECTION}", "",
                 f"> motif_count.py 产出：语料 {len(files)} 篇 {total} 字，"
                 "频率单位 = 次/千字；**advisory，不进任何判定**。", "",
                 "| motif | 次/千字 |", "|---|---|"]
        for w, r in rows:
            if r >= args.min_rate:
                lines.append(f"| {w} | {r:.2f} |")
        stats_block = "\n".join(lines) + "\n"
        m = re.search(rf"^##\s+{re.escape(splib.MOTIF_STATS_SECTION)}\s*$.*?(?=^##\s+|\Z)",
                      text, flags=re.M | re.S)
        if m:
            text = text[:m.start()] + stats_block + text[m.end():]
        else:
            text = text.rstrip("\n") + "\n\n" + stats_block
        thought_path.write_text(text, encoding="utf-8", newline="\n")
        _bump_pack_meta(pack_dir, "motif_stats 更新（motif_count.py）")
        print(f"已写回：词表 {len(keep)} 词 + motif_stats 节；pack.json 已联动升版")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
