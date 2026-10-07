# -*- coding: utf-8 -*-
"""migrate_human_judging：盲测人工判读包 md → 结构化双 JSON（阶段 0 / r4 P0-1）。

用法：
    python scripts/migrate_human_judging.py [--pack <判读包.md>] [--answers <答案.md>]

产出：
    evals/human_judging.json          判读包本体（无答案，入仓库）
    evals/human_judging_answers.json  答案卷（敏感数据，gitignore，不进公开仓库）

迁移断言（防 md→JSON 丢信息）：回合数 == 8、带包臂序列 == 乙甲乙甲甲乙乙乙、
每回合甲/乙文本非空且互异、子代理判官战绩 == 带包 6/8。
md 归档保留（工作区根），JSON 为网页判读台与计分脚本的数据源。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT.parent  # 工作区根（判读包 md 所在，仓库外）

EXPECTED_PACKED = ["乙", "甲", "乙", "甲", "甲", "乙", "乙", "乙"]
EXPECTED_SUBAGENT_HITS = 6

RoundHead = re.compile(r"^##\s*回合\s*(\d+)（(.+?)）·\s*题：(.+?)\s*$")


def _parse_pack(md: str) -> list[dict]:
    rounds: list[dict] = []
    cur: dict | None = None
    arm = None
    buf: list[str] = []
    for line in md.splitlines():
        head = RoundHead.match(line.strip())
        if head:
            if cur:
                rounds.append(cur)
            cur = {"id": int(head.group(1)), "author": head.group(2),
                   "title": head.group(3), "甲": "", "乙": ""}
            arm, buf = None, []
            continue
        if cur is None:
            continue
        s = line.strip()
        if s == "【甲】":
            if buf and arm:
                cur[arm] = "\n".join(buf).strip()
            arm, buf = "甲", []
        elif s == "【乙】":
            if buf and arm:
                cur[arm] = "\n".join(buf).strip()
            arm, buf = "乙", []
        elif s.startswith("**你的判读**"):
            if buf and arm:
                cur[arm] = "\n".join(buf).strip()
            arm, buf = None, []
        elif arm and s and not s.startswith("#"):
            buf.append(line)
    if cur:
        rounds.append(cur)
    return rounds


def _parse_answers(md: str) -> list[dict]:
    rows: list[dict] = []
    for line in md.splitlines():
        s = line.strip()
        if not s.startswith("|") or s.startswith("| 回合") or set(s) <= {"|", "-", " ", ":"}:
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 5:
            continue
        rid = int(re.match(r"(\d+)", cells[0]).group(1))
        verdict = cells[4]
        conf_m = re.search(r"（(高|中偏高|中|低)）", verdict)
        note = verdict.split("——", 1)[1].strip() if "——" in verdict else ""
        rows.append({
            "id": rid,
            "甲_生成": cells[1].replace("**", ""),
            "乙_生成": cells[2].replace("**", ""),
            "packed_arm": cells[3].replace("**", ""),
            "subagent_winner": None,  # 由 packed_arm + 胜方措辞推出
            "subagent_confidence": conf_m.group(1) if conf_m else "",
            "subagent_note": note,
            "subagent_verdict_raw": verdict,
        })
    return rows


def migrate(pack_md: str, answers_md: str) -> tuple[dict, dict]:
    rounds = _parse_pack(pack_md)
    answers = _parse_answers(answers_md)
    assert len(rounds) == 8, f"回合数断言失败：{len(rounds)} != 8"
    assert [r["id"] for r in rounds] == list(range(1, 9)), "回合 id 断言失败"
    for r, packed in zip(rounds, EXPECTED_PACKED):
        assert r["甲"] and r["乙"], f"回合 {r['id']} 文本缺失"
        assert r["甲"] != r["乙"], f"回合 {r['id']} 甲乙文本相同"
    assert [a["packed_arm"] for a in answers] == EXPECTED_PACKED, \
        f"带包臂序列断言失败：{[a['packed_arm'] for a in answers]}"
    for r, a in zip(rounds, answers):
        a["author"], a["title"] = r["author"], r["title"]
    for a in answers:
        a["subagent_winner"] = (a["packed_arm"]
                                if a["subagent_verdict_raw"].startswith("带包胜")
                                else ("乙" if a["packed_arm"] == "甲" else "甲"))
    hits = sum(1 for a in answers if a["subagent_winner"] == a["packed_arm"])
    assert hits == EXPECTED_SUBAGENT_HITS, f"子代理战绩断言失败：{hits} != 6"

    judging = {
        "protocol": "人工判读 v1 —— 同源偏差度量（对应 盲测人工判读包.md v0.4.0）",
        "instruction": [
            "每回合约两段文字（【甲】【乙】），都试图模仿同一位作者，生成方式不同。",
            "判读问题（重点不在句子节奏和词汇——那是表层；请聚焦思想层）："
            "哪一段更像「这个作者在思考」——选题的胃口（他为什么写这个）、"
            "看事情的角度（从哪里下刀）、叙述者站在哪里说话、"
            "对笔下人物与读者的姿态？",
            "给出：选择（甲/乙/都不像）+ 一两句理由 + 置信度（高/中/低）。",
            "你的知识是唯一依据；判完之前不要打开答案文件。",
        ],
        "rounds": [{"id": r["id"], "author": r["author"], "title": r["title"],
                    "甲": r["甲"], "乙": r["乙"]} for r in rounds],
    }
    answers_out = {
        "note": "答案卷——判完再看；本文件不入 git（r4 红线 6，测试锁定）",
        "subagent_record": f"子代理判官带包 {hits}/8（见 calibration.json "
                           "thought_blind_v040 / final_verdict_v040）",
        "rounds": answers,
    }
    return judging, answers_out


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="盲测人工判读包 md → 双 JSON")
    ap.add_argument("--pack", default=str(WS / "盲测人工判读包.md"))
    ap.add_argument("--answers", default=str(WS / "盲测人工判读包-答案.md"))
    ap.add_argument("--out-judging", default=str(ROOT / "evals" / "human_judging.json"))
    ap.add_argument("--out-answers",
                    default=str(ROOT / "evals" / "human_judging_answers.json"))
    args = ap.parse_args()

    pack_md = splib.read_text(Path(args.pack))[0]
    answers_md = splib.read_text(Path(args.answers))[0]
    judging, answers_out = migrate(pack_md, answers_md)

    for path, data in ((args.out_judging, judging), (args.out_answers, answers_out)):
        out = Path(path)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"已写入 {out}")
    print(f"断言通过：8 回合、带包臂 {''.join(EXPECTED_PACKED)}、"
          f"子代理战绩 6/8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
