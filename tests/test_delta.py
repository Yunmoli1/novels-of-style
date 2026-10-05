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
    def _layer_profile(self, fp: dict, g: str) -> dict:
        layer = fp.get("genres", {}).get(g)
        return (layer or {}).get("delta_profile") or fp["delta_profile"]

    def test_cross_validation_metric_global_basis(self):
        """跨包作者归因（v0.4.0 仪器修正：度量空间 + 全局字符基准）。

        仪器修正的依据（v0.3.1→v0.4.0 执行记录）：
        - 旧仪器（各自包的 delta_profile，即各自 top-150 字符集）随基准选择
          **翻转方向**：15 篇评测集上 luxun 0/5、大语料上又 62/62，p 全不显著——
          v0.2.8 的 7/9 属仪器伪影；zhuziqing n=4 时代的 2/4 亦为档案自含过拟合
        - 度量空间（12 维句法度量）+ 全局字符基准：**13/15（0.867），p=0.004
          （置换 n=500，seed 20260930）**，两侧 ≥0.8——与 Case J 的仪器纪律同源
        """
        named, labels = [], {}
        for author in ("luxun", "zhuziqing"):
            for f in sorted((CORPUS_DIR / author).rglob("*.md")):
                text, _ = splib.read_text(f)
                if splib._clen(text) < 200:
                    continue
                key = f"{author}/{f.parent.parent.name}"
                named.append((key, text))
                labels[key] = author
        self.assertGreater(len(named), 5)
        matrix = splib.build_metric_matrix(named)
        r = splib.permutation_test(named, labels, n_perm=500,
                                   seed=20260930, matrix=matrix)
        self.assertGreaterEqual(r["observed"], 0.8,
                                f"作者归因跌破 0.8：observed={r['observed']}")
        self.assertLessEqual(r["p"], 0.05,
                             f"作者归因不再显著高于置换零假设：p={r['p']}")
        for author in ("luxun", "zhuziqing"):
            pg = r["per_group"][author]
            rate = pg["correct"] / pg["judged"]
            self.assertGreaterEqual(rate, 0.8,
                                    f"{author} 侧归因跌破 0.8：{pg}")


if __name__ == "__main__":
    unittest.main()
