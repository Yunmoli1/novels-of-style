# -*- coding: utf-8 -*-
"""routes_history：历史章节与成本浏览（v0.9.5）。

sessions/ 是每章交付的完整可复判快照——此前只能翻 JSON 文件；
本模块把它变成网页：章节列表（门禁/成本概览）+ 详情（立意/拍子/报告）
+ cost.jsonl 的每章消耗条形图。纯读端点，CLI 等价 = 直接读文件。
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

import appstate
import routes_create as _rc

router = APIRouter(prefix="/app/api/history")


def _project(cfg: dict, name: str) -> Path:
    return _rc._project_dir(cfg, name)


@router.get("/sessions")
def sessions_list(project: str):
    cfg = appstate.load_config()
    sd = _project(cfg, project) / "sessions"
    out = []
    if sd.is_dir():
        for f in sorted(sd.glob("*.json"), reverse=True):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            checks = d.get("checks", {})
            fp_ok = (checks.get("fp_check") or {}).get("exit_code") == 0
            aic = checks.get("ai_cliche") or {}
            aic_ok = (aic.get("exit_code") == 0) if aic else None
            ending = checks.get("ending") or {}
            totals = d.get("session_totals") or {}
            out.append({
                "file": f.name, "ts": d.get("ts", ""),
                "chapter_no": d.get("chapter_no"), "title": d.get("title", ""),
                "chars": len(d.get("text", "")),
                "model": (d.get("usage") or {}).get("model", ""),
                "session_tokens": totals.get("tokens"),
                "session_calls": totals.get("calls"),
                "fp_ok": fp_ok, "aic_ok": aic_ok,
                "ending": (ending or {}).get("violation"),
                "pack": d.get("pack", "")})
    return {"sessions": out}


@router.get("/session_detail")
def session_detail(project: str, file: str):
    cfg = appstate.load_config()
    sd = _project(cfg, project) / "sessions"
    p = (sd / file).resolve()
    if not p.is_file() or p.parent != sd.resolve():
        raise HTTPException(404, "会话文件不存在")
    d = json.loads(p.read_text(encoding="utf-8"))
    text = d.get("text", "")
    d["text_preview"] = text[:1200] + ("…" if len(text) > 1200 else "")
    d.pop("text", None)  # 全文不搬（预览够判读；全文看 manuscript）
    d.pop("assembly", None)
    return d


@router.get("/costs")
def costs(project: str):
    """cost.jsonl 全量（date/skill/tokens/session_tokens/chars/note）——
    图表与累计口径的数据源。"""
    cfg = appstate.load_config()
    c = _project(cfg, project) / "style" / "cost.jsonl"
    rows = []
    if c.is_file():
        for line in c.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return {"rows": rows,
            "total_tokens": sum(int(r.get("session_tokens")
                                     or r.get("tokens") or 0) for r in rows)}
