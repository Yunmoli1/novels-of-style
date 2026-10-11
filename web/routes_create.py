# -*- coding: utf-8 -*-
"""routes_create：创作环与配置的 API（v0.6.0）。

红线落实：
- GET /app/api/config 永不返回 api_key（sanitize）；
- 装配预览与生成共用 assemble()（所见即所发）；
- fp_check/borrow_check 为 advisory 报告，UI 不得渲染成通过/失败门，
  交付动作必须显式点"确认交付"（阶段门的显式覆盖出口）；
- 每次模型调用前检查会话 token 护栏，调用后记账 cost.jsonl。
"""
from __future__ import annotations

import datetime
import json
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import appstate
import assemble as assemble_mod
import creation
import model_client
import splib  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
STYLEPACKS = ROOT / "stylepacks"

router = APIRouter(prefix="/app/api")

# 会话 token 护栏的内存账（本地单用户，进程内存即可）
_sessions: dict[str, dict] = {}


def _ws_root(cfg: dict) -> Path:
    return Path(cfg.get("workspace_root") or appstate.ROOT.parent)


def _project_dir(cfg: dict, name: str) -> Path:
    d = (_ws_root(cfg) / name).resolve()
    root = _ws_root(cfg).resolve()
    if root not in d.parents and d != root:
        raise HTTPException(400, "项目名非法")
    if not d.is_dir():
        raise HTTPException(404, f"项目不存在：{name}")
    return d


def _pack_dir(pack: str) -> Path:
    d = (STYLEPACKS / pack).resolve()
    if not (d / "pack.json").is_file():
        raise HTTPException(404, f"风格包不存在或无 pack.json：{pack}")
    return d


def _resolve_model(cfg: dict, route: str) -> tuple[str, str, str]:
    prov, model = appstate.resolve_route(cfg, route)
    if not prov or not model:
        raise HTTPException(400, f"未配置 {route} 模型路由——请先到「模型配置」页设置")
    return prov["base_url"], prov.get("api_key"), model


def _guard(cfg: dict, session_id: str, est_tokens: int) -> None:
    limit = cfg.get("session_max_tokens")
    if not limit:
        return
    used = _sessions.get(session_id, {}).get("tokens", 0)
    if used + est_tokens > int(limit):
        raise HTTPException(429, f"会话 token 护栏：已用 {used} + 本次 {est_tokens} "
                                 f"> 上限 {limit}（可在模型配置页调整）")


def _record_usage(session_id: str, usage: dict) -> None:
    s = _sessions.setdefault(session_id, {"tokens": 0, "calls": 0})
    s["tokens"] += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    s["calls"] += 1


def _run_gate(script: str, args: list[str]) -> dict:
    """advisory 门禁：跑 CLI 脚本，返回报告（不作为通过/失败判定）。"""
    try:
        r = subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                           capture_output=True, encoding="utf-8", errors="replace",
                           timeout=120)
        return {"script": script, "exit_code": r.returncode,
                "report": (r.stdout or "") + (r.stderr or "")}
    except subprocess.TimeoutExpired:
        return {"script": script, "exit_code": -1, "report": "超时"}


# ---- 配置 ----

class ConfigIn(BaseModel):
    providers: list[dict] = []
    routing: dict = {}
    workspace_root: str | None = None
    context_budget_tokens: int = 24000
    session_max_tokens: int | None = 200000
    prose_max_tokens: int = 3500
    temperature: float = 0.8


@router.get("/config")
def get_config():
    cfg = appstate.load_config()
    view = appstate.sanitize_config(cfg)
    view["workspace_projects"] = appstate.discover_projects(_ws_root(cfg))
    return view


@router.post("/config")
def set_config(body: ConfigIn):
    cfg = appstate.load_config()
    cfg["providers"] = [p for p in body.providers if p.get("name") and p.get("base_url")]
    for p in cfg["providers"]:
        if not isinstance(p.get("models"), list):
            p["models"] = []
    cfg["routing"] = body.routing or {}
    if body.workspace_root:
        cfg["workspace_root"] = body.workspace_root
    cfg["context_budget_tokens"] = body.context_budget_tokens
    cfg["session_max_tokens"] = body.session_max_tokens
    cfg["prose_max_tokens"] = body.prose_max_tokens
    cfg["temperature"] = body.temperature
    appstate.save_config(cfg)
    return {"ok": True, "config": appstate.sanitize_config(appstate.load_config())}


class TestIn(BaseModel):
    name: str


