# -*- coding: utf-8 -*-
"""web 阶段 0 红线锁定（r4）：产物无全文、判读页无答案、计分/迁移/入口行为。

基线口径说明：pytest 计 subTest 为独立项（v0.4.2 起 CI 基线以此为准）。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from test_gbk_console import _run

S = Path(__file__).resolve().parent.parent
WEB = S / "web"
BUILD = WEB / "build_site.py"
LAUNCH = WEB / "launch.py"
MIGRATE = S / "scripts" / "migrate_human_judging.py"
SCORE = S / "scripts" / "score_human_judging.py"

PACK_FIXTURE = """# 判读包

## 回合 1（测试作者）· 题：题目一

【甲】
甲的第一段。

【乙】
乙的第一段。

**你的判读**：______

## 回合 2（测试作者）· 题：题目二

【甲】
甲的第二段。

【乙】
乙的第二段。

**你的判读**：______
"""

ANS_FIXTURE = """# 答案卷

| 回合 | 甲 | 乙 | 带包臂 | 子代理判官的判读（参考） |
|---|---|---|---|---|
| 1 题目一 | 无包 | **带包** | 乙 | 带包胜（高）——注 A |
| 2 题目二 | **带包** | 无包 | 甲 | 无包胜（中）——注 B |
"""


class TestBuildSite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = Path(self.tmp.name) / "site"
        r = _run([sys.executable, str(BUILD), "--out", str(self.site)],
                 timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.pages = list(self.site.rglob("*.html"))
        self.content = "\n".join(p.read_text(encoding="utf-8") for p in self.pages)

    def test_pages_exist(self):
        for rel in ("index.html", "judging/index.html", "packs/index.html",
                    "packs/luxun/index.html", "packs/zhuziqing/index.html",
                    "style.css"):
            self.assertTrue((self.site / rel).is_file(), rel)

    def test_pack_page_renders_sections(self):
        t = (self.site / "packs" / "zhuziqing" / "index.html").read_text(encoding="utf-8")
        for word in ("文风档案 profile", "思想档案 thought", "范例 exemplars",
                     "测量可视化", "留一及格线", "motif 频率"):
            self.assertIn(word, t)
        self.assertIn("v0.4.3", t)
        self.assertIn("永不进判定", t)

    def test_judging_page_rounds_without_answers(self):
        j = (self.site / "judging" / "index.html").read_text(encoding="utf-8")
        for word in ("回合 1", "回合 8", "冬天的集市", "老宅的院子", "导出判读结果"):
            self.assertIn(word, j)
        for bad in ("乙甲乙甲甲乙乙乙", "packed_arm", "subagent_winner"):
            self.assertNotIn(bad, j)
        ans = S / "evals" / "human_judging_answers.json"
        if ans.is_file():  # 本机存在答案卷时：产物树不得出现其内容
            note = json.loads(ans.read_text(encoding="utf-8"))["rounds"][0]["subagent_note"][:16]
            self.assertNotIn(note, self.content)
        self.assertFalse((self.site / "human_judging_answers.json").exists())

    def test_no_corpus_fulltext_in_products(self):
        corpus = S.parent / "downloads" / "corpus"
        if not corpus.is_dir():
            self.skipTest("本机无语料目录（CI 用例侧跳过）")
        import random
        rng = random.Random(20261007)
        checked = 0
        for txt in corpus.rglob("*.txt"):
            text = txt.read_text(encoding="utf-8", errors="ignore")
            if len(text) < 400:
                continue
            for _ in range(3):
                i = rng.randrange(0, len(text) - 260)
                window = text[i:i + 250]  # > 短引上限 200，命中即全文泄漏
                self.assertNotIn(window, self.content, f"{txt.name} 全文窗口泄漏")
                checked += 1
        self.assertGreater(checked, 0)

    def test_judging_json_invariants(self):
        j = json.loads((S / "evals" / "human_judging.json").read_text(encoding="utf-8"))
        self.assertEqual(len(j["rounds"]), 8)
        for r in j["rounds"]:
            self.assertTrue(r["甲"].strip() and r["乙"].strip(), r["id"])
            self.assertNotIn("带包", r["甲"] + r["乙"], f"回合 {r['id']} 文本夹带答案提示")


class TestScore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_perfect_packed_follow_scores(self):
        ans_path = S / "evals" / "human_judging_answers.json"
        if not ans_path.is_file():
            self.skipTest("本机无答案卷（migrate 未跑）")
        ans = json.loads(ans_path.read_text(encoding="utf-8"))
        results = {"exported_at": "t", "protocol": "test",
                   "rounds": [{"id": a["id"], "choice": a["packed_arm"]}
                              for a in ans["rounds"]]}
        rf = Path(self.tmp.name) / "r.json"
        rf.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
        r = _run([sys.executable, str(SCORE), str(rf)], timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("① 辨认带包臂：8/8", r.stdout)
        self.assertIn("② 与子代理判官一致：6/8", r.stdout)
        self.assertIn("一致率高", r.stdout)

    def test_missing_answers_guides_migrate(self):
        rf = Path(self.tmp.name) / "r.json"
        rf.write_text('{"rounds": []}', encoding="utf-8")
        r = _run([sys.executable, str(SCORE), str(rf), "--answers",
                  str(Path(self.tmp.name) / "nope.json")], timeout=120)
        self.assertEqual(r.returncode, 2)
        self.assertIn("migrate_human_judging", r.stderr)


class TestMigrate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_guard_rejects_truncated_package(self):
        pack = Path(self.tmp.name) / "p.md"
        ans = Path(self.tmp.name) / "a.md"
        pack.write_text(PACK_FIXTURE, encoding="utf-8")
        ans.write_text(ANS_FIXTURE, encoding="utf-8")
        r = _run([sys.executable, str(MIGRATE), "--pack", str(pack),
                  "--answers", str(ans),
                  "--out-judging", str(Path(self.tmp.name) / "j.json"),
                  "--out-answers", str(Path(self.tmp.name) / "o.json")],
                 timeout=120)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("回合数断言失败", r.stderr)

    def test_fixture_two_round_answer_mapping(self):
        """2 回合夹具过不了 8 回合守卫，但答案映射逻辑可经真实迁移产物反向验证。"""
        if not (S / "evals" / "human_judging_answers.json").is_file():
            self.skipTest("本机无答案卷（CI 无此 gitignore 文件）")
        j = json.loads((S / "evals" / "human_judging.json").read_text(encoding="utf-8"))
        a = json.loads((S / "evals" / "human_judging_answers.json").read_text(encoding="utf-8"))
        self.assertEqual([r["id"] for r in j["rounds"]], [x["id"] for x in a["rounds"]])
        for r, x in zip(j["rounds"], a["rounds"]):
            self.assertEqual(r["title"], x["title"])
            self.assertIn(x["packed_arm"], ("甲", "乙"))
            self.assertIn(x["subagent_winner"], ("甲", "乙"))


class TestLauncher(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_launch_build_only_hermetic(self):
        out = Path(self.tmp.name) / "site"
        r = _run([sys.executable, str(LAUNCH), "--build-only",
                  "--site", str(out)], timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((out / "index.html").is_file())

    def test_bat_entry_exists_and_wired(self):
        bat = S / "启动工作台.bat"
        self.assertTrue(bat.is_file(), "双击入口缺失")
        raw = bat.read_bytes()
        # cmd 解析 LF-only 批处理时 goto/标签不可靠（v0.5.2 启动失败的根因）——
        # 行尾必须是 CRLF，行为锁定
        crlf = b"\r\n"
        self.assertIn(crlf, raw, "bat 必须是 CRLF 行尾")
        self.assertNotIn(b" \n", raw.replace(crlf, b""))
        content = raw.decode("utf-8")
        self.assertIn("launch.py", content)
        self.assertIn("pause", content)
        self.assertIn("%*", content)  # 参数透传（--port/--build-only 等）

    def test_redline_localhost_binding(self):
        src = LAUNCH.read_text(encoding="utf-8")
        self.assertIn('ThreadingHTTPServer(("127.0.0.1", port)', src)
        self.assertNotIn('("0.0.0.0"', src)


if __name__ == "__main__":
    unittest.main()
