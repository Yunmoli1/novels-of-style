# -*- coding: utf-8 -*-
"""registers.md 调子分区校验（R0）：validate (a)-(f) 正负例 + export 条件合并。"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import export_pack  # noqa: E402
import validate_pack  # noqa: E402

LUXUN = ROOT / "stylepacks" / "luxun"


class RegistersBase(unittest.TestCase):
    """以真实 luxun 包的临时副本为正例，变异出各负例。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.pack = Path(self.tmp.name) / "luxun"
        shutil.copytree(LUXUN, self.pack)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def errs(self) -> list[str]:
        errors, _ = validate_pack.check_pack(self.pack)
        return errors

    def warns(self) -> list[str]:
        _, warns = validate_pack.check_pack(self.pack)
        return warns

    def replace_in(self, rel: str, old: str, new: str) -> None:
        p = self.pack / rel
        p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


class TestRegistersPositive(RegistersBase):
    def test_luxun_copy_validates_clean(self):
        self.assertEqual(self.errs(), [])

    def test_capability_flag_consistent(self):
        self.assertFalse(any("registers" in w for w in self.warns()))


class TestRegistersNegative(RegistersBase):
    def test_a_dangling_reference(self):
        self.replace_in("registers.md", "示范段 10", "示范段 10、示范段 99")
        self.assertTrue(any("在 exemplars.md 中不存在" in e for e in self.errs()))

    def test_b_tone_value_out_of_domain(self):
        self.replace_in("exemplars.md", "调子：沉郁哲思", "调子：忧郁哲思")
        self.assertTrue(any("未在 registers.md 分区定义中出现" in e for e in self.errs()))

    def test_b_tone_without_registers_file(self):
        (self.pack / "registers.md").unlink()
        errors = self.errs()
        self.assertTrue(any("缺少 registers.md" in e for e in errors))

    def test_flag_true_without_file(self):
        (self.pack / "registers.md").unlink()
        self.assertTrue(any("registers: true，但包内缺少" in e for e in self.errs()))

    def test_flag_missing_warns(self):
        self.replace_in("pack.json", '"registers": true,', '"registers": false,')
        self.assertTrue(any("registers" in w for w in self.warns()))

    def test_c_name_clash_with_exemplar_title(self):
        self.replace_in("registers.md", "#### 沉郁哲思", "#### 重复凝视式开场")
        self.assertTrue(any("跨文件查重" in e for e in self.errs()))

    def test_e_quote_too_long(self):
        self.replace_in(
            "registers.md", "### 沉郁哲思\n示范段 1",
            "### 沉郁哲思\n示范段 1\n\n> " + "长" * 201,
        )
        self.assertTrue(any("registers.md 引文超 200 字" in e for e in self.errs()))

    def test_f_mirror_forward_unlisted(self):
        self.replace_in("registers.md", "### 沉郁哲思\n示范段 1", "### 沉郁哲思\n")
        self.assertTrue(any("未列入 registers.md 示范段路由" in e for e in self.errs()))

    def test_f_mirror_reverse_tone_mismatch(self):
        self.replace_in("exemplars.md", "调子：对话场", "调子：白描场")
        errors = self.errs()
        self.assertTrue(any("调子为「白描场」" in e for e in errors))

    def test_f_mirror_reverse_untagged(self):
        self.replace_in("exemplars.md", "调子：白描场\n", "")
        self.assertTrue(any("未标注调子" in e for e in self.errs()))


class TestRegistersExport(RegistersBase):
    def _export(self) -> str:
        out = Path(self.tmp.name) / "out.md"
        with mock.patch.object(sys, "argv",
                               ["export_pack.py", str(self.pack), "--out", str(out)]):
            rc = export_pack.main()
        self.assertEqual(rc, 0)
        return out.read_text(encoding="utf-8")

    def test_export_contains_registers_in_prose(self):
        text = self._export()
        self.assertIn("## 调子分区", text)
        # 断言落在正文区段（JSON 附录之前），而非附录
        self.assertLess(text.index("## 调子分区"), text.index("## 附录：量化指纹"))
        self.assertIn("### 沉郁哲思", text)
        self.assertIn("示范段 12", text)

    def test_export_legacy_pack_unchanged(self):
        (self.pack / "registers.md").unlink()
        text = self._export()
        # 断言节标题不存在（pack.json 的 changelog 文字里允许出现"调子分区"字样）
        self.assertNotIn("## 调子分区", text)
        for title in ("精华卡", "完整档案", "范例", "词汇与句式", "能力边界"):
            self.assertIn(f"## {title}", text)


if __name__ == "__main__":
    unittest.main()
