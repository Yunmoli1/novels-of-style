# -*- coding: utf-8 -*-
"""v0.2.3 测试：文体分层指纹——检测器、散布容差、层内留一、统一验收路径。"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import splib  # noqa: E402


def _essay_text(seed: int, paras: int = 30) -> str:
    """无对话的散文：长句、零引号。seed 控制句长微变化。"""
    out = []
    for i in range(paras):
        n = 2 + (i + seed) % 3
        sents = []
        for j in range(n):
            ln = 26 + ((i * 7 + j * 5 + seed * 3) % 14)
            sents.append("时光沿着旧墙慢慢流成一线" * (ln // 12))
        out.append("。".join(sents) + "。")
    return "\n\n".join(out)


def _narr_text(seed: int, paras: int = 30) -> str:
    """对话驱动的叙事：段落以引号开头（段首引号信号 + 引号字占比双高）。"""
    out = []
    for i in range(paras):
        if (i + seed) % 5 < 3:
            out.append("“你到底去不去？”他把碗往桌上一放，碗沿磕出一个小口。")
        else:
            out.append("他没答话，起身推门出去了，街上正落着细雨，行人稀少得很。")
    return "\n\n".join(out)


def _inline_narr_text(paras: int = 30) -> str:
    """对话全部嵌在叙述段中间（段首无引号）——孔乙己型，靠引号字占比识别。"""
    out = []
    for i in range(paras):
        out.append("他站着说道，“窃书不能算偷……读书人的事，能算偷么？”"
                   "接连便是难懂的话，引得众人都哄笑起来，店内外充满了快活的空气。")
    return "\n\n".join(out)


class TestDetectGenre(unittest.TestCase):
    def test_narrative_essay_and_inline(self):
        d1 = splib.detect_genre(_narr_text(0))
        self.assertEqual(d1["genre"], "narrative")
        d2 = splib.detect_genre(_essay_text(0))
        self.assertEqual(d2["genre"], "essay")
        # 孔乙己型：对话不居段首，靠引号字占比识别（v0.2.1 教训）
        d3 = splib.detect_genre(_inline_narr_text())
        self.assertEqual(d3["genre"], "narrative")
        self.assertGreaterEqual(d3["quote_char_ratio"], 0.12)

    def test_confidence_degrades_near_boundary(self):
        # 造一个信号落在边界附近的文本：引号字占比 ≈ 0.12
        base = "墙外的枣树落尽了叶子，天空奇怪而高。"
        quoted = "他说，“走。”"
        paras = [base] * 10 + [quoted] * 4
        d = splib.detect_genre("\n\n".join(paras))
        self.assertEqual(d["confidence"], "medium")


class TestLayersAndLOO(unittest.TestCase):
    def _corpus(self):
        return [("文甲", _narr_text(0)), ("文乙", _narr_text(1)), ("文丙", _narr_text(2)),
                ("散甲", _essay_text(0)), ("散乙", _essay_text(1))]

    def test_layers_split_and_threshold_pass_own_line(self):
        out = splib.build_genre_layers(self._corpus())
        genres = out["genres"]
        self.assertEqual(set(genres), {"narrative", "essay"})
        self.assertEqual(genres["narrative"]["samples"], ["文甲", "文乙", "文丙"])
        # 散布容差：层内每篇真迹必须过本层线（v0.2.3 的核心验收）
        for g, layer in genres.items():
            tree = layer["metrics"]
            self.assertGreaterEqual(len(list(splib.iter_target_leaves(tree))), 5)
            for name in layer["samples"]:
                text = dict(self._corpus())[name]
                m = splib.compute_metrics(text)
                splib.fill_missing_rates(m, tree)
                rows = splib.compare_metrics(m, {"metrics": tree})
                bad = [r["path"] for r in rows if not r["ok"]]
                self.assertFalse(bad, f"{name} 未过本层 {g} 线：{bad}")

    def test_loo_n_guard(self):
        loo = splib.leave_one_out(self._corpus())
        self.assertIsNone(loo["essay"]["delta_max"])          # n=2 → 线不可标定
        self.assertIn("note", loo["essay"])
        self.assertIsInstance(loo["narrative"]["delta_max"], float)  # n=3 → 真线
        self.assertGreaterEqual(loo["narrative"]["delta_max"], 0.0)

    def test_loo_discriminates_wrong_author(self):
        loo = splib.leave_one_out(self._corpus())
        prof = splib.build_genre_layers(self._corpus())["genres"]["narrative"]["delta_profile"]
        alien = splib.delta_distance(_essay_text(9), prof)
        self.assertGreater(alien, loo["narrative"]["delta_p50"])


class TestLayeredCheck(unittest.TestCase):
    def _fingerprint(self):
        corpus = self._corpus()
        layers = splib.build_genre_layers(corpus)
        return {"metrics": {}, "genres": layers["genres"],
                "self_check": splib.leave_one_out(corpus)}

    _corpus = TestLayersAndLOO._corpus

    def test_auto_layer_and_genuine_pass(self):
        fp = self._fingerprint()
        res = splib.layered_check(_narr_text(3), fp)
        self.assertEqual(res["layer_used"], "narrative")
        self.assertTrue(res["ok"])
        self.assertTrue(res["delta_counted"])                 # n=3 → 留一线生效
        res2 = splib.layered_check(_essay_text(3), fp)
        self.assertEqual(res2["layer_used"], "essay")
        self.assertFalse(res2["delta_counted"])               # n=2 → 不进判定

    def test_short_text_delta_not_counted(self):
        fp = self._fingerprint()
        res = splib.layered_check(_narr_text(4)[:300], fp)
        self.assertFalse(res["delta_counted"])
        self.assertIn("仅为参考", res["delta_note"])

    def test_genre_all_uses_mixed(self):
        fp = self._fingerprint()
        res = splib.layered_check(_narr_text(5), fp, genre="all")
        self.assertEqual(res["layer_used"], "all(混合)")


class TestGenericAuthorPipeline(unittest.TestCase):
    """任意作者端到端：合成语料 → build_delta --layered 建包 → fp_check 验收。

    本项目不针对任何特定作者——分层机制必须对任意语料同构可用，
    本测试全程不触碰自带包（luxun/zhuziqing）。
    """

    def test_build_then_check_cli(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            corpus = root / "corpus" / "某作者"
            for name, text in [("篇甲", _narr_text(0)), ("篇乙", _narr_text(1)),
                               ("篇丙", _narr_text(2)),
                               ("章甲", _essay_text(0)), ("章乙", _essay_text(1))]:
                d = corpus / name / "chapters"
                d.mkdir(parents=True)
                (d / f"001-{name}.md").write_text(text, encoding="utf-8")
            pack = root / "pack"
            pack.mkdir()
            (pack / "fingerprint.json").write_text("{}", encoding="utf-8")

            build = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_delta.py"),
                 str(corpus), "--pack", str(pack), "--layered"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120)
            self.assertEqual(build.returncode, 0, build.stderr)
            self.assertIn("层 narrative", build.stdout)
            self.assertIn("层 essay", build.stdout)
            self.assertIn("不可标定", build.stdout)      # essay n=2 → 线如实置空
            fp = splib.load_json(pack / "fingerprint.json")
            self.assertIn("genres", fp)
            self.assertIn("self_check", fp)
            self.assertIsNotNone(fp["genres"]["narrative"]["delta_profile"])
            self.assertIsNone(fp["genres"]["essay"]["delta_profile"])

            # 层内真迹过线（CLI 全链路，auto 选层）
            genuine = corpus / "篇甲" / "chapters" / "001-篇甲.md"
            check = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "fp_check.py"),
                 str(pack), str(genuine)],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120)
            self.assertEqual(check.returncode, 0, check.stdout)
            self.assertIn("阈值层：narrative", check.stdout)

            # 强制错层 → 必须拒绝（散文文本按小说阈值判）
            alien = root / "alien.md"
            alien.write_text(_essay_text(9), encoding="utf-8")
            bad = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "fp_check.py"),
                 str(pack), str(alien), "--genre", "narrative"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120)
            self.assertEqual(bad.returncode, 1, bad.stdout)


class TestFPCheckCLI(unittest.TestCase):
    def test_cli_layered_exit_codes(self):
        real_pack = ROOT / "stylepacks" / "luxun"
        if not (real_pack / "fingerprint.json").is_file():
            self.skipTest("仓库内无 luxun 包")
        with tempfile.TemporaryDirectory() as td:
            ok_file = Path(td) / "ok.txt"
            ok_file.write_text(_narr_text(0) * 3, encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "fp_check.py"),
                 str(real_pack), str(ok_file), "--genre", "all"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120)
            self.assertIn(r.returncode, (0, 1))               # 分层包上混合层可判
            self.assertIn("文体判定", r.stdout)                # 分层元信息出现在报告里
            bad_args = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "fp_check.py"),
                 str(Path(td) / "no-such-pack"), str(ok_file)],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=60)
            self.assertEqual(bad_args.returncode, 2)          # 用法错误


if __name__ == "__main__":
    unittest.main()
