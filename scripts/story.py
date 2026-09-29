# -*- coding: utf-8 -*-
"""story：状态机双暴露 CLI（与 MCP 工具一一对应，共用 server/store.py 实现）。

用法：
    python scripts/story.py sync   [--project <项目>]
    python scripts/story.py search --query <关键词> [--k 5] [--project P]
    python scripts/story.py character --name <人物> [--project P]
    python scripts/story.py recap [--n 3] [--project P]
    python scripts/story.py foreshadow [--status planted|closed] [--project P]
    python scripts/story.py propose --payload <delta.json> [--project P]
    python scripts/story.py merge [--ids 1,2] [--force] [--project P]
    python scripts/story.py aging [--project P]

MCP 在场时优先用 MCP 工具；本 CLI 是无 MCP 宿主的等价路径（单一实现、两个壳）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "scripts"))

from store import Store, fit  # noqa: E402
import splib  # noqa: E402


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="故事状态机 CLI")
    ap.add_argument("--project", default=".")
    # 允许 --project 放在子命令之后（与之前等价，双位置兼容）
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--project", default=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sync", parents=[parent])
    p = sub.add_parser("search", parents=[parent]); p.add_argument("--query", required=True); p.add_argument("--k", type=int, default=5)
    p = sub.add_parser("character", parents=[parent]); p.add_argument("--name", required=True)
    p = sub.add_parser("recap", parents=[parent]); p.add_argument("--n", type=int, default=3)
    p = sub.add_parser("foreshadow", parents=[parent]); p.add_argument("--status", default=None)
    p = sub.add_parser("propose", parents=[parent]); p.add_argument("--payload", required=True, help="delta JSON 文件")
    p = sub.add_parser("merge", parents=[parent]); p.add_argument("--ids", default=""); p.add_argument("--force", action="store_true")
    sub.add_parser("aging", parents=[parent])

    args = ap.parse_args()
    store = Store(Path(args.project).resolve())

    if args.cmd == "sync":
        out = store.sync()
    elif args.cmd == "search":
        out = {"results": store.search(args.query, args.k)}
    elif args.cmd == "character":
        out = {"card": store.character(args.name)}
    elif args.cmd == "recap":
        out = store.recap(args.n)
    elif args.cmd == "foreshadow":
        out = {"foreshadow": store.foreshadow(args.status)}
    elif args.cmd == "propose":
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        out = store.propose_delta(payload)
    elif args.cmd == "merge":
        ids = [int(x) for x in args.ids.split(",") if x.strip()] or None
        out = store.merge_delta(ids, args.force)
    else:  # aging
        out = store.pending_aging()

    store.close()
    print(json.dumps(fit(out), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
