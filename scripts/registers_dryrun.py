# -*- coding: utf-8 -*-
"""registers_dryrun：R1 检查点 1 的方案比较——先出数字，后定方案，本脚本不写任何文件。

用法：
    python scripts/registers_dryrun.py <语料目录> --pack <风格包目录> \
        [--n-perm 1000] [--seed 20260930] [--top-n 150]

对 registers.md 的每根轴给出候选分法（k=现状主分区 + 全部 k-1 两两合并变体），
逐方案计算：
  1. 层间归因率（留一，全局 top-N 字符集——判别力检验，不依赖 n 对齐）
  2. 置换检验 p 值（标签随机重排同规模假层 N 次，固定种子可复现）
  3. 随机基线（1/k）与零假设均值
判读：p ≤ 0.05 且归因率明显高于基线 = 分区统计上真实；达线方案才允许
build_delta --registers 写入指纹（见计划书/风格分区-R1-执行规划.md 检查点 1）。
退出码：0 成功；2 用法错误。
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402


def build_matrix(space: str, named_texts: list[tuple[str, str]],
                 top_n: int) -> tuple[list[str], list[dict[str, float]]]:
    return (splib.build_metric_matrix(named_texts) if space == "metric"
            else splib._build_rate_matrix(named_texts, top_n))


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="调子分区 dry-run（R1 检查点 1）")
    ap.add_argument("corpus", help="语料目录（递归收集 *.txt/*.md）")
    ap.add_argument("--pack", required=True, help="风格包目录（含 registers.md）")
    ap.add_argument("--n-perm", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20260930)
    ap.add_argument("--top-n", type=int, default=150)
    ap.add_argument("--space", choices=["delta", "metric", "both"], default="delta",
                    help="归因空间：delta=字频向量（Burrows）；metric=句长/对话密度/"
                         "标点等度量向量（节奏轴的主张落在这里）；both=两个都跑")
    args = ap.parse_args()

    reg_path = Path(args.pack) / "registers.md"
    if not reg_path.is_file():
        print(f"错误：找不到 {reg_path}", file=sys.stderr)
        return 2
    parsed = splib.parse_registers_md(reg_path.read_text(encoding="utf-8"))
    labels, axes = parsed["labels"], parsed["axes"]
    if not labels or not axes:
        print("错误：registers.md 缺少分区定义或篇目总表", file=sys.stderr)
        return 2

    corpus = Path(args.corpus)
    files = sorted(p for p in corpus.rglob("*")
                   if p.is_file() and p.suffix in {".txt", ".md"})
    named, unmatched = splib.match_labels_to_files(files, labels)
    print(f"语料匹配 {len(named)} 篇 / 未匹配 {len(unmatched)} 篇"
          f"｜置换 {args.n_perm} 次 / 种子 {args.seed}｜全局 top-{args.top_n}")
    if unmatched:
        print("未匹配（不参与分区统计）：" + "、".join(unmatched[:8])
              + ("…" if len(unmatched) > 8 else ""))

    by_axis: dict[str, list[str]] = {}
    for reg, ax in axes.items():
        if reg in set(labels.values()):
            by_axis.setdefault(ax, []).append(reg)

    # 基准纪律：矩阵一律以全体匹配语料构建（全局基准），所有方案共用——
    # 禁止逐轴自建基准（basis shopping 会翻转显著性；fp_check 验收面对的
    # 本来就是全语料参考系）
    matrices = {"delta": splib._build_rate_matrix(named, top_n=args.top_n),
                "metric": splib.build_metric_matrix(named)}
    print("归因基准：全局（全部匹配语料统一建矩阵）")

    print()
    print("| 轴 | 分法 | 判归因篇数 | 观察归因率 | 零假设均值 | p（单侧） | 判读 |")
    print("|---|---|---|---|---|---|---|")
    spaces = [args.space] if args.space != "both" else ["delta", "metric"]
    for space in spaces:
        if space == "metric":
            print(f"\n（度量空间：句长 p25/p50/p75、段长、对话段占比、引号字占比、"
                  f"标点率、叠词率——各维全局 z-score）")
        summary: list[dict] = []
        for ax, regs in by_axis.items():
            sub = [(n, t) for n, t in named if labels[n] in regs]
            full = {n: labels[n] for n, _ in sub}
            if len(set(full.values())) < 2:
                print(f"| {ax} | （只有一个分区，跳过） | - | - | - | - | - |")
                continue
            matrix = matrices[space]

            schemes: list[tuple[str, dict[str, str]]] = [(f"k={len(regs)}（现状）", full)]
            for pair in itertools.combinations(regs, 2):
                merged = "+".join(pair)
                lab = {n: (merged if labels[n] in pair else labels[n]) for n, _ in sub}
                schemes.append((f"k={len(regs) - 1}（{merged}）", lab))

            for name_s, lab in schemes:
                r = splib.permutation_test(sub, lab, n_perm=args.n_perm,
                                           seed=args.seed, top_n=args.top_n,
                                           matrix=matrix)
                k = len(set(lab.values()))
                chance = round(1 / k, 3)
                verdict = "✅ 显著" if r["p"] <= 0.05 else "❌ 不显著"
                print(f"| {ax} | {name_s} | {r['judged']} | {r['observed']:.3f} "
                      f"| {r['null_mean']:.3f}（基线≈{chance}） | {r['p']} | {verdict} |")
                summary.append({"axis": ax, "scheme": name_s, "k": k,
                                "observed": r["observed"], "p": r["p"],
                                "null_mean": r["null_mean"], "judged": r["judged"]})
                if name_s.startswith("k=") and name_s.endswith("（现状）"):
                    for g, pg in r["per_group"].items():
                        rate = round(pg["correct"] / pg["judged"], 3) if pg["judged"] else 0.0
                        print(f"| {ax} | ↳ {g}（{pg['judged']} 篇判归因） | {pg['judged']} "
                              f"| {rate:.3f} | - | - | 分层明细 |")

    print()
    print("通过线：p ≤ 0.05 且观察归因率明显高于基线。通过轴才允许 "
          "build_delta --registers 写入指纹；未通过的轴全部退回仅路由。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