@router.post("/config/test")
def test_connection(body: TestIn):
    cfg = appstate.load_config()
    for prov in cfg.get("providers", []):
        if prov.get("name") == body.name:
            try:
                ids = model_client.list_models(prov["base_url"], prov.get("api_key"))
                return {"ok": True, "models": ids}
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}
    raise HTTPException(404, f"未找到 provider：{body.name}")


# ---- 项目/包 ----

@router.get("/projects")
def projects():
    cfg = appstate.load_config()
    return {"workspace_root": str(_ws_root(cfg)),
            "projects": appstate.discover_projects(_ws_root(cfg)),
            "packs": [{"name": d.name} for d in sorted(STYLEPACKS.iterdir())
                      if d.is_dir() and (d / "pack.json").is_file()
                      and d.name != "local"]
            + ([{"name": f"local/{d.name}"}
                for d in sorted(local_dir.iterdir())
                if d.is_dir() and (d / "pack.json").is_file()]
               if (local_dir := STYLEPACKS / "local").is_dir() else [])}


class AssembleIn(BaseModel):
    project: str
    pack: str
    chapter_no: int
    keywords: list[str] = []


@router.post("/assemble")
def do_assemble(body: AssembleIn):
    cfg = appstate.load_config()
    result = assemble_mod.assemble(
        _project_dir(cfg, body.project), _pack_dir(body.pack),
        body.chapter_no, body.keywords, cfg.get("context_budget_tokens", 24000))
    result.pop("kept_texts", None)  # 预览不外带全文
    return result


# ---- 共创与生成 ----

class OutlineIn(BaseModel):
    project: str
    pack: str
    chapter_no: int
    title: str
    keywords: list[str] = []
    user_notes: str = ""
    session_id: str | None = None


def _session_id(body) -> str:
    return body.session_id or uuid.uuid4().hex[:12]


