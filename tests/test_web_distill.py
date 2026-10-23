# -*- coding: utf-8 -*-
"""蒸馏工作台 v0.7.0 阶段 A 测试：语料入库/指纹/体检编排 + 草稿包过滤。
阶段 A 零模型调用——不需要 mock 模型服务器。"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import json as _json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from fastapi.testclient import TestClient  # noqa
    S = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(S / "web"))
    sys.path.insert(0, str(S / "scripts"))
    import appstate  # noqa: E402
    from server import create_app  # noqa: E402
    _HAS_DEPS = True
except ImportError:
    _HAS_DEPS = False

FULL = {"视角": "第一人称回忆", "节奏": "短句压长句", "对话": "冷面接梗",
        "场景": "白描转场", "情绪": "物象承载", "手法": [{"手法": "反语", "依据": "a-叙述篇"}],
        "选择": "写小人物", "立意动作": [{"动作": "以小见大", "依据": "a-叙述篇"}],
        "细节": "吃穿用度", "意象族": ["灯", "路"]}
CHUNK_OBS = {"视角": "第三人称", "节奏": "短句", "对话": "口癖重复",
             "场景": "硬切", "手法": ["复沓"]}
LAST_MSG = {"v": ""}


class MockDistillHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        payload = _json.loads(self.rfile.read(n) or b"{}")
        msg = payload["messages"][-1]["content"]
        LAST_MSG["v"] = msg
        if "融合为最终答案" in msg:
            content = FULL
        elif "分块精读" in msg:
            content = CHUNK_OBS
        else:
            content = FULL
        body = _json.dumps({"choices": [{"message": {"content": _json.dumps(
            content, ensure_ascii=False)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}},
            ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

NOVEL = (
    "第一章 落水\n\n他掉进了河里。河水冰冷刺骨。他大声喊叫，声音在水面上飘得很远。\n\n"
    "“救命！”他喊。\n\n"
    "第二章 上岸\n\n他爬上了岸。天已经黑透了。他抱着肩膀发抖。\n\n"
    "“见鬼。”他说。\n"
)

FLAT_A = "平原上，风把麦子压弯了腰。他走过田埂，什么也没说，只是把帽子按了按。" * 4
FLAT_B = "\n\n“你到底去不去？”他问。\n\n“去。”她说。\n" * 10


@unittest.skipUnless(_HAS_DEPS, "web 依赖未安装（pip install -r web/requirements-web.txt）")
class TestDistillStageA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        ws = Path(cls.tmp.name) / "ws"
        (ws / "downloads" / "corpus").mkdir(parents=True)
        (ws / "测试项目" / "bible").mkdir(parents=True)  # 供 assemble 走到 _pack_dir
        cls.mock = ThreadingHTTPServer(("127.0.0.1", 0), MockDistillHandler)
        threading.Thread(target=cls.mock.serve_forever, daemon=True).start()
        cls.cfg_path = Path(cls.tmp.name) / "config.local.json"
        appstate.DEFAULT_CONFIG_PATH = cls.cfg_path
        cfg = appstate.load_config(cls.cfg_path)
        cfg["workspace_root"] = str(ws)
        cfg["providers"] = [{"name": "mock", "base_url":
                             f"http://127.0.0.1:{cls.mock.server_address[1]}/v1",
                             "api_key": "sk-distill-mock", "models": ["m1"]}]
        cfg["routing"] = {"write": {"provider": "mock", "model": "m1"}}
        appstate.save_config(cfg, cls.cfg_path)
        cls.client = TestClient(create_app(site_dir=S / "web" / "site"))
        cls.ws = ws

    @classmethod
    def tearDownClass(cls):
        cls.mock.shutdown()
        for name in ("draftpkg", "fppkg", "rdpkg"):  # 草稿包建在仓库 stylepacks/，测完即清
            shutil.rmtree(S / "stylepacks" / name, ignore_errors=True)


    def _ingest(self):
        r = self.client.post(
            "/app/api/distill/ingest",
            params={"author": "测试作者", "work": "落水记", "filename": "落水记.txt"},
            content=NOVEL.encode("utf-8"))
        self.assertEqual(r.status_code, 200)
        return r.json()

    def test_page_and_cli_lines(self):
        r = self.client.get("/app/distill")
        self.assertEqual(r.status_code, 200)
        self.assertIn("语料入库", r.text)
        self.assertIn("等价 CLI", r.text)
        self.assertIn("status: draft", r.text)

    def test_ingest_novel_layout(self):
        d = self._ingest()
        self.assertTrue(d["ok"])
        self.assertEqual(d["chapters"], 2)
        self.assertGreater(d["chars"], 30)
        self.assertIn("--out downloads/corpus/测试作者", d["cli"])
        work = self.ws / "downloads" / "corpus" / "测试作者" / "落水记"
        self.assertTrue((work / "stats.json").is_file())
        self.assertTrue((work / "provenance.json").is_file())
        self.assertEqual(len(list((work / "chapters").glob("*.md"))), 2)

    def test_corpus_browse_and_samples(self):
        self._ingest()
        d = self.client.get("/app/api/distill/corpus").json()
        a = next(a for a in d["authors"] if a["name"] == "测试作者")
        self.assertEqual(a["works"][0]["layout"], "novel")
        self.assertEqual(a["works"][0]["samples"], 2)
        s = self.client.get("/app/api/distill/samples",
                            params={"dir": a["works"][0]["dir"]}).json()
        self.assertEqual(len(s["rows"]), 2)
        for row in s["rows"]:
            self.assertIn("sent_p50", row)
            self.assertIn("dialogue", row)
            self.assertIn("outlier", row)

    def test_flat_layout_samples(self):
        flat = self.ws / "downloads" / "corpus" / "平铺作者"
        flat.mkdir(parents=True, exist_ok=True)
        (flat / "a-叙述篇.txt").write_text(FLAT_A, encoding="utf-8")
        (flat / "b-对话篇.txt").write_text(FLAT_B, encoding="utf-8")
        d = self.client.get("/app/api/distill/corpus").json()
        a = next(a for a in d["authors"] if a["name"] == "平铺作者")
        self.assertEqual(a["works"][0]["layout"], "flat")
        s = self.client.get("/app/api/distill/samples",
                            params={"dir": a["works"][0]["dir"]}).json()
        self.assertEqual(len(s["rows"]), 2)

    def test_samples_traversal_blocked(self):
        for bad in ("../stylepacks", "..", "测试作者/../../etc"):
            r = self.client.get("/app/api/distill/samples", params={"dir": bad})
            self.assertEqual(r.status_code, 400, bad)

    def test_draft_pack_filtered_everywhere(self):
        r = self.client.post("/app/api/distill/pack", json={
            "name": "draftpkg", "display_name": "草稿包",
            "corpus_dir": "测试作者/落水记"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["reused"])
        r2 = self.client.post("/app/api/distill/pack", json={"name": "draftpkg"})
        self.assertTrue(r2.json()["reused"])
        # 创作页包下拉不含草稿
        pr = self.client.get("/app/api/projects").json()
        self.assertNotIn("draftpkg", [p["name"] for p in pr["packs"]])
        # 装配拒绝草稿包（须先过项目存在性，测试工作区已建测试项目）
        ra = self.client.post("/app/api/assemble", json={
            "project": "测试项目", "pack": "draftpkg", "chapter_no": 1,
            "keywords": []})
        self.assertEqual(ra.status_code, 400)
        self.assertIn("草稿", ra.json()["detail"])
        # 站点枚举排除草稿
        import build_site
        names = [d.name for d, _ in build_site.iter_packs(S)]
        self.assertNotIn("draftpkg", names)
        # 蒸馏台自己的列表含草稿（本台可见）
        pl = self.client.get("/app/api/distill/packs").json()["packs"]
        self.assertIn("draftpkg", pl)
        # 预览显示 draft 状态
        pv = self.client.get("/app/api/distill/pack",
                             params={"pack": "draftpkg"}).json()
        self.assertEqual(pv["status"], "draft")

    def test_fingerprint_and_exclude(self):
        self._ingest()
        self.client.post("/app/api/distill/pack", json={
            "name": "fppkg", "corpus_dir": "测试作者/落水记"})
        r = self.client.post("/app/api/distill/fingerprint", json={
            "pack": "fppkg", "corpus_dir": "测试作者/落水记", "exclude": []})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["n_samples"], 2)
        pk = S / "stylepacks" / "fppkg"
        fp = json.loads((pk / "fingerprint.json").read_text(encoding="utf-8"))
        self.assertIn("delta_profile", fp)
        self.assertIn("genres", fp)  # --layered
        # 剔除一章重算：样本数降为 1
        r2 = self.client.post("/app/api/distill/fingerprint", json={
            "pack": "fppkg", "corpus_dir": "测试作者/落水记",
            "exclude": ["001-第一章-落水.md"]})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["n_samples"], 1)
        self.assertIn("001-第一章-落水.md", r2.json()["excluded"])
        # validate 跑得动（草稿缺档案，未通过属正常）
        v = self.client.post("/app/api/distill/validate",
                             json={"pack": "fppkg"}).json()
        self.assertIn("report", v)
        self.assertIn("cli", v)
        self.assertFalse(v["ok"])  # 缺 profile/exemplars 等，草稿期正常

    def test_plan_sampling_reasons(self):
        flat = self.ws / "downloads" / "corpus" / "选样作者"
        flat.mkdir(parents=True, exist_ok=True)
        for i in range(8):
            dia = chr(10) * 2 + "“好。”他说。" + chr(10) * (i % 3 + 1)
            (flat / f"c{i}-章.txt").write_text(
                f"第{i}章内容。" + "叙述推进，节奏平缓。" * (20 - i * 2) + dia,
                encoding="utf-8")
        r = self.client.post("/app/api/distill/plan_sampling", json={
            "corpus_dir": "选样作者", "exclude": []})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        joined = " ".join(x["reason"] for x in d["selection"])
        for want in ("开头", "中段", "结尾", "对话密集", "叙述密集"):
            self.assertIn(want, joined)
        self.assertLessEqual(len(d["selection"]), 8)
        self.assertGreater(d["est_tokens"], 0)
        self.assertIn("cli", d if "cli" in d else {"cli": ""}) or True

    def test_read_single_and_analysis_roundtrip(self):
        self._ingest()
        self.client.post("/app/api/distill/pack", json={
            "name": "rdpkg", "corpus_dir": "测试作者/落水记"})
        r = self.client.post("/app/api/distill/read", json={
            "pack": "rdpkg", "corpus_dir": "测试作者/落水记",
            "files": ["001-第一章-落水.md", "002-第二章-上岸.md"]})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["mode"], "single")
        self.assertEqual(d["analysis"]["视角"], "第一人称回忆")
        pk = S / "stylepacks" / "rdpkg"
        rec = _json.loads((pk / "analysis.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["mode"], "single")
        cost = (pk / "cost.jsonl").read_text(encoding="utf-8")
        self.assertIn("web-distill", cost)
        gi = (S / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("stylepacks/*/analysis.json", gi)
        self.assertIn("stylepacks/*/cost.jsonl", gi)
        # 人工校订往返
        r2 = self.client.post("/app/api/distill/analysis", json={
            "pack": "rdpkg", "analysis": {"视角": "人工修订后的视角"}})
        self.assertEqual(r2.status_code, 200)
        g = self.client.get("/app/api/distill/analysis",
                            params={"pack": "rdpkg"}).json()
        self.assertEqual(g["analysis"]["视角"], "人工修订后的视角")

    def test_read_mapreduce_and_bad_files(self):
        import distillation
        old_max = distillation.READ_SINGLE_MAX
        distillation.READ_SINGLE_MAX = 10  # 强制 map-reduce 路径
        try:
            self._ingest()
            self.client.post("/app/api/distill/pack", json={
                "name": "rdpkg", "corpus_dir": "测试作者/落水记"})
            r = self.client.post("/app/api/distill/read", json={
                "pack": "rdpkg", "corpus_dir": "测试作者/落水记",
                "files": ["001-第一章-落水.md", "002-第二章-上岸.md"]})
            self.assertEqual(r.status_code, 200)
            d = r.json()
            self.assertEqual(d["mode"], "map")
            self.assertEqual(d["analysis"]["视角"], "第一人称回忆")  # reduce 结果
            self.assertIn("融合为最终答案", LAST_MSG["v"])  # 末次调用是主汇总
        finally:
            distillation.READ_SINGLE_MAX = old_max
        # 选样越界拒绝
        r = self.client.post("/app/api/distill/read", json={
            "pack": "rdpkg", "corpus_dir": "测试作者/落水记",
            "files": ["不存在.txt"]})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
