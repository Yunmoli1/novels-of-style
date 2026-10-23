# -*- coding: utf-8 -*-
"""蒸馏工作台 v0.7.0 阶段 A 测试：语料入库/指纹/体检编排 + 草稿包过滤。
阶段 A 零模型调用——不需要 mock 模型服务器。"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

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
        cls.cfg_path = Path(cls.tmp.name) / "config.local.json"
        appstate.DEFAULT_CONFIG_PATH = cls.cfg_path
        cfg = appstate.load_config(cls.cfg_path)
        cfg["workspace_root"] = str(ws)
        appstate.save_config(cfg, cls.cfg_path)
        cls.client = TestClient(create_app(site_dir=S / "web" / "site"))
        cls.ws = ws

    @classmethod
    def tearDownClass(cls):
        for name in ("draftpkg", "fppkg"):  # 草稿包建在仓库 stylepacks/，测完即清
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


if __name__ == "__main__":
    unittest.main()