def _do_model(cfg: dict, route: str, session_id: str, prompt: str,
              max_tokens: int, json_mode: bool):
    base, key, model = _resolve_model(cfg, route)
    _guard(cfg, session_id, int(max_tokens * 1.5))
    result = model_client.chat(base, key, model,
                               [{"role": "system", "content": creation.SYSTEM},
                                {"role": "user", "content": prompt}],
                               temperature=cfg.get("temperature", 0.8),
                               max_tokens=max_tokens)
    _record_usage(session_id, result)
    if json_mode:
        try:
            result["json"] = creation.extract_json(result["text"])
        except (ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(502, f"模型未返回可解析 JSON：{exc}｜原文头 300 字："
                                     f"{result['text'][:300]}")
    return result


@router.post("/outline")
def do_outline(body: OutlineIn):
    cfg = appstate.load_config()
    sid = _session_id(body)
    assembly = assemble_mod.assemble(
        _project_dir(cfg, body.project), _pack_dir(body.pack),
        body.chapter_no, body.keywords, cfg.get("context_budget_tokens", 24000))
    prompt = creation.outline_prompt(body.chapter_no, body.title, body.keywords,
                                     assembly["kept_texts"], body.user_notes)
    result = _do_model(cfg, "write", sid, prompt, 1200, True)
    return {"session_id": sid, "options": result["json"].get("options", []),
            "recommended": result["json"].get("recommended", 0),
            "usage": result, "assembly": {k: v for k, v in assembly.items()
                                          if k != "kept_texts"}}


class BeatsIn(OutlineIn):
    chosen: dict = {}


@router.post("/beats")
def do_beats(body: BeatsIn):
    cfg = appstate.load_config()
    sid = _session_id(body)
    assembly = assemble_mod.assemble(
        _project_dir(cfg, body.project), _pack_dir(body.pack),
        body.chapter_no, body.keywords, cfg.get("context_budget_tokens", 24000))
    canon_note = ("二创项目：原作锚点必须落到 canon-terms.json 的 must 术语与人物"
                  if (_project_dir(cfg, body.project) / "canon" / "canon-terms.json").is_file()
                  else "")
    prompt = creation.beats_prompt(body.chapter_no, body.title, body.chosen,
                                   assembly["kept_texts"], canon_note)
    result = _do_model(cfg, "write", sid, prompt, 1500, True)
    return {"session_id": sid, **result["json"], "usage": result}


class RerollIn(BeatsIn):
    beats: list[dict] = []
    index: int = 1


@router.post("/reroll_beat")
def do_reroll(body: RerollIn):
    cfg = appstate.load_config()
    sid = _session_id(body)
    assembly = assemble_mod.assemble(
        _project_dir(cfg, body.project), _pack_dir(body.pack),
        body.chapter_no, body.keywords, cfg.get("context_budget_tokens", 24000))
    prompt = creation.reroll_beat_prompt(body.chapter_no, body.title, body.chosen,
                                         body.beats, body.index,
                                         assembly["kept_texts"])
    result = _do_model(cfg, "write", sid, prompt, 400, True)
    return {"session_id": sid, "beat": result["json"], "usage": result}


class GenerateIn(BeatsIn):
    beats: list[dict] = []
    tone_note: str = "不指定"
    canon_anchor: str = "无"
    n_drafts: int = 1
    session_id: str = ""


@router.post("/generate")
def do_generate(body: GenerateIn):
    cfg = appstate.load_config()
    sid = _session_id(body)
    project_dir = _project_dir(cfg, body.project)
    pack_dir = _pack_dir(body.pack)
    assembly = assemble_mod.assemble(
        project_dir, pack_dir, body.chapter_no, body.keywords,
        cfg.get("context_budget_tokens", 24000))
    prompt = creation.prose_prompt(body.chapter_no, body.title, body.chosen,
                                   body.beats, body.tone_note, body.canon_anchor,
                                   assembly["kept_texts"],
                                   cfg.get("prose_max_tokens", 3500) * 2 // 3)
    drafts = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(max(1, min(3, body.n_drafts))):
            result = _do_model(cfg, "write", sid, prompt,
                               cfg.get("prose_max_tokens", 3500), False)
            draft_path = Path(td) / f"d{i}.txt"
            draft_path.write_text(result["text"], encoding="utf-8", newline="\n")
            fp = _run_gate("fp_check.py", [str(pack_dir), str(draft_path)])
            borrow = _run_gate("borrow_check.py", [str(draft_path),
                                                   "--pack", str(pack_dir)])
            drafts.append({"text": result["text"], "usage": result,
                           "fp_check": fp, "borrow_check": borrow})
    return {"session_id": sid, "drafts": drafts,
            "assembly_preview": assembly["items"],
            "assembly_tokens": assembly["total_est_tokens"]}


class EndingIn(BaseModel):
    project: str
    title: str
    text: str
    session_id: str = ""


@router.post("/ending_check")
def do_ending(body: EndingIn):
    cfg = appstate.load_config()
    sid = _session_id(body)
    tail = body.text[-800:]
    prompt = creation.ending_check_prompt(body.title, tail)
    result = _do_model(cfg, "judge", sid, prompt, 300, True)
    return {"session_id": sid, "ending_check": result["json"], "usage": result}


class SaveIn(BaseModel):
    project: str
    pack: str
    chapter_no: int
    title: str
    text: str
    chosen: dict = {}
    beats: list[dict] = []
    tone_note: str = "不指定"
    canon_anchor: str = "无"
    checks: dict = {}
    usage: dict = {}
    session_id: str = ""
    assembly_preview: list[dict] = []


@router.post("/save")
def do_save(body: SaveIn):
    cfg = appstate.load_config()
    project_dir = _project_dir(cfg, body.project)
    ms = project_dir / "manuscript"
    ms.mkdir(parents=True, exist_ok=True)
    target = ms / f"{body.chapter_no:03d}-{body.title}.md"
    if target.exists():
        stamp = time.strftime("%H%M%S")
        target = ms / f"{body.chapter_no:03d}-{body.title}-{stamp}.md"
    target.write_text(body.text, encoding="utf-8", newline="\n")

    sessions = project_dir / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    gitignore = sessions / ".gitignore"
    if not gitignore.is_file():  # 会话记录含创作内容，防误提交
        gitignore.write_text("*\n!.gitignore\n", encoding="utf-8", newline="\n")
    record = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "tool": "web-create v0.6.0", "session_id": body.session_id,
        "project": body.project, "pack": body.pack,
        "chapter_no": body.chapter_no, "title": body.title,
        "chosen": body.chosen, "beats": body.beats,
        "tone_note": body.tone_note, "canon_anchor": body.canon_anchor,
        "checks": body.checks, "usage": body.usage,
        "assembly": body.assembly_preview,
        "output_file": target.name, "text": body.text,
    }
    (sessions / f"{time.strftime('%Y%m%d-%H%M%S')}-{body.chapter_no:03d}.json"
     ).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8", newline="\n")
    appstate.append_cost(project_dir, "web-create",
                         chars=len(body.text), model=str(body.usage.get("model", "")),
                         tokens=(body.usage.get("prompt_tokens", 0)
                                 + body.usage.get("completion_tokens", 0)),
                         note=f"第{body.chapter_no}章《{body.title}》")
    return {"ok": True, "manuscript": str(target), "sessions_dir": str(sessions)}
