# -*- coding: utf-8 -*-
"""v0.2 测试：状态机（store）、MCP 协议、交接测试、返回纪律。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "scripts"))

from store import Store  # noqa: E402
from mcp_server import MCPServer  # noqa: E402


def _project(td: Path) -> Path:
    p = td / "proj"
    (p / "bible" / "pending").mkdir(parents=True)
    (p / "manuscript").mkdir()
    (p / "bible" / "names.json").write_text(json.dumps([
        {"name": "林凡", "aliases": ["凡哥"], "tier": "core"},
        {"name": "小翠", "aliases": [], "tier": "minor"},
    ], ensure_ascii=False), encoding="utf-8")
    (p / "bible" / "characters.md").write_text(
        "## 林凡\n主角，冷静，重情。\n\n## 小翠\n丫鬟，机敏。", encoding="utf-8")
    (p / "bible" / "foreshadowing.md").write_text(
        "- 001 玉佩的裂纹未解释\n- 002 神秘信件（已回收）", encoding="utf-8")
    (p / "manuscript" / "001-初入山门.md").write_text(
        "# 第一章\n林凡握紧玉佩，与小翠道别，踏入了山门。", encoding="utf-8")
    (p / "manuscript" / "002-夜探藏书楼.md").write_text(
        "# 第二章\n林凡夜探藏书楼，发现一封神秘信件。", encoding="utf-8")
    return p


class TestStore(unittest.TestCase):
    def test_sync_search_character_recap(self):
        with tempfile.TemporaryDirectory() as td:
            p = _project(Path(td))
            s = Store(p)
            info = s.sync()
            self.assertTrue(info["ok"])
            self.assertEqual(info["characters"], 2)
            self.assertEqual(info["chapters"], 2)
            rows = s.search("玉佩")
            self.assertTrue(rows and "玉佩" in rows[0]["snippet"])
            card = s.character("林凡")
            self.assertEqual(card["name"], "林凡")
            self.assertEqual(card["tier"], "core")
            self.assertIn("主角", card["summary"])
            card2 = s.character("凡哥")  # 别名可达
            self.assertEqual(card2["name"], "林凡")
            r = s.recap(3)
            self.assertEqual(len(r["recent"]), 2)
            self.assertEqual(len(r["open_foreshadow"]), 1)  # 002 已回收
            self.assertTrue(all(d["digest"] for d in r["recent"]))
            s.close()

    def test_propose_risk_grading_and_merge(self):
        with tempfile.TemporaryDirectory() as td:
            p = _project(Path(td))
            s = Store(p)
            s.sync()
            out = s.propose_delta({
                "chapter": "003-试炼.md", "digest": "林凡通过试炼，小翠受伤。",
                "changes": [
                    {"entity": "林凡", "field": "location", "value": "试炼谷"},
                    {"entity": "小翠", "field": "mood", "value": "不安"},
                    {"entity": "路人甲", "field": "location", "value": "村口"},
                ]})
            risks = {a["entity"]: a["risk"] for a in out["proposed"]}
            self.assertEqual(risks["林凡"], "high")    # core 实体 → 高风险
            self.assertEqual(risks["小翠"], "low")     # minor + mood → 低风险
            self.assertEqual(risks["路人甲"], "low")   # 新实体 + location → 低风险
            m1 = s.merge_delta(None)                    # 低风险自动合并
            self.assertIn(3, m1["merged"])              # 路人甲
            self.assertTrue(any(b["risk"] == "high" for b in m1["blocked"]))
            m2 = s.merge_delta(None, force=True)        # 用户确认后合并
            self.assertTrue(m2["merged"])
            card = s.character("林凡")
            self.assertTrue(any(st["field"] == "location" and st["value"] == "试炼谷"
                                for st in card["recent_states"]))
            r = s.recap(3)
            digests = {d["chapter"]: d["digest"] for d in r["recent"]}
            self.assertIn("林凡通过试炼", digests.get("003-试炼.md", ""))
            self.assertTrue((p / "bible" / "pending" / "merged.log").exists())
            self.assertEqual(s.pending_aging()["total_pending"], 0)
            s.close()

    def test_fit_truncation(self):
        from store import fit
        big = {"results": [{"snippet": "x" * 300} for _ in range(50)]}
        self.assertLessEqual(len(json.dumps(fit(big), ensure_ascii=False).encode("utf-8")), 2000)


class TestMCP(unittest.TestCase):
    def test_handshake_tools_and_handoff(self):
        with tempfile.TemporaryDirectory() as td:
            p = _project(Path(td))
            srv = MCPServer(p)
            resp = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                               "params": {"protocolVersion": "2024-11-05"}})
            self.assertEqual(resp["result"]["serverInfo"]["name"], "stylepack")
            self.assertIsNone(srv.handle({"jsonrpc": "2.0",
                                          "method": "notifications/initialized"}))
            tools = srv.handle({"jsonrpc": "2.0", "id": 2,
                                "method": "tools/list"})["result"]["tools"]
            self.assertLessEqual(len(tools), 10)  # 工具纪律硬上限
            self.assertIn("story.recap", {t["name"] for t in tools})

            def call(i, name, arguments):
                return srv.handle({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                                   "params": {"name": name, "arguments": arguments}})

            call(3, "story.sync", {})
            # 交接测试（机械化）：新会话只靠 recap + character 两次调用拿齐续写上下文
            recap = call(4, "story.recap", {"n": 2})["result"]["content"][0]["text"]
            self.assertLessEqual(len(recap.encode("utf-8")), 2048)  # 返回纪律
            self.assertIn("林凡", recap)
            card = call(5, "story.character", {"name": "林凡"})["result"]["content"][0]["text"]
            self.assertLessEqual(len(card.encode("utf-8")), 2048)
            self.assertIn("主角", card)
            self.assertTrue((p / "style" / "cost.jsonl").exists())  # 自动记账
            srv.store.close()

    def test_unknown_method_and_tool(self):
        with tempfile.TemporaryDirectory() as td:
            srv = MCPServer(_project(Path(td)))
            resp = srv.handle({"jsonrpc": "2.0", "id": 9, "method": "no/such"})
            self.assertEqual(resp["error"]["code"], -32601)
            resp = srv.handle({"jsonrpc": "2.0", "id": 10, "method": "tools/call",
                               "params": {"name": "nope", "arguments": {}}})
            self.assertTrue(resp["result"]["isError"])

    def test_fp_check_tool(self):
        with tempfile.TemporaryDirectory() as td:
            p = _project(Path(td))
            srv = MCPServer(p)
            srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "story.sync", "arguments": {}}})
            resp = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                               "params": {"name": "fp.check", "arguments": {
                                   "pack": str(ROOT / "stylepacks" / "luxun"),
                                   "text_path": "manuscript/001-初入山门.md"}}})
            self.assertNotIn("error", resp["result"].get("content", [{}])[0])
            out = json.loads(resp["result"]["content"][0]["text"])
            self.assertIn("ok", out)
            self.assertTrue(out["rows"])
            srv.store.close()


    def test_stylepack_info_list_alias_and_error_keeps_available(self):
        # v0.2.2 实测回归：缺省=清单（成功路径）；中文名别名可达；
        # 错误载荷必须保留 available——v0.2.1 的 isError 包装曾把自救清单整个丢弃，
        # 导致宿主误判"没有风格包"后凭印象直写
        with tempfile.TemporaryDirectory() as td:
            srv = MCPServer(_project(Path(td)))

            def call(i, arguments):
                return srv.handle({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                                   "params": {"name": "stylepack.info",
                                              "arguments": arguments}})

            listing = call(1, {})
            self.assertFalse(listing["result"]["isError"])
            packs = json.loads(listing["result"]["content"][0]["text"])["packs"]
            self.assertIn("luxun", {p["name"] for p in packs})
            self.assertIn("鲁迅", {p["display_name"] for p in packs})

            alias = call(2, {"name": "鲁迅"})
            self.assertFalse(alias["result"]["isError"])
            info = json.loads(alias["result"]["content"][0]["text"])["info"]
            self.assertEqual(info["name"], "luxun")

            miss = call(3, {"name": "不存在的作者"})
            self.assertTrue(miss["result"]["isError"])
            payload = json.loads(miss["result"]["content"][0]["text"])
            self.assertIn("error", payload)
            self.assertIn("luxun", [p["name"] for p in payload["available"]])
            srv.store.close()


if __name__ == "__main__":
    unittest.main()
