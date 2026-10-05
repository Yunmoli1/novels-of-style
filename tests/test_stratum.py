# -*- coding: utf-8 -*-
"""R1 归因/置换机器与 dry-run 的仪器测试（Case J 的机器守卫）。

阳性对照：构造字频 + 句长双维可分的两组语料，归因必须显著；
阴性对照：随机标签必须测不出显著——防止机器把噪声当信号。
"""
from __future__ import annotations

import contextlib
import io
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import registers_dryrun  # noqa: E402
import splib  # noqa: E402

LUXUN = ROOT / "stylepacks" / "luxun"

# 两个分布不同的合成"层"：甲层长句 + 山/天字域，乙层短句 + 海/船字域
_A_POOL = ["山在天边，天也在远山之外。", "他望着山，一天又一天地望着。",
           "山外的天低低地压着山。", "望山的人不走。"]
_B_POOL = ["海上有船。", "船在海中。", "她数着船。", "一夜又一夜。",
           "海中无路。", "看船的人不说话。"]


def _mini_texts(seed: int = 42) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    named = []
    for i in range(4):
        a = "".join(rng.choices(_A_POOL, k=8))
        b = "".join(rng.choices(_B_POOL, k=12))
        named.append((f"集一-甲{i}", a))
        named.append((f"集二-乙{i}", b))
    return named


def _mini_labels(named: list[tuple[str, str]]) -> dict[str, str]:
    return {n: ("甲层" if "甲" in n else "乙层") for n, _ in named}


class TestAttributionMachinery(unittest.TestCase):
    def test_positive_control_both_spaces(self):
        """真实可分的两层在字频与度量两个空间都必须显著（阳性对照）。"""
        named = _mini_texts()
        labels = _mini_labels(named)
        for matrix in (splib._build_rate_matrix(named, 150),
                       splib.build_metric_matrix(named)):
            r = splib.permutation_test(named, labels, n_perm=150,
                                       seed=20260930, matrix=matrix)
            self.assertGreater(r["observed"], 0.75, r)
            self.assertLessEqual(r["p"], 0.05, r)

    def test_negative_control_random_labels(self):
        """随机标签必须测不出显著（阴性对照）。"""
        named = _mini_texts()
        rng = random.Random(11)
        labels = {n: rng.choice(["甲层", "乙层"]) for n, _ in named}
        if len(set(labels.values())) < 2:  # 极小概率全同
            first = named[0][0]
            labels[first] = "乙层" if labels[first] == "甲层" else "甲层"
        m = splib.build_metric_matrix(named)
        r = splib.permutation_test(named, labels, n_perm=150, seed=20260930, matrix=m)
        self.assertGreater(r["p"], 0.05, r)

    def test_attribution_deterministic(self):
        named = _mini_texts()
        labels = _mini_labels(named)
        m = splib.build_metric_matrix(named)
        r1 = splib.permutation_test(named, labels, n_perm=50, seed=99, matrix=m)
        r2 = splib.permutation_test(named, labels, n_perm=50, seed=99, matrix=m)
        self.assertEqual(r1, r2)  # 固定种子 → 换机重跑可复现


class TestParseRegistersCalibration(unittest.TestCase):
    def test_calibration_lines(self):
        text = (
            "## 分区定义\n\n### 情感轴（散文）\n\n#### 沉郁哲思\n定义一。\n"
            "标定：仅路由（p=0.336）\n\n#### 冷峻讽刺\n定义二。\n"
            "标定：已标定（p=0.01）\n"
        )
        parsed = splib.parse_registers_md(text)
        self.assertEqual(parsed["calibration"],
                         {"沉郁哲思": "仅路由", "冷峻讽刺": "已标定"})
        self.assertEqual(parsed["axes"], {"沉郁哲思": "情感轴", "冷峻讽刺": "情感轴"})

    def test_luxun_registers_all_route_only(self):
        parsed = splib.parse_registers_md(
            (LUXUN / "registers.md").read_text(encoding="utf-8"))
        self.assertEqual(len(parsed["labels"]), 61)
        self.assertEqual(set(parsed["calibration"].values()), {"仅路由"})
        self.assertEqual(len(parsed["calibration"]), 6)


class TestDryrunCLI(unittest.TestCase):
    def test_dryrun_smoke(self):
        """合成小语料 + mini registers.md 走一遍 CLI（CI 无 downloads/ 语料）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            corpus = root / "corpus"
            corpus.mkdir()
            for i, (name, text) in enumerate(_mini_texts()):
                prefix = "jia" if "甲" in name else "yi"
                (corpus / f"{prefix}-{name.split('-')[1]}.txt").write_text(
                    text, encoding="utf-8")
            pack = root / "pack"
            pack.mkdir()
            (pack / "registers.md").write_text(
                "# 调子分区\n\n## 分区定义\n\n### 节奏轴（叙事）\n\n#### 甲层\n"
                "定义甲。\n标定：仅路由\n\n#### 乙层\n定义乙。\n标定：仅路由\n\n"
                "## 篇目总表\n\n| 篇名 | 主分区 | 次分区 | 依据 |\n|---|---|---|---|\n"
                + "".join(f"| 甲{i} | 甲层 | — | 测试 |\n" for i in range(3))
                + "".join(f"| 乙{i} | 乙层 | — | 测试 |\n" for i in range(3)),
                encoding="utf-8")
            out = io.StringIO()
            with mock.patch.object(sys, "argv", [
                    "registers_dryrun.py", str(corpus), "--pack", str(pack),
                    "--n-perm", "50"]), \
                    contextlib.redirect_stdout(out):
                rc = registers_dryrun.main()
            self.assertEqual(rc, 0)
            text = out.getvalue()
            self.assertIn("甲层", text)
            self.assertIn("p（单侧）", text)


if __name__ == "__main__":
    unittest.main()
