# -*- coding: utf-8 -*-
"""thought.md 思想层（v0.3）：validate 正负例 + export 条件段 + fp_check --thought + motif_count。"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import export_pack  # noqa: E402
import fp_check  # noqa: E402
import motif_count  # noqa: E402
import splib  # noqa: E402
import validate_pack  # noqa: E402

ZH = ROOT / "stylepacks" / "zhuziqing"

THOUGHT = """# 朱自清思想层（thought）

## 选题地平线
写家庭、旅途、自然片段；回避宏大叙事与时代论断。

## 立意动作
- 以小见大：一件小物引出人情。

## 观察清单
手的动作、光的移动、植物的姿态。

## 意象系统
核心意象族：月夜、水、灯火。
motif 词表：月光、背影、雪

## 价值姿态
叙述者贴着人物走，含蓄不评判。

## 禁区
经历、时代所指——写了也不像，宁可平实。
"""

CORPUS_A = "月光如流水一般，静静地泻在荷叶上。月光照亮了塘边的柳影，也照亮了灯。"
CORPUS_B = "我看见他戴着黑布小帽，蹒跚地走到铁道边。月光下，灯还亮着。"


class ThoughtBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.pack = Path(self.tmp.name) / "zhuziqing"
        shutil.copytree(ZH, self.pack)
        # zhuziqing 自 v0.3 起自带 thought.md 与 thought 标记；测试基座统一剥掉，
        # 使"老包"（无 thought.md）与"新包"（各用例自行写入 fixture）两条路径皆可确定性地测
        (self.pack / "thought.md").unlink(missing_ok=True)
        pj_path = self.pack / "pack.json"
        pj = json.loads(pj_path.read_text(encoding="utf-8"))
        pj.pop("thought", None)
        pj_path.write_text(json.dumps(pj, ensure_ascii=False, indent=2), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def errs(self) -> list[str]:
        errors, _ = validate_pack.check_pack(self.pack)
        return errors

    def warns(self) -> list[str]:
        _, warns = validate_pack.check_pack(self.pack)
        return warns


class TestValidateThought(ThoughtBase):
    def test_legacy_pack_passes_with_one_hint(self):
        self.assertEqual(self.errs(), [])
        self.assertTrue(any("包无 thought.md" in w for w in self.warns()))

    def test_complete_thought_no_errors(self):
        (self.pack / "thought.md").write_text(THOUGHT, encoding="utf-8")
        self.assertEqual(self.errs(), [])
        self.assertTrue(any('"thought": true' in w or "thought" in w for w in self.warns()))

    def test_missing_section_is_error(self):
        (self.pack / "thought.md").write_text(
            THOUGHT.replace("## 观察清单\n手的动作、光的移动、植物的姿态。\n\n", ""),
            encoding="utf-8")
        self.assertTrue(any("缺少章节：「观察清单」" in e for e in self.errs()))

    def test_missing_motif_list_is_error(self):
        (self.pack / "thought.md").write_text(
            THOUGHT.replace("motif 词表：月光、背影、雪\n", ""), encoding="utf-8")
        self.assertTrue(any("motif 词表" in e for e in self.errs()))

    def test_flag_true_without_file(self):
        pj_path = self.pack / "pack.json"
        pj = json.loads(pj_path.read_text(encoding="utf-8"))
        pj["thought"] = True
        pj_path.write_text(json.dumps(pj, ensure_ascii=False, indent=2), encoding="utf-8")
        self.assertTrue(any("thought: true，但包内缺少" in e for e in self.errs()))


class TestSplibThought(unittest.TestCase):
    def test_parse_motif_list(self):
        self.assertEqual(splib.parse_motif_list(THOUGHT), ["月光", "背影", "雪"])
        self.assertEqual(splib.parse_motif_list("没有词表行"), [])

    def test_count_motifs(self):
        rates = splib.count_motifs(CORPUS_A, ["月光", "雪"])
        self.assertGreater(rates["月光"], 0)
        self.assertEqual(rates["雪"], 0.0)
        self.assertEqual(splib.count_motifs("", ["月"]), {"月": 0.0})


class TestExportThought(ThoughtBase):
    def _export(self) -> str:
        out = Path(self.tmp.name) / "out.md"
        with mock.patch.object(sys, "argv",
                               ["export_pack.py", str(self.pack), "--out", str(out)]):
            self.assertEqual(export_pack.main(), 0)
        return out.read_text(encoding="utf-8")

    def test_export_with_thought(self):
        (self.pack / "thought.md").write_text(THOUGHT, encoding="utf-8")
        text = self._export()
        self.assertIn("## 思想档案", text)
        self.assertLess(text.index("## 思想档案"), text.index("## 附录：量化指纹"))
        self.assertIn("思想档案」", text)  # preamble 提示

    def test_export_legacy_unchanged(self):
        text = self._export()
        self.assertNotIn("## 思想档案", text)
        self.assertNotIn("思想档案」", text)


class TestFPCheckThought(ThoughtBase):
    def _run(self, flag: bool) -> tuple[int, str]:
        txt = Path(self.tmp.name) / "t.txt"
        txt.write_text(CORPUS_A + CORPUS_B, encoding="utf-8")
        argv = ["fp_check.py", str(self.pack), str(txt)]
        if flag:
            argv.append("--thought")
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(buf), \
                contextlib.redirect_stderr(io.StringIO()):
            rc = fp_check.main()
        return rc, buf.getvalue()

    def test_thought_flag_advisory_only(self):
        (self.pack / "thought.md").write_text(THOUGHT, encoding="utf-8")
        rc_plain, out_plain = self._run(False)
        rc_thought, out_thought = self._run(True)
        self.assertEqual(rc_plain, rc_thought)  # 退出码不受 --thought 影响
        self.assertNotIn("motif 密度对照", out_plain)
        self.assertIn("motif 密度对照", out_thought)
        self.assertIn("advisory", out_thought)

    def test_thought_flag_without_file(self):
        rc, out = self._run(True)
        self.assertIn("包无 thought.md", out)


class TestMotifCount(ThoughtBase):
    def _corpus(self) -> Path:
        d = Path(self.tmp.name) / "corpus"
        d.mkdir()
        (d / "a.txt").write_text(CORPUS_A * 5, encoding="utf-8")
        (d / "b.txt").write_text(CORPUS_B * 5, encoding="utf-8")
        return d

    def _run(self, corpus: Path, write: bool) -> tuple[int, str]:
        argv = ["motif_count.py", str(corpus), "--pack", str(self.pack)]
        if write:
            argv.append("--write")
        buf = io.StringIO()
        err = io.StringIO()
        with mock.patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            rc = motif_count.main()
        return rc, buf.getvalue() + err.getvalue()

    def test_validate_and_write_back(self):
        (self.pack / "thought.md").write_text(THOUGHT, encoding="utf-8")
        corpus = self._corpus()
        rc, out = self._run(corpus, write=False)
        self.assertEqual(rc, 0)
        self.assertIn("剔除", out)  # 雪 在 fixture 语料中未出现 → 低于 1.5/千字

        rc, out = self._run(corpus, write=True)
        self.assertEqual(rc, 0)
        thought = (self.pack / "thought.md").read_text(encoding="utf-8")
        self.assertIn("## motif_stats", thought)
        self.assertIn("月光", splib.parse_motif_list(thought))
        self.assertNotIn("雪", splib.parse_motif_list(thought))  # 被剔除
        self.assertGreater(splib.parse_motif_stats(thought)["月光"], 0)

        pj = json.loads((self.pack / "pack.json").read_text(encoding="utf-8"))
        self.assertTrue(any("motif_stats" in c["changes"] for c in pj["changelog"]))

    def test_all_below_threshold(self):
        (self.pack / "thought.md").write_text(
            THOUGHT.replace("motif 词表：月光、背影、雪", "motif 词表：雪、霜"), encoding="utf-8")
        rc, _ = self._run(self._corpus(), write=True)
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
