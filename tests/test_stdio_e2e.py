# -*- coding: utf-8 -*-
"""v0.2 端到端测试：真实子进程 stdio 协议握手与工具调用。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server" / "mcp_server.py"


class TestStdioE2E(unittest.TestCase):
    def test_handshake_and_call(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "bible").mkdir()
            (p / "manuscript").mkdir()
            (p / "bible" / "names.json").write_text(
                json.dumps([{"name": "测试者", "tier": "core"}], ensure_ascii=False),
                encoding="utf-8")
            (p / "manuscript" / "001.md").write_text(
                "# 一\n测试者走进房间。", encoding="utf-8")

            lines = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                 "params": {"protocolVersion": "2024-11-05"}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                 "params": {"name": "story.sync", "arguments": {}}},
                {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                 "params": {"name": "story.search",
                            "arguments": {"query": "测试者"}}},
            ]
            stdin = "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in lines)
            proc = subprocess.run(
                [sys.executable, str(SERVER), "--project", str(p)],
                input=stdin, capture_output=True, text=True,
                encoding="utf-8", timeout=60)
            outs = [json.loads(l) for l in proc.stdout.splitlines() if l.strip()]
            self.assertEqual(len(outs), 4)  # 通知不回包
            self.assertEqual(outs[0]["result"]["serverInfo"]["name"], "stylepack")
            self.assertLessEqual(len(outs[1]["result"]["tools"]), 10)
            sync = json.loads(outs[2]["result"]["content"][0]["text"])
            self.assertTrue(sync["ok"])
            self.assertEqual(sync["chapters"], 1)
            search = json.loads(outs[3]["result"]["content"][0]["text"])
            self.assertTrue(search["results"])
            self.assertIn("测试者", search["results"][0]["snippet"])


if __name__ == "__main__":
    unittest.main()
