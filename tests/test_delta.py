# -*- coding: utf-8 -*-
"""v0.2 测试：Burrows Delta 档案的距离分离能力（合成语料 + 真实包交叉验证）。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import splib  # noqa: E402

CORPUS_DIR = ROOT.parent / "corpus"  # 工作区语料（不入库；缺席则跳过真实包验证）


class TestDeltaSynthetic(unittest.TestCase):
    def test_separation(self):
        a0, a1 = "的了是在我", "有人这不说"
        b0, b1 = "着子地很那", "个也下去到"
        # 三个样本各带偏斜，保证档案内 std > 0
        a_samples = [a0 * 150, a1 * 150, (a0 + a1) * 75]
        b_samples = [b0 * 150, b1 * 150, (b0 + b1) * 75]
        prof_a = splib.build_delta_profile(a_samples)
        prof_b = splib.build_delta_profile(b_samples)
        cand_a = (a0 + a1) * 40 + "乙" * 20
        d_a = splib.delta_distance(cand_a, prof_a)
        d_b = splib.delta_distance(cand_a, prof_b)
        self.assertLess(d_a, d_b)
        cand_b = (b0 + b1) * 40 + "丙" * 20
        self.assertLess(splib.delta_distance(cand_b, prof_b),
                        splib.delta_distance(cand_b, prof_a))


@unittest.skipUnless(CORPUS_DIR.is_dir(), "工作区语料不存在（CI 环境），跳过真实交叉验证")
class TestDeltaRealPacks(unittest.TestCase):
    def test_cross_validation(self):
        lux_fp = splib.load_json(ROOT / "stylepacks" / "luxun" / "fingerprint.json")
        zhu_fp = splib.load_json(ROOT / "stylepacks" / "zhuziqing" / "fingerprint.json")
        self.assertIn("delta_profile", lux_fp)
        self.assertIn("delta_profile", zhu_fp)
        correct = total = 0
        for author, own in (("luxun", lux_fp), ("zhuziqing", zhu_fp)):
            other = zhu_fp if author == "luxun" else lux_fp
            for f in sorted((CORPUS_DIR / author).rglob("chapters/*.md")):
                text, _ = splib.read_text(f)
                if splib._clen(text) < 200:
                    continue
                total += 1
                d_own = splib.delta_distance(text, own["delta_profile"])
                d_other = splib.delta_distance(text, other["delta_profile"])
                if d_own < d_other:
                    correct += 1
        self.assertGreater(total, 0)
        self.assertGreaterEqual(correct / total, 0.9)  # 目标 ≥ 9/10


if __name__ == "__main__":
    unittest.main()
