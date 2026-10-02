# -*- coding: utf-8 -*-
"""export_pack：把风格包目录编译为自包含单文件 Markdown。

用法：
    python scripts/export_pack.py <风格包目录> --out <输出.md>

单文件 = 使用说明 + 精华卡 + 完整档案 + 范例 + 词汇 + 边界 + JSON 附录。
把这一个文件贴进任何裸 agent 对话即可按该文风写作，无需插件、无需原文。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402

SECTIONS = [
    ("card.md", "精华卡"),
    ("profile.md", "完整档案"),
    ("thought.md", "思想档案"),
    ("exemplars.md", "范例"),
    ("registers.md", "调子分区"),
    ("lexicon.md", "词汇与句式"),
    ("limits.md", "能力边界"),
]

# 可选段：包内没有该文件时整段跳过，老包导出保持既有五段不变。
# registers.md（R0 调子分区）与 thought.md（v0.3 思想层）均走此机制。
OPTIONAL_SECTIONS = {"registers.md", "thought.md"}

PREAMBLE = (
    "你是使用本风格包的写作助手。以下资料完整描述了一位作者的文风，"
    "请在写作时严格遵循「完整档案」的指导、「词汇与句式」的用词习惯、"
    "「范例」所演示的特征，并遵守「禁用清单」。本文件自包含，不依赖任何外部语料。"
)


def _strip_h1(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="导出自包含单文件风格包")
    ap.add_argument("pack", help="风格包目录")
    ap.add_argument("--out", required=True, help="输出 .md 路径")
    args = ap.parse_args()

    pack_dir = Path(args.pack)
    missing = [n for n in splib.PACK_FILES if not (pack_dir / n).is_file()]
    if missing:
        print(f"错误：包不完整，缺少 {missing}，先运行 validate_pack", file=sys.stderr)
        return 2

    pj = splib.load_json(pack_dir / "pack.json")
    fp = splib.load_json(pack_dir / "fingerprint.json")

    preamble = PREAMBLE
    if (pack_dir / "thought.md").is_file():
        preamble += ("如本文件包含「思想档案」，写作时遵循其立意动作与观察清单，"
                     "使用「意象系统」的意象，并遵守「禁区」——宁可平实，不硬贴。")

    out = [f"<!-- STYLEPACK-SINGLE-FILE format_version={pj['format_version']} -->", ""]
    out.append(f"# StylePack：{pj['display_name']}")
    out.append("")
    out.append(f"> {preamble}")
    out.append("")

    for fname, title in SECTIONS:
        p = pack_dir / fname
        if not p.is_file():
            if fname in OPTIONAL_SECTIONS:
                continue
        body = _strip_h1(p.read_text(encoding="utf-8"))
        out.append(f"## {title}")
        out.append("")
        out.append(body)
        out.append("")

    out.append("## 附录：量化指纹（JSON）")
    out.append("")
    out.append("```json")
    out.append(json.dumps(fp, ensure_ascii=False, indent=2))
    out.append("```")
    out.append("")
    out.append("## 附录：包清单（JSON）")
    out.append("")
    out.append("```json")
    out.append(json.dumps(pj, ensure_ascii=False, indent=2))
    out.append("```")
    out.append("")

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"单文件风格包已导出：{dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
