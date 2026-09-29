# -*- coding: utf-8 -*-
"""names_check：人物专名一致性检查（脚本侧）。

用法：
    python scripts/names_check.py --names <bible/names.json> <正文文件或目录...>

names.json 格式：
    [{"name": "孔乙己", "aliases": ["孔乙己", "孔乙已"]}, ...]
（把常见错写放进 aliases 可以顺带统计错写出现次数。）

输出：每个名字（含别名）的出现次数、零出现警告。
退出码：0 = 正常；1 = 存在零出现的人名（供 CI / 技能判断）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="人物专名一致性检查")
    ap.add_argument("--names", required=True, help="bible/names.json 路径")
    ap.add_argument("inputs", nargs="+", help="正文文件或目录")
    args = ap.parse_args()

    people = splib.load_json(args.names)
    files = splib.collect_text_files(args.inputs)
    if not files:
        print("错误：未找到正文文件", file=sys.stderr)
        return 2
    full = "\n".join(splib.read_text(f)[0] for f in files)

    rows = []
    zero = 0
    for person in people:
        variants = [person["name"]] + person.get("aliases", [])
        counts = {v: len(re.findall(re.escape(v), full)) for v in variants}
        total = sum(counts.values())
        if total == 0:
            zero += 1
        rows.append((person["name"], counts, total))

    for name, counts, total in rows:
        detail = "，".join(f"{v}×{c}" for v, c in counts.items() if c)
        print(f"{name}: 共 {total} 次" + (f"（{detail}）" if detail else "  ⚠️ 全文未出现"))
    print(f"\n人名总数 {len(rows)}，零出现 {zero}")
    return 1 if zero else 0


if __name__ == "__main__":
    raise SystemExit(main())
