# -*- coding: utf-8 -*-
"""web 工作台 v0.6.0 服务端测试：mock 模型 e2e + 红线断言（key/session/绑定）。"""
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fastapi.testclient import TestClient

S = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(S / "web"))
sys.path.insert(0, str(S / "scripts"))

import appstate  # noqa: E402
from server import create_app  # noqa: E402

MOCK_KEY = "sk-mock-1234567890"

PROSE = ("他推门出去，街上正落着细雨。夜色像一层旧棉絮盖在屋顶上，"
         "远处有狗叫了两声，又静了。\n他攥紧了手里的钥匙，指节发白。")

OUTLINE = {"options": [
    {"title": "方向A", "angle": "以小见大", "action": "立意1 小物承大情",
     "stance": "克制外化"}], "recommended": 0}
BEATS = {"beats": [{"no": 1, "beat": "承接上章：雨夜归途"},
                   {"no": 2, "beat": "场景：屋内对峙"},
                   {"no": 3, "beat": "钩子：门外脚步"}],
         "tone_note": "不指定", "canon_anchor": "无"}


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 静默
        pass

    def _send(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.endswith("/models"):
            self._send({"data": [{"id": "mock-write"}, {"id": "mock-judge"}]})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        user_msg = payload["messages"][-1]["content"]
        if "只输出正文本身" in user_msg:
            content = PROSE
        elif "收尾检查" in user_msg:
            content = json.dumps({"violation": False, "reason": "物化收束，无立碑/安慰/点题"},
                                 ensure_ascii=False)
        elif "重掷第" in user_msg:
            content = json.dumps({"no": 2, "beat": "重掷后的场景：意外来客"}, ensure_ascii=False)
        elif "2–3 个立意方向" in user_msg:
            content = json.dumps(OUTLINE, ensure_ascii=False)
        elif "拍子表" in user_msg:
            content = json.dumps(BEATS, ensure_ascii=False)
        else:
            content = PROSE
        self._send({"choices": [{"message": {"content": content}}],
                    "model": payload.get("model", "mock"),
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50}})


class TestWebServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock = ThreadingHTTPServer(("127.0.0.1", 0), MockHandler)
        cls.mock_port = cls.mock.server_address[1]
        threading.Thread(target=cls.mock.serve_forever, daemon=True).start()

        cls.tmp = tempfile.TemporaryDirectory()
        ws = Path(cls.tmp.name) / "ws"
        proj = ws / "测试项目"
        (proj / "bible").mkdir(parents=True)
        (proj / "manuscript").mkdir()
        (proj / "bible" / "characters.md").write_text(
            "## 韩天宇\n主角。性格：贱、怂、精明。\n\n## 大比目鱼\n深渊传奇武器，"
            "蓝发少女形态，老派绅士作派。\n", encoding="utf-8")
        (proj / "manuscript" / "001-开局.md").write_text(
            "雨夜里他第一次见到那把枪。\n枪说自己叫大比目鱼。\n", encoding="utf-8")
        cls.cfg_path = Path(cls.tmp.name) / "config.local.json"
        appstate.DEFAULT_CONFIG_PATH = cls.cfg_path  # 测试注入，不碰真实配置
        cfg = appstate.load_config(cls.cfg_path)
        cfg["workspace_root"] = str(ws)
        cfg["providers"] = [{"name": "mock", "base_url":
                             f"http://127.0.0.1:{cls.mock_port}/v1",
                             "api_key": MOCK_KEY, "models": ["mock-write"]}]
        cfg["routing"] = {"write": {"provider": "mock", "model": "mock-write"},
                          "judge": {"provider": "mock", "model": "mock-judge"}}
        appstate.save_config(cfg, cls.cfg_path)
        cls.client = TestClient(create_app(site_dir=S / "web" / "site"))

    @classmethod
    def tearDownClass(cls):
        cls.mock.shutdown()

    def test_config_sanitized(self):
        r = self.client.get("/app/api/config")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(MOCK_KEY, r.text, "key 泄漏进配置接口")
        view = r.json()
        self.assertTrue(view["providers"][0]["has_key"])
        self.assertNotIn("api_key", view["providers"][0])

    def test_config_gitignored(self):
        gi = (S / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("web/config.local.json", gi)

    def test_test_connection(self):
        r = self.client.post("/app/api/config/test", json={"name": "mock"})
        self.assertTrue(r.json()["ok"])
        self.assertIn("mock-write", r.json()["models"])

    def test_projects_discovered(self):
        r = self.client.get("/app/api/projects")
        names = [p["name"] for p in r.json()["projects"]]
        self.assertIn("测试项目", names)
        self.assertIn("luxun", [p["name"] for p in r.json()["packs"]])

    def test_project_traversal_blocked(self):
        r = self.client.post("/app/api/assemble", json={
            "project": "../stylepacks", "pack": "luxun",
            "chapter_no": 1, "keywords": []})
        self.assertEqual(r.status_code, 400)

    def test_assemble_preview(self):
        r = self.client.post("/app/api/assemble", json={
            "project": "测试项目", "pack": "luxun", "chapter_no": 2,
            "keywords": ["大比目鱼"]})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        kinds = [i["kind"] for i in d["items"]]
        self.assertIn("包·文风档案", kinds)
        self.assertIn("记忆·人物", kinds)
        self.assertIn("章节锚定·上一章结尾", kinds)
        self.assertTrue(any("大比目鱼" in i["excerpt"] for i in d["items"]))
        self.assertNotIn("kept_texts", d, "预览不得外带全文")

    def test_creation_e2e(self):
        base = {"project": "测试项目", "pack": "luxun", "chapter_no": 2,
                "title": "夜谈", "keywords": ["大比目鱼"]}
        o = self.client.post("/app/api/outline", json={**base, "user_notes": ""})
        self.assertEqual(o.status_code, 200)
        self.assertEqual(len(o.json()["options"]), 1)
        sid = o.json()["session_id"]

        b = self.client.post("/app/api/beats", json={
            **base, "chosen": OUTLINE["options"][0], "session_id": sid})
        self.assertEqual(len(b.json()["beats"]), 3)

        rr = self.client.post("/app/api/reroll_beat", json={
            **base, "chosen": OUTLINE["options"][0], "beats": BEATS["beats"],
            "index": 2, "session_id": sid})
        self.assertIn("重掷", rr.json()["beat"]["beat"])

        g = self.client.post("/app/api/generate", json={
            **base, "chosen": OUTLINE["options"][0], "beats": BEATS["beats"],
            "tone_note": "不指定", "canon_anchor": "无", "n_drafts": 1,
            "session_id": sid})
        self.assertEqual(g.status_code, 200)
        draft = g.json()["drafts"][0]
        self.assertIn("细雨", draft["text"])
        self.assertIn("fp_check", draft)
        self.assertIn("borrow_check", draft)

        e = self.client.post("/app/api/ending_check", json={
            "project": "测试项目", "title": "夜谈",
            "text": draft["text"], "session_id": sid})
        self.assertFalse(e.json()["ending_check"]["violation"])

        s = self.client.post("/app/api/save", json={
            **base, "text": draft["text"], "chosen": OUTLINE["options"][0],
            "beats": BEATS["beats"], "checks": {"ending": e.json()["ending_check"]},
            "usage": draft["usage"], "session_id": sid,
            "assembly_preview": g.json()["assembly_preview"]})
        self.assertEqual(s.status_code, 200)
        ws = Path(self.tmp.name) / "ws" / "测试项目"
        self.assertTrue((ws / "manuscript" / "002-夜谈.md").is_file())
        sessions = list((ws / "sessions").glob("*.json"))
        self.assertEqual(len(sessions), 1)
        self.assertTrue((ws / "sessions" / ".gitignore").is_file())
        record = sessions[0].read_text(encoding="utf-8")
        self.assertNotIn(MOCK_KEY, record, "key 泄漏进会话记录")
        self.assertIn("章节锚定", record, "会话记录缺装配快照（可复判要求）")
        self.assertIn("细雨", record)
        cost = (ws / "style" / "cost.jsonl").read_text(encoding="utf-8")
        self.assertIn("web-create", cost)

    def test_unconfigured_route_fails_clean(self):
        cfg = appstate.load_config(self.cfg_path)
        cfg["routing"]["write"] = None
        appstate.save_config(cfg, self.cfg_path)
        r = self.client.post("/app/api/outline", json={
            "project": "测试项目", "pack": "luxun", "chapter_no": 2,
            "title": "夜谈", "keywords": []})
        self.assertEqual(r.status_code, 400)
        self.assertIn("模型配置", r.json()["detail"])
        cfg["routing"]["write"] = {"provider": "mock", "model": "mock-write"}
        appstate.save_config(cfg, self.cfg_path)

    def test_localhost_binding_source(self):
        src = (S / "web" / "launch.py").read_text(encoding="utf-8")
        self.assertIn('host="127.0.0.1"', src)
        self.assertNotIn('("0.0.0.0"', src)


if __name__ == "__main__":
    unittest.main()
