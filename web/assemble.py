# -*- coding: utf-8 -*-
"""assemble：装配预览——创作环的上下文组装与透明化（r4 §七 P2 吸收项）。

加载顺序照 style-apply 上下文加载协议（照搬不发明）：
  1 风格包档案（card/profile/thought/lexicon/limits/exemplars，整件装载不裁剪）
  3 bible 相关条目（按关键词命中；记忆注入最小版：命中优先、预算内装入）
  5 canon 层（canon/canon-terms.json 存在时：must/ban 术语表）
  4 章节锚定（上一章结尾 800 字）

纪律：
- 预览与生成走**同一个** assemble()——所见即所发；/generate 端点重跑组装并
  把装配快照写进 sessions/（可复判）。
- 每项带来源文件 + token 估算——红线 1（外发知情）的落地物。
- 预算裁剪只裁记忆与锚定，风格包档案不裁（盲测协议即整件装载）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import splib  # noqa: E402  (web/ 已把 scripts/ 加入 sys.path)

PACK_FILES = [("card.md", "包卡"), ("profile.md", "文风档案"),
              ("thought.md", "思想档案"), ("lexicon.md", "词汇表"),
              ("limits.md", "能力边界"), ("exemplars.md", "范例")]

TAIL_CHARS = 800
CHARS_PER_TOKEN = 0.75  # 中文粗估


def _est_tokens(text: str) -> int:
    return int(len(text) * CHARS_PER_TOKEN)


def _split_blocks(text: str) -> list[tuple[str, str]]:
    if "## " not in text:
        return [("", text.strip())]
    parts = text.split("\n## ")
    blocks: list[tuple[str, str]] = []
    head = parts[0].strip()
    if head:
        blocks.append((head.splitlines()[0].lstrip("# ").strip()[:30], head))
    for p in parts[1:]:
        title = p.splitlines()[0].lstrip("# ").strip()[:30]
        blocks.append((title, "## " + p.strip()))
    return blocks


def _matched_blocks(path: Path, keywords: list[str], kind: str) -> list[dict]:
    if not path.is_file():
        return []
    text = splib.read_text(path)[0]
    if not text.strip():
        return []
    blocks = _split_blocks(text)
    kw = [k for k in keywords if k]
    hits = [b for b in blocks if any(k in b[1] for k in kw)] if kw else []
    if not hits:
        hits = blocks[:2]  # 无命中只带头部，防整卷灌入
    return [{"kind": kind, "source": f"bible/{path.name}#{t}",
             "text": body} for t, body in hits]


def _chapter_num(stem: str) -> int | None:
    m = re.match(r"(\d+)", stem)
    return int(m.group(1)) if m else None


def assemble(project_dir: Path, pack_dir: Path, chapter_no: int,
             keywords: list[str] | None = None,
             budget_tokens: int = 24000) -> dict:
    keywords = keywords or []
    items: list[dict] = []  # 内部项：kind/source/text

    for fname, label in PACK_FILES:
        p = pack_dir / fname
        if p.is_file():
            text = splib.read_text(p)[0]
            src = (str(p.relative_to(project_dir))
                   if pack_dir.is_relative_to(project_dir)
                   else f"stylepacks/{'local/' if 'local' in pack_dir.parts else ''}{pack_dir.name}/{fname}")
            items.append({"kind": f"包·{label}", "source": src, "text": text,
                          "trimmable": False})

    for fname, kind in (("characters.md", "记忆·人物"), ("world.md", "记忆·设定"),
                        ("foreshadowing.md", "记忆·伏笔")):
        items += _matched_blocks(project_dir / "bible" / fname, keywords, kind)

    terms = project_dir / "canon" / "canon-terms.json"
    if terms.is_file():
        try:
            t = json.loads(terms.read_text(encoding="utf-8"))
            must = [x.get("term") for x in t.get("must", []) if isinstance(x, dict)]
            ban = [x.get("term") for x in t.get("ban", []) if isinstance(x, dict)]
            text = (f"must（按阈值落实）：{'、'.join(must) or '无'}\n"
                    f"ban（绝对不出现）：{'、'.join(ban) or '无'}")
            items.append({"kind": "canon·术语", "source": "canon/canon-terms.json",
                          "text": text, "trimmable": False})
        except (json.JSONDecodeError, OSError):
            pass

    ms = project_dir / "manuscript"
    if ms.is_dir():
        prev = [f for f in ms.glob("*.md")
                if (n := _chapter_num(f.stem)) and n < chapter_no]
        if prev:
            latest = max(prev, key=lambda f: _chapter_num(f.stem) or 0)
            text = splib.read_text(latest)[0][-TAIL_CHARS:]
            items.append({"kind": "章节锚定·上一章结尾",
                          "source": f"manuscript/{latest.name}", "text": text,
                          "trimmable": True})

    # 记忆·前情提要（v0.9.0）：MCP 同源 Store 的 recap——最近章摘要+未回收伏笔。
    # 无 db / 空库（新项目、未走记忆登记）静默跳过，装配行为不变。
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
        from store import Store  # noqa: E402 —— 延迟导入，无 server/ 时跳过
        store = Store(project_dir)
        try:
            recap = store.recap(3)
        finally:
            store.close()
        if recap.get("recent") or recap.get("open_foreshadow"):
            lines = [f"第{r['chapter']}章摘要：{r['digest']}"
                     for r in recap["recent"]]
            if recap["open_foreshadow"]:
                lines.append("未回收伏笔：" + "；".join(
                    f"{r['title']}（第{r['planted_chapter']}章埋）"
                    for r in recap["open_foreshadow"]))
            items.append({"kind": "记忆·前情提要",
                          "source": "style/memory.db（recap）",
                          "text": "\n".join(lines)[:1200], "trimmable": True})
    except Exception:  # noqa: BLE001 —— 记忆是增强，绝不阻断装配
        pass

    # 预算裁剪：只裁 trimmable，从后往前
    def tok(x: dict) -> int:
        return _est_tokens(x["text"])

    total = sum(tok(i) for i in items)
    for item in reversed([i for i in items if i.get("trimmable")]):
        if total <= budget_tokens:
            break
        total -= tok(item)
        item["dropped"] = True

    preview = []
    for i in items:
        preview.append({"kind": i["kind"], "source": i["source"],
                        "chars": len(i["text"]), "est_tokens": tok(i),
                        "dropped": bool(i.get("dropped")),
                        "excerpt": i["text"][:160] + ("…" if len(i["text"]) > 160 else "")})
    kept_texts = [f"【{i['kind']}｜{i['source']}】\n{i['text']}"
                  for i in items if not i.get("dropped")]
    return {"items": preview, "kept_texts": kept_texts,
            "total_chars": sum(len(i["text"]) for i in items),
            "total_est_tokens": sum(tok(i) for i in items if not i.get("dropped")),
            "budget_tokens": budget_tokens,
            "within_budget": total <= budget_tokens}
