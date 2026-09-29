# -*- coding: utf-8 -*-
"""validate_pack：校验风格包的自包含性与结构完整性（可进 CI）。

用法：
    python scripts/validate_pack.py <风格包目录>

检查项：
  A. 必备文件齐全（pack.json / card.md / profile.md / fingerprint.json /
     exemplars.md / lexicon.md / limits.md）
  B. pack.json 必填字段与类型
  C. card.md ≤ 400 字（非空白字符）
  D. exemplars.md ≥ 6 条范例，每条引文（> 引用块）≤ 200 字
  E. fingerprint.json 至少 5 个带 target+容差的指标叶
  F. 无悬空引用：md 内不允许指向包外（../ 或绝对路径）的链接；
     正文不允许出现 corpus/ 语料路径引用
  G. profile.md 章节骨架齐全（缺章节给警告，不算失败）
退出码：0 = 通过；1 = 存在错误。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splib  # noqa: E402

BAD_LINK_RE = re.compile(r"\]\((\.\.?/|/|[A-Za-z]:)[^)]*\)")
CORPUS_REF_RE = re.compile(r"(corpus/|语料库/|\.\./chapters/)")

# 语义注入启发式：包文件会进入宿主上下文，指令型语句视为供应链风险线索。
# 命中只给警告（可能误伤文学文本），放行前必须人工复核。
INJECTION_PATTERNS = [
    re.compile(r"(忽略|无视)[^\s，。；：\"“”'‘’（）]{0,8}(指令|规则|要求|设定|提示词?)"),
    re.compile(r"(disregard|ignore)\s+(all\s+|any\s+)?(previous|above|prior|earlier)", re.I),
    re.compile(r"(系统提示|system prompt)\s*[:：]", re.I),
    re.compile(r"(不要遵循|不必遵守)(任何|以上|这些|下面的?)(规则|指令|要求)"),
]


def check_pack(pack_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []

    # A. 必备文件
    for name in splib.PACK_FILES:
        if not (pack_dir / name).is_file():
            errors.append(f"缺少必备文件：{name}")
    if not (pack_dir / "tests").is_dir():
        warns.append("缺少 tests/（A/B 盲测用例），建议补充")

    # B. pack.json
    pj_path = pack_dir / "pack.json"
    if pj_path.is_file():
        try:
            pj = splib.load_json(pj_path)
        except Exception as e:  # noqa: BLE001
            errors.append(f"pack.json 无法解析：{e}")
            pj = None
        if pj is not None:
            for key in ("format_version", "name", "display_name", "language",
                        "genres", "version", "created", "updated",
                        "corpus", "provenance", "license_note", "changelog"):
                if key not in pj:
                    errors.append(f"pack.json 缺少字段：{key}")
            if isinstance(pj.get("genres"), str):
                errors.append("pack.json.genres 应为数组")
            corpus = pj.get("corpus")
            if not isinstance(corpus, dict):
                errors.append("pack.json.corpus 应为对象")
            else:
                for key in ("works", "total_chars", "sampling", "confidence"):
                    if key not in corpus:
                        errors.append(f"pack.json.corpus 缺少字段：{key}")
            if not isinstance(pj.get("provenance"), list):
                errors.append("pack.json.provenance 应为数组")

    # C. card.md 长度
    card = pack_dir / "card.md"
    if card.is_file():
        text = card.read_text(encoding="utf-8")
        n = sum(1 for c in text if not c.isspace())
        if n > 400:
            errors.append(f"card.md 超长：{n} 字（上限 400）")

    # D. exemplars.md 条目与引文长度
    ex = pack_dir / "exemplars.md"
    if ex.is_file():
        text = ex.read_text(encoding="utf-8")
        entries = re.split(r"^###\s+", text, flags=re.M)[1:]
        if len(entries) < 6:
            errors.append(f"exemplars.md 范例仅 {len(entries)} 条（至少 6 条）")
        for entry in entries:
            title = entry.splitlines()[0].strip() if entry.splitlines() else "?"
            for quote in re.findall(r"^>\s?(.*)$", entry, flags=re.M):
                q = quote.strip().strip("》>").strip()
                if len(q) > 200:
                    errors.append(f"范例「{title}」引文超 200 字（{len(q)}），违反短引纪律")

    # E. fingerprint.json 指标叶
    fp = pack_dir / "fingerprint.json"
    if fp.is_file():
        try:
            fj = splib.load_json(fp)
        except Exception as e:  # noqa: BLE001
            errors.append(f"fingerprint.json 无法解析：{e}")
            fj = None
        if fj is not None:
            leaves = list(splib.iter_target_leaves(fj.get("metrics", {})))
            if len(leaves) < 5:
                errors.append(f"fingerprint.json 带容差的指标叶仅 {len(leaves)} 个（至少 5 个）")
            for path, leaf in leaves:
                if "tolerance_abs" not in leaf and "tolerance_rel" not in leaf:
                    errors.append(f"指标 {'.'.join(path)} 缺少 tolerance_abs/tolerance_rel")
            # v0.2.3 分层指纹：每层阈值树与顶层同等纪律
            for gname, layer in (fj.get("genres") or {}).items():
                gl = list(splib.iter_target_leaves(layer.get("metrics", {})))
                if len(gl) < 5:
                    errors.append(f"genres.{gname}.metrics 带容差的指标叶仅 {len(gl)} 个（至少 5 个）")
                for path, leaf in gl:
                    if "tolerance_abs" not in leaf and "tolerance_rel" not in leaf:
                        errors.append(f"genres.{gname} 指标 {'.'.join(path)} 缺少容差")
                if not layer.get("samples"):
                    errors.append(f"genres.{gname} 缺少 samples 列表")
            for gname, sc in (fj.get("self_check") or {}).items():
                if "n" not in sc or "delta_loo" not in sc:
                    errors.append(f"self_check.{gname} 缺少 n / delta_loo 字段")

    # F. 悬空引用
    for md in pack_dir.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for m in BAD_LINK_RE.finditer(text):
            errors.append(f"{md.name}：包外链接引用「{m.group(0)}」破坏自包含")
        if CORPUS_REF_RE.search(text):
            warns.append(f"{md.name}：出现语料路径引用，请确认不是运行时依赖")

    # F2. 语义注入启发式（命中 = 警告，人工复核后才可放行第三方包）
    for md in pack_dir.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for pat in INJECTION_PATTERNS:
            m = pat.search(text)
            if m:
                warns.append(
                    f"{md.name}：疑似指令注入语句「{m.group(0)[:40]}」——"
                    "第三方风格包按第三方代码对待，合并前必须人工复核语义")

    # G. profile.md 骨架
    profile = pack_dir / "profile.md"
    if profile.is_file():
        text = profile.read_text(encoding="utf-8")
        for section in splib.PROFILE_SECTIONS:
            if section not in text:
                warns.append(f"profile.md 缺少章节：「{section}」")

    return errors, warns


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="风格包自包含性校验")
    ap.add_argument("pack", help="风格包目录")
    args = ap.parse_args()

    pack_dir = Path(args.pack)
    if not pack_dir.is_dir():
        print(f"错误：目录不存在：{pack_dir}", file=sys.stderr)
        return 2

    errors, warns = check_pack(pack_dir)
    for w in warns:
        print(f"⚠️  {w}")
    for e in errors:
        print(f"❌ {e}")
    if not errors and not warns:
        print("✅ 校验通过，无警告")
    elif not errors:
        print(f"✅ 校验通过（{len(warns)} 条警告）")
    else:
        print(f"校验失败：{len(errors)} 个错误，{len(warns)} 条警告")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
