# -*- coding: utf-8 -*-
"""timeline_check：时间线一致性检查（脚本侧，机器可校验部分）。

用法：
    python scripts/timeline_check.py --timeline <bible/timeline.json> [--manuscript <正文目录>]

timeline.json 格式：
    {"events": [{"id": "e1", "order": 1, "date": "1921-09-01"（可选，ISO）,
                 "description": "...", "chapters": ["001-xxx.md"]（可选）}]}
检查：id 唯一；order 若存在必须严格递增且不重复；date 若存在必须可解析；
chapters 引用必须真实存在（需 --manuscript）。
退出码：0 = 正常；1 = 存在错误。
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402


def parse_date(s: str):
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        try:
            return datetime.datetime.fromisoformat(s).date()
        except ValueError:
            return None


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="时间线一致性检查")
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--manuscript", help="正文目录（校验章节引用时必需）")
    args = ap.parse_args()

    data = splib.load_json(args.timeline)
    events = data.get("events", [])
    errors: list[str] = []

    ids = [e.get("id") for e in events]
    if len(ids) != len(set(ids)):
        errors.append("存在重复的事件 id")

    orders = [e["order"] for e in events if "order" in e]
    if orders and (len(orders) != len(set(orders)) or orders != sorted(orders)):
        errors.append("order 字段重复或非递增，时间顺序存在矛盾")

    for e in events:
        if "date" in e and parse_date(e["date"]) is None:
            errors.append(f"事件 {e.get('id')} 的日期无法解析：{e['date']}")

    if args.manuscript:
        known = {f.name for f in Path(args.manuscript).rglob("*.md")}
        for e in events:
            for ch in e.get("chapters", []):
                if ch not in known:
                    errors.append(f"事件 {e.get('id')} 引用了不存在的章节：{ch}")

    for err in errors:
        print(f"❌ {err}")
    if not errors:
        print(f"✅ 时间线一致（{len(events)} 个事件）")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
