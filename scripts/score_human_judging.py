# -*- coding: utf-8 -*-
"""score_human_judging：人工判读结果计分——同源偏差的直接度量（r4 P0-1 收口）。

用法：
    python scripts/score_human_judging.py <判读导出.json> [--answers <答案卷.json>]

判读导出 = 判读台（web/site/judging/）"导出判读结果"按钮下载的 JSON：
    {"exported_at": ..., "rounds": [{"id": 1, "choice": "甲|乙|都不像", ...}]}

答案卷 = evals/human_judging_answers.json（**不入 git**，本机由
migrate_human_judging.py 生成；缺失时本脚本给出补救指引）。

输出两个一致率：
  ① 辨认带包臂命中率——你能否认出哪段装载了风格包；
  ② 与子代理判官一致率——同源偏差的直接度量。
判读纪律照答案卷：高→子代理判官可继续用；低→判官必须换模型或换人。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANSWERS = ROOT / "evals" / "human_judging_answers.json"


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="人工判读计分（同源偏差度量）")
    ap.add_argument("results", help="判读台导出的 JSON")
    ap.add_argument("--answers", default=str(DEFAULT_ANSWERS))
    args = ap.parse_args()

    rp = Path(args.results)
    if not rp.is_file():
        print(f"错误：判读结果文件不存在：{rp}", file=sys.stderr)
        return 2
    apath = Path(args.answers)
    if not apath.is_file():
        print(f"错误：答案卷不存在：{apath}\n"
              "答案卷不入公开仓库（r4 红线 6）。本机补救：\n"
              "  python scripts/migrate_human_judging.py\n"
              "（需工作区根有 盲测人工判读包.md 与 盲测人工判读包-答案.md）",
              file=sys.stderr)
        return 2

    results = splib.load_json(rp)
    answers = splib.load_json(apath)
    ans = {a["id"]: a for a in answers["rounds"]}
    by_id = {}
    for r in results.get("rounds", []):
        by_id[int(r["id"])] = r

    print("人工判读计分（判读问题：哪一段更像「这个作者在思考」）\n")
    header = f"{'回合':<4}{'题目':<14}{'你的选择':<6}{'带包臂':<5}{'子代理':<5}{'辨认':<4}{'与判官'}"
    print(header)
    print("-" * len(header) + "----")
    recognize_hit, judge_agree, blank, n = 0, 0, 0, 0
    for rid in sorted(ans):
        a = ans[rid]
        r = by_id.get(rid, {})
        choice = r.get("choice", "")
        packed = a["packed_arm"]
        judge = a["subagent_winner"]
        if choice not in ("甲", "乙", "都不像"):
            print(f"{rid:<4}{a['title'][:12]:<14}{'—':<6}{packed:<5}{judge:<5}{'未判':<4}{'—'}")
            continue
        n += 1
        rec = "✓" if choice == packed else "✗"
        agree = "✓" if choice == judge else "✗"
        if choice == "都不像":
            blank += 1
        else:
            recognize_hit += choice == packed
            judge_agree += choice == judge
        print(f"{rid:<4}{a['title'][:12]:<14}{choice:<6}{packed:<5}{judge:<5}{rec:<4}{agree}")

    print(f"\n① 辨认带包臂：{recognize_hit}/{n}（『都不像』{blank} 次不计入命中）")
    print(f"② 与子代理判官一致：{judge_agree}/{n}（判官战绩带包 6/8，见 calibration.json）")
    if n == 0:
        print("没有可计分的回合——请先在判读台完成判读并导出。")
        return 0
    rate = judge_agree / n
    if rate >= 0.75:
        print("结论：一致率高——同源偏差有限，子代理判官可继续用。")
    elif rate >= 0.5:
        print("结论：一致率中等——判官结论需与人工判读并读，暂不单独作数。")
    else:
        print("结论：一致率低——判官必须换模型或换人，如实记录进 calibration.json。")
    print("提示：判读结果请回填 calibration.json（style-calibrate 协议）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
