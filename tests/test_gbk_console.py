# -*- coding: utf-8 -*-
"""v0.2.4 回归：默认 GBK 控制台/管道（不设 PYTHONUTF8）下 CLI 与 MCP 不崩。

背景（codex 审查 P1）：emoji 报告与 ensure_ascii=False 的 JSON 在 cp936 流上
会 UnicodeEncodeError 或被本地代码页污染；旧测试套件因中文能被 GBK 编码而
侥幸全绿。本文件强制 PYTHONIOENCODING=cp936 复现最恶劣环境。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 最恶劣环境：显式 cp936，并剥掉一切 UTF-8 偏好变量
GBK_ENV = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
GBK_ENV["PYTHONIOENCODING"] = "cp936"

# 本模块测的是 Windows cp936 控制台行为（含反斜杠路径拼接），仅 Windows 实跑；
# linux CI（locale 本就是 UTF-8，无 cp936 控制台问题）跳过
IS_WINDOWS = os.name == "nt"


def _run(args, **kw):
    return subprocess.run(args, env=GBK_ENV, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", **kw)


@unittest.skipUnless(IS_WINDOWS, "cp936 控制台行为仅 Windows，非 Windows 跳过")
class TestGBKConsole(unittest.TestCase):
    def test_validate_pack_entry_no_crash(self):
        """validate_pack.main() 入口路径（P2：旧测试只覆盖 check_pack）。"""
        r = _run([sys.executable, str(ROOT / "scripts" / "validate_pack.py"),
                  str(ROOT / "stylepacks" / "luxun")], timeout=120)
        self.assertNotIn("UnicodeEncodeError", r.stderr, r.stderr)
        self.assertNotIn("Traceback", r.stderr, r.stderr)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_fp_check_entry_no_crash(self):
        text = Path(tempfile.mkdtemp()) / "sample.md"
        text.write_text("他推门出去，街上正落着细雨。\n" * 60, encoding="utf-8")
        r = _run([sys.executable, str(ROOT / "scripts" / "fp_check.py"),
                  str(ROOT / "stylepacks" / "luxun"), str(text)], timeout=120)
        self.assertNotIn("UnicodeEncodeError", r.stderr, r.stderr)
        self.assertNotIn("Traceback", r.stderr, r.stderr)
        self.assertIn(r.returncode, (0, 1))
        self.assertIn("文体判定", r.stdout)          # emoji 行正常产出

    def test_mcp_stdio_utf8_under_gbk(self):
        server = ROOT / "server" / "mcp_server.py"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "bible").mkdir()
            (p / "manuscript").mkdir()
            (p / "bible" / "names.json").write_text(
                json.dumps([{"name": "测试者", "tier": "core"}], ensure_ascii=False),
                encoding="utf-8")
            (p / "manuscript" / "001.md").write_text(
                "# 一\n测试者走进房间，玉佩微凉。", encoding="utf-8")
            inp = "\n".join([
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                            "params": {"protocolVersion": "2024-11-05"}},
                           ensure_ascii=False),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                            "params": {"name": "story.sync", "arguments": {}}},
                           ensure_ascii=False),
            ]) + "\n"
            r = subprocess.run(
                [sys.executable, str(server), "--project", str(p)],
                input=inp.encode("utf-8"), env=GBK_ENV, capture_output=True,
                timeout=120)  # 字节级进出，手工按 UTF-8 解码——模拟 UTF-8 宿主
            self.assertNotIn("Traceback", r.stderr.decode("utf-8", "replace"))
            lines = [ln for ln in r.stdout.decode("utf-8").splitlines() if ln.strip()]
            self.assertTrue(lines, "stdio 无响应")
            resp1 = json.loads(lines[0])
            self.assertEqual(resp1["result"]["serverInfo"]["name"], "stylepack")
            resp2 = json.loads(lines[1])
            self.assertFalse(resp2["result"].get("isError"), resp2)


@unittest.skipUnless(IS_WINDOWS, "cp936 控制台行为仅 Windows，非 Windows 跳过")
class TestGBKSmokeAllCLI(unittest.TestCase):
    """v0.2.6 收口：每个 CLI 在 GBK 管道下真实实跑，断言关键词而非只看 rc——
    errors=replace 会把编码错误吞成乱码而非崩溃，仅看 rc 会漏判。"""

    def _smoke(self, args, expect_rc, expect_word=None):
        r = _run([sys.executable] + args, timeout=120)
        self.assertNotIn("Traceback", r.stderr, r.stderr)
        self.assertNotIn("UnicodeEncodeError", r.stderr, r.stderr)
        self.assertEqual(r.returncode, expect_rc, r.stdout + r.stderr)
        if expect_word:
            self.assertIn(expect_word, r.stdout)
        return r

    def test_all_cli_entries(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "s.txt").write_text(
                "他推门出去，街上正落着细雨。林凡握紧玉佩。\n", encoding="utf-8")
            (t / "names.json").write_text(json.dumps(
                [{"name": "林凡", "aliases": [], "tier": "core"}],
                ensure_ascii=False), encoding="utf-8")
            (t / "timeline.json").write_text(json.dumps(
                {"events": [{"id": "e1", "order": 1, "description": "测试事件"}]},
                ensure_ascii=False), encoding="utf-8")
            S = str(ROOT / "scripts")
            cases = [
                ("fp_extract", [S + r"\fp_extract.py", str(t / "s.txt")],
                 0, "总字符数"),
                ("ingest", [S + r"\ingest.py", "--input", str(t / "s.txt"),
                            "--out", str(t / "corpus" / "x"), "--work", "测试"],
                 0, "入库完成"),
                ("export_pack", [S + r"\export_pack.py",
                                 str(ROOT / "stylepacks" / "luxun"),
                                 "--out", str(t / "l.md")], 0, "已导出"),
                ("cost_log", [S + r"\cost.py", "log", "--skill", "t",
                              "--chars", "10", "--project", str(t)], 0, "已记账"),
                ("cost_report", [S + r"\cost.py", "report", "--project", str(t)],
                 0, "读取字符"),
                ("story_sync", [S + r"\story.py", "--project", str(t), "sync"],
                 0, "ok"),
                ("names_check", [S + r"\names_check.py", "--names",
                                 str(t / "names.json"), str(t / "s.txt")],
                 0, "林凡"),
                # 真实工具路径（v0.2.7：替换此前的 --help 冒烟）
                ("timeline_check", [S + r"\timeline_check.py", "--timeline",
                                    str(t / "timeline.json")], 0, "时间线一致"),
                # borrow_check（v0.4.2）：真包真引文，干净草稿走 GBK 管道
                ("borrow_check", [S + r"\borrow_check.py", str(t / "s.txt"),
                                  "--pack", str(ROOT / "stylepacks" / "zhuziqing")],
                 0, "未发现"),
            ]
            for name, args, rc, word in cases:
                with self.subTest(cli=name):
                    self._smoke(args, rc, word)


if __name__ == "__main__":
    unittest.main()
