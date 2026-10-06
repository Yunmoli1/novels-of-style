# -*- coding: utf-8 -*-
"""borrow_check 行为锁定：命中/不命中/阈值边界/规范化鲁棒性/错误路径。"""
import sys
import tempfile
import unittest
from pathlib import Path

from test_gbk_console import _run  # 复用统一的子进程运行器（encoding=utf-8）

S = Path(__file__).resolve().parent.parent
SCRIPT = S / "scripts" / "borrow_check.py"

EXEMPLARS = """# 范例

### 1. 测试范例

> 曲曲折折的荷塘上面，弥望的是田田的叶子。叶子出水很高，像亭亭的舞女的裙。

批注：测试。

"""


class TestBorrowCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pack = Path(self.tmp.name) / "pack"
        self.pack.mkdir()
        (self.pack / "exemplars.md").write_text(EXEMPLARS, encoding="utf-8")

    def _draft(self, text: str) -> str:
        p = Path(self.tmp.name) / "draft.txt"
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_clean_draft_passes(self):
        r = _run([sys.executable, str(SCRIPT), self._draft("今天天气很好，我们出门散步，看到许多花开了。"),
                  "--pack", str(self.pack)])
        self.assertEqual(r.returncode, 0, (r.stdout or "") + (r.stderr or ""))
        self.assertIn("未发现", r.stdout)

    def test_verbatim_borrow_flagged(self):
        r = _run([sys.executable, str(SCRIPT),
                  self._draft("推开窗，曲曲折折的荷塘上面，弥望的是田田的叶子，我看得出了神。"),
                  "--pack", str(self.pack)])
        self.assertEqual(r.returncode, 1, (r.stdout or "") + (r.stderr or ""))
        self.assertIn("范例 1", r.stdout)

    def test_short_common_phrase_not_flagged(self):
        r = _run([sys.executable, str(SCRIPT), self._draft("她穿着黑色的裙子站在门口，没有说话。"),
                  "--pack", str(self.pack)])
        self.assertEqual(r.returncode, 0, (r.stdout or "") + (r.stderr or ""))

    def test_punctuation_variant_still_flagged(self):
        r = _run([sys.executable, str(SCRIPT),
                  self._draft('只见那\n"曲曲折折的荷塘上面，弥望的是田田的叶子。"……他停住了。'),
                  "--pack", str(self.pack)])
        self.assertEqual(r.returncode, 1, (r.stdout or "") + (r.stderr or ""))

    def test_threshold_boundary(self):
        text = self._draft("弥望的是田田的叶子，我看得出了神。")  # 11 字重叠
        lenient = _run([sys.executable, str(SCRIPT), text, "--pack", str(self.pack), "--min-len", "8"])
        self.assertEqual(lenient.returncode, 1)
        strict = _run([sys.executable, str(SCRIPT), text, "--pack", str(self.pack), "--min-len", "12"])
        self.assertEqual(strict.returncode, 0)

    def test_missing_pack_errors(self):
        r = _run([sys.executable, str(SCRIPT), self._draft("随意一段话。"),
                  "--pack", str(Path(self.tmp.name) / "nope")])
        self.assertEqual(r.returncode, 2)
        self.assertIn("错误", r.stderr)


if __name__ == "__main__":
    unittest.main()
