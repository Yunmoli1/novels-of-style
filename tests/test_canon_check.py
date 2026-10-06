# -*- coding: utf-8 -*-
"""canon_terms_check 行为测试。运行：python -m unittest discover -s tests -v"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "canon_terms_check.py"


def run_check(terms: dict, files: dict[str, str], *extra: str) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as td:
        tpath = Path(td) / "terms.json"
        tpath.write_text(json.dumps(terms, ensure_ascii=False), encoding="utf-8")
        for name, text in files.items():
            (Path(td) / name).write_text(text, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--terms", str(tpath), *extra,
             *[str(Path(td) / n) for n in files]],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        return proc.returncode, proc.stdout + proc.stderr


BASE = {
    "work": "测试包",
    "must": [
        {"term": "艾莫号", "wrong": ["埃尔莫"]},
        {"term": "坍塌风暴", "wrong": []},
    ],
    "ban": [{"term": "埃尔莫", "reason": "错译"}],
    "thresholds": {"must_scope": "volume", "must_min_distinct": 2,
                   "concentration_advisory_per_1k": 1.0, "ban_zero": True},
}


class TestCanonTermsCheck(unittest.TestCase):
    def test_pass_volume(self):
        code, out = run_check(BASE, {"a.md": "艾莫号在坍塌风暴里前进。"})
        self.assertEqual(code, 0)
        self.assertIn("通过", out)

    def test_ban_hit_fails(self):
        code, out = run_check(BASE, {"a.md": "埃尔莫在坍塌风暴里前进。"})
        self.assertEqual(code, 1)
        self.assertIn("埃尔莫", out)
        self.assertIn("错译", out)

    def test_wrong_variant_counts_as_ban(self):
        terms = dict(BASE)
        terms["ban"] = []  # wrong 变体即使没进 ban 列表也该被拦
        code, out = run_check(terms, {"a.md": "埃尔莫号起锚。坍塌风暴来了。"})
        self.assertEqual(code, 1)
        self.assertIn("错写", out)

    def test_coverage_fail_volume(self):
        terms = dict(BASE)
        terms["thresholds"] = dict(BASE["thresholds"], must_min_distinct=2)
        code, out = run_check(terms, {"a.md": "只写了艾莫号，没写别的。"})
        self.assertEqual(code, 1)
        self.assertIn("坍塌风暴", out)

    def test_per_chapter_scope(self):
        terms = dict(BASE)
        terms["thresholds"] = dict(BASE["thresholds"],
                                   must_scope="chapter", must_min_distinct=2)
        files = {"001-a.md": "艾莫号在坍塌风暴里。",
                 "002-b.md": "艾莫号在夜里。"}
        code, _ = run_check(terms, files, "--per-chapter")
        self.assertEqual(code, 1)  # 002 缺 坍塌风暴
        files2 = {"001-a.md": "艾莫号在坍塌风暴里。",
                  "002-b.md": "艾莫号躲过坍塌风暴。"}
        code2, _ = run_check(terms, files2, "--per-chapter")
        self.assertEqual(code2, 0)

    def test_report_written(self):
        with tempfile.TemporaryDirectory() as td:
            tpath = Path(td) / "terms.json"
            tpath.write_text(json.dumps(BASE, ensure_ascii=False), encoding="utf-8")
            (Path(td) / "a.md").write_text("艾莫号在坍塌风暴里。", encoding="utf-8")
            rp = Path(td) / "r" / "report.md"
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--terms", str(tpath),
                 "--report", str(rp), str(Path(td) / "a.md")],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(proc.returncode, 0)
            self.assertTrue(rp.exists())
            self.assertIn("canon_terms_check 报告", rp.read_text(encoding="utf-8"))

    def test_bad_terms_usage_code_2(self):
        code, out = run_check({"work": "空包", "must": [], "ban": []},
                              {"a.md": "文本"})
        self.assertEqual(code, 2)


# --------------------------------------------------------------- validate/export

CANON_PACK = {
    "pack.json": json.dumps({
        "format_version": "1.0", "kind": "canon", "name": "testwork",
        "display_name": "测试作品 canon 包", "language": "zh",
        "version": "0.1.0", "created": "2026-10-06", "updated": "2026-10-06",
        "cast_policy": {"min_active_canon_chars_per_volume": 3,
                        "ooc_ref": "characters.json"},
        "provenance": [], "license_note": "测试",
        "changelog": ["0.1.0: test"],
    }, ensure_ascii=False),
    "terms.json": json.dumps(BASE, ensure_ascii=False),
    "characters.json": json.dumps({
        "roster": [{"name": "甲", "tier": "core", "role": "主角",
                    "redline": "不越界"},
                   {"name": "乙", "tier": "minor", "role": "路人"}],
    }, ensure_ascii=False),
    "card.md": "精华卡：事件原创、设定恪守。",
    "facts.md": "# 设定事实\n\n2074 年，污染区。",
    "conventions.md": "# 题材惯例\n\n先选场景再落术语。",
    "sources.md": ("| 来源 | 日期 |\n|---|---|\n"
                   "| https://example.com/wiki | 2026-10-06 |\n\n"
                   "## 版权声明\n\n测试声明。"),
}


def write_pack(files: dict[str, str]) -> Path:
    td = tempfile.TemporaryDirectory()
    pack = Path(td.name) / "pack"
    pack.mkdir(parents=True)
    for name, text in files.items():
        (pack / name).write_text(text, encoding="utf-8")
    # 保持 TemporaryDirectory 生命周期到断言结束
    write_pack._keep = td
    return pack


class TestCanonPackValidateExport(unittest.TestCase):
    def test_validate_canon_pass(self):
        import validate_pack
        pack = write_pack(CANON_PACK)
        errors, warns = validate_pack.check_pack(pack)
        self.assertEqual(errors, [], msg=str(warns))

    def test_validate_canon_missing_sources(self):
        import validate_pack
        files = dict(CANON_PACK)
        del files["sources.md"]
        errors, warns = validate_pack.check_pack(write_pack(files))
        self.assertTrue(any("sources.md" in e for e in errors))

    def test_validate_canon_quote_discipline(self):
        import validate_pack
        files = dict(CANON_PACK)
        files["facts.md"] = "# 设定事实\n\n> " + "原" * 120
        errors, _ = validate_pack.check_pack(write_pack(files))
        self.assertTrue(any("摘要纪律" in e for e in errors))

    def test_export_canon_single_file(self):
        import export_pack
        pack = write_pack(CANON_PACK)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out.md"
            export_pack._export_canon(pack, json.loads(CANON_PACK["pack.json"]), out)
            text = out.read_text(encoding="utf-8")
            self.assertIn("CANONPACK-SINGLE-FILE", text)
            self.assertIn("CanonPack：测试作品 canon 包", text)
            self.assertIn("术语三级表", text)

    def test_style_pack_regression(self):
        """canon 分支不得影响既有风格包校验。"""
        import validate_pack
        files = dict(CANON_PACK)
        files["pack.json"] = CANON_PACK["pack.json"].replace('"canon"', '"style"')
        errors, _ = validate_pack.check_pack(write_pack(files))
        # style 分支会报缺少风格包必备文件——证明走了 style 分支
        self.assertTrue(any("缺少必备文件" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
