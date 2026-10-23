# -*- coding: utf-8 -*-
"""routes_distill：蒸馏工作台 API（v0.7.1：阶段 A 入库/指纹/体检 + 阶段 B 采样精读）。

红线落实：
- 每个写操作响应带 cli 字段 = 等价 CLI 命令（插件属性：网页流程必有 CLI 等价）；
- 语料只允许 workspace downloads/corpus 之内（穿越防护）；
- status:"draft" 的包不进入任何消费枚举（创作/站点/项目包下拉），
  只能在本工作台与 /pack 预览，validate 通过并定稿后才对外可见；
- 成本纪律：精读前必走 plan_sampling 预告（N 篇/X 字/预计调用），
  >100k 字自动 map-reduce；账本入 <包>/cost.jsonl（gitignore）。
"""
from __future__ import annotations

import datetime
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel

import appstate
import creation
import distillation
import model_client
import routes_create as _rc
import splib  # noqa: E402  # server.py 已把 scripts/ 加入 sys.path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
STYLEPACKS = ROOT / "stylepacks"

router = APIRouter(prefix="/app/api/distill")


def _ws(cfg: dict) -> Path:
    return Path(cfg.get("workspace_root") or appstate.ROOT.parent)


def _corpus_root(cfg: dict) -> Path:
    return _ws(cfg) / "downloads" / "corpus"


def _safe_name(name: str, field: str = "名称") -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", (name or "").strip()).strip("-")
    if not s:
        raise HTTPException(400, f"{field}非法（仅限中英文/数字/连字符）")
    return s[:40]


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _corpus_dir(cfg: dict, rel: str) -> Path:
    root = _corpus_root(cfg)
    d = (root / rel).resolve()
    if not _under(d, root) or not d.is_dir():
        raise HTTPException(400, f"语料目录非法或不存在：{rel}")
    return d


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _pack_dir_checked(pack: str) -> Path:
    p = (pack or "").strip()
    if p.startswith("local/"):
        d = STYLEPACKS / "local" / _safe_name(p[len("local/"):], "包名")
    else:
        d = STYLEPACKS / _safe_name(p, "包名")
    if not (d / "pack.json").is_file():
        raise HTTPException(404, f"包不存在或无 pack.json：{pack}")
    return d


def _pack_rel(d: Path) -> str:
    return "stylepacks/" + d.resolve().relative_to(STYLEPACKS.resolve()).as_posix()


def _run_script(script: str, args: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          capture_output=True, encoding="utf-8", errors="replace",
                          timeout=timeout)


# ---- 语料浏览 ----

@router.get("/corpus")
def corpus_browse():
    """downloads/corpus 下的作者与作品（长篇 chapters/ 布局 + 短篇平铺布局）。"""
    cfg = appstate.load_config()
    root = _corpus_root(cfg)
    if not root.is_dir():
        return {"root": str(root), "authors": []}
    authors = []
    for ad in sorted(root.iterdir()):
        if not ad.is_dir() or ad.name.startswith("_") or ad.name == "legacy-root-corpus":
            continue
        works = []
        for w in sorted(ad.iterdir()):
            if w.is_dir() and (w / "chapters").is_dir():
                works.append({"name": w.name, "layout": "novel", "dir": _rel(w, root),
                              "samples": len(list((w / "chapters").glob("*.md"))),
                              "has_stats": (w / "stats.json").is_file()})
        flat = [f for f in ad.iterdir()
                if f.is_file() and f.suffix.lower() in (".txt", ".md")]
        if flat:
            works.append({"name": "（平铺语料）", "layout": "flat", "dir": _rel(ad, root),
                          "samples": len(flat), "has_stats": False})
        if works:
            authors.append({"name": ad.name, "works": works})
    return {"root": str(root), "authors": authors}


@router.get("/samples")
def samples(dir: str):
    """语料集逐样本指标 + 离群标记（z≥2）：有 stats.json 读缓存，否则现场计算。"""
    cfg = appstate.load_config()
    d = _corpus_dir(cfg, dir)
    rows = []
    stats_path = d / "stats.json"
    if stats_path.is_file():
        stats = splib.load_json(stats_path)
        for ch in stats.get("chapters", []):
            m = ch.get("metrics", {})
            rows.append({
                "file": ch.get("file") or ch.get("title"), "chars": ch.get("chars"),
                "sent_p50": (m.get("sentence_length") or {}).get("p50"),
                "dialogue": (m.get("paragraph") or {}).get("dialogue_para_ratio")})
    else:
        for f in splib.collect_text_files([str(d)]):
            text, _ = splib.read_text(f)
            m = splib.compute_metrics(text)
            rows.append({"file": f.name, "chars": m["chars_total"],
                         "sent_p50": m["sentence_length"]["p50"],
                         "dialogue": m["paragraph"]["dialogue_para_ratio"]})
    for key in ("sent_p50", "dialogue"):
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        if len(vals) >= 4:
            mean = sum(vals) / len(vals)
            std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
            if std > 0:
                for r in rows:
                    if isinstance(r.get(key), (int, float)):
                        r[f"{key}_z"] = round((r[key] - mean) / std, 2)
    for r in rows:
        r["outlier"] = any(abs(r.get(k, 0)) >= 2
                           for k in ("sent_p50_z", "dialogue_z"))
    return {"dir": dir, "rows": rows,
            "outliers": sum(1 for r in rows if r["outlier"])}


# ---- 入库（raw body 上传，零新依赖）----

@router.post("/ingest")
async def ingest(author: str = Query(...), work: str = Query(""),
                 source_url: str = Query(""), source_date: str = Query(""),
                 notes: str = Query(""), no_strip_ads: bool = Query(False),
                 unwrap: bool = Query(False),
                 filename: str = Query("upload.txt"),
                 body: bytes = Body(b"")):
    """单文件上传入库（前端多文件逐个调用）。body = 原始 txt 字节。"""
    if not body:
        raise HTTPException(400, "空的上传内容")
    if len(body) > 50 * 1024 * 1024:
        raise HTTPException(400, "单文件超 50MB——请拆分后入库")
    if not filename.lower().endswith((".txt", ".md")):
        raise HTTPException(400, "仅支持 .txt/.md")
    cfg = appstate.load_config()
    a = _safe_name(author, "作者名")
    adir = _corpus_root(cfg) / a
    w = _safe_name(work or Path(filename).stem, "作品名")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        inpath = Path(td) / "input.txt"
        inpath.write_bytes(body)
        cmd = [sys.executable, str(SCRIPTS / "ingest.py"), "--input", str(inpath),
               "--out", str(adir), "--work", w]
        if source_url:
            cmd += ["--source-url", source_url]
        if source_date:
            cmd += ["--source-date", source_date]
        if notes:
            cmd += ["--notes", notes]
        if no_strip_ads:
            cmd.append("--no-strip-ads")
        if unwrap:
            cmd.append("--unwrap")
        r = _run_script("ingest.py", cmd[2:], timeout=300)
        if r.returncode != 0:
            raise HTTPException(502, f"ingest 失败：{(r.stderr or r.stdout)[-400:]}")
    prov = splib.load_json(adir / w / "provenance.json")
    rel = _rel(adir / w, _corpus_root(cfg))
    cli = (f'python scripts/ingest.py --input <文件> --out downloads/corpus/{a} '
           f'--work {w}'
           + (f' --source-url {source_url}' if source_url else '')
           + (' --no-strip-ads' if no_strip_ads else '')
           + (' --unwrap' if unwrap else ''))
    return {"ok": True, "work": w, "dir": rel,
            "chapters": prov.get("chapter_count"), "chars": prov.get("total_chars"),
            "encoding": prov.get("original_encoding"),
            "ads_removed": prov.get("ads_removed_lines"), "cli": cli}


# ---- 草稿包 ----

@router.get("/packs")
def packs_list():
    """蒸馏台侧栏的包列表（含草稿——只有创作页/站点/装配枚举才过滤）。"""
    out = []
    if STYLEPACKS.is_dir():
        for d in sorted(STYLEPACKS.iterdir()):
            if d.is_dir() and (d / "pack.json").is_file() and d.name != "local":
                out.append(d.name)
        local = STYLEPACKS / "local"
        if local.is_dir():
            out += [f"local/{x.name}" for x in sorted(local.iterdir())
                    if x.is_dir() and (x / "pack.json").is_file()]
    return {"packs": out}

class PackIn(BaseModel):
    name: str
    display_name: str = ""
    corpus_dir: str = ""  # 语料集相对路径（记入 provenance）


@router.post("/pack")
def pack_create(body: PackIn):
    """创建草稿包（status: draft）——已存在草稿则复用；已存在正式包则 409。"""
    name = _safe_name(body.name, "包名")
    target = STYLEPACKS / name
    pj = target / "pack.json"
    if pj.is_file():
        meta = splib.load_json(pj)
        if meta.get("status") == "draft":
            return {"ok": True, "reused": True, "name": name}
        raise HTTPException(409, f"包 {name} 已存在且已定稿——请换名")
    target.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    scaffold = {
        "format_version": "0.2", "name": name,
        "display_name": body.display_name or name, "language": "zh",
        "genres": [], "registers": False, "version": "0.1.0",
        "created": today, "updated": today, "status": "draft",
        "corpus": {"works": [], "total_chars": 0,
                   "sampling": f"待定（蒸馏台草案，语料集：{body.corpus_dir or '未记录'}）",
                   "confidence": "未定稿（蒸馏台草稿）"},
        # provenance 须为数组、license_note/changelog 必备——validate 硬性字段
        "provenance": [], "license_note": "", "changelog": [],
    }
    pj.write_text(json.dumps(scaffold, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8", newline="\n")
    cli = "python scripts/validate_pack.py " + f"stylepacks/{name}"
    return {"ok": True, "reused": False, "name": name, "cli": cli}


@router.get("/pack")
def pack_preview(pack: str):
    d = _pack_dir_checked(pack)
    meta = splib.load_json(d / "pack.json")
    files = sorted(f.name for f in d.iterdir() if f.is_file())
    return {"name": d.name, "status": meta.get("status", "published"),
            "version": meta.get("version", ""), "files": files,
            "display_name": meta.get("display_name", ""),
            "corpus": meta.get("corpus", {}),
            "provenance": meta.get("provenance", {})}


class FingerprintIn(BaseModel):
    pack: str
    corpus_dir: str
    exclude: list[str] = []


@router.post("/fingerprint")
def fingerprint(body: FingerprintIn):
    """fp_extract（指标存档）+ build_delta --layered（写 fingerprint.json），
    支持 --exclude 离群剔除后重算。零模型调用。"""
    d = _pack_dir_checked(body.pack)
    cfg = appstate.load_config()
    cdir = _corpus_dir(cfg, body.corpus_dir)
    excl = [x for x in body.exclude if x.strip()]
    fp_json = d / "fp_extract.json"  # 工作数据（分析存档，非定稿物）
    r1 = _run_script("fp_extract.py", [str(cdir), "--json", str(fp_json), "--exclude", *excl])
    r2 = _run_script("build_delta.py", [str(cdir), "--pack", str(d), "--layered",
                                        "--exclude", *excl])
    if r2.returncode != 0:
        raise HTTPException(502, f"build_delta 失败：{(r2.stderr or r2.stdout)[-400:]}")
    fp = splib.load_json(d / "fingerprint.json")
    profile = fp.get("delta_profile") or {}
    layers = []
    for g, layer in sorted((fp.get("genres") or {}).items()):
        layers.append({"genre": g, "samples": layer.get("samples", []),
                       "n": len(layer.get("samples", []))})
    self_check = fp.get("self_check") or {}
    sc = [{"genre": g, "delta_max": v.get("delta_max"),
           "calibratable": v.get("delta_max") is not None}
          for g, v in sorted(self_check.items())]
    cli = (f'python scripts/fp_extract.py downloads/corpus/{body.corpus_dir} '
           f'--json stylepacks/{d.name}/fp_extract.json'
           + (" --exclude " + " ".join(excl) if excl else "")
           + f'\npython scripts/build_delta.py downloads/corpus/{body.corpus_dir} '
           + f'--pack stylepacks/{d.name} --layered'
           + (" --exclude " + " ".join(excl) if excl else ""))
    return {"ok": True, "n_samples": profile.get("n_samples", 0),
            "layers": layers, "self_check": sc,
            "excluded": excl, "fp_extract_report": (r1.stdout or "")[-1200:],
            "cli": cli}


class ValidateIn(BaseModel):
    pack: str


@router.post("/validate")
def validate_pack(body: ValidateIn):
    d = _pack_dir_checked(body.pack)
    r = _run_script("validate_pack.py", [str(d)], timeout=300)
    return {"exit_code": r.returncode, "report": (r.stdout or "") + (r.stderr or ""),
            "ok": r.returncode == 0,
            "cli": f"python scripts/validate_pack.py {_pack_rel(d)}"}


# ---- 阶段 B：采样精读（模型调用，D3=写作路由；纪律：先预告后烧）----

def _sample_rows(cfg: dict, rel: str, exclude: list[str] | None = None) -> list[dict]:
    d = _corpus_dir(cfg, rel)
    excl = set(exclude or [])
    rows = []
    stats_path = d / "stats.json"
    if stats_path.is_file():
        stats = splib.load_json(stats_path)
        for ch in stats.get("chapters", []):
            fname = ch.get("file") or ch.get("title")
            if fname in excl:
                continue
            m = ch.get("metrics", {})
            rows.append({"file": fname, "chars": ch.get("chars", 0),
                         "sent_p50": (m.get("sentence_length") or {}).get("p50"),
                         "dialogue": (m.get("paragraph") or {}).get("dialogue_para_ratio")})
    else:
        for f in splib.collect_text_files([str(d)]):
            if f.name in excl:
                continue
            text, _ = splib.read_text(f)
            m = splib.compute_metrics(text)
            rows.append({"file": f.name, "chars": m["chars_total"],
                         "sent_p50": m["sentence_length"]["p50"],
                         "dialogue": m["paragraph"]["dialogue_para_ratio"]})
    return rows


class SamplingIn(BaseModel):
    corpus_dir: str
    exclude: list[str] = []


@router.post("/plan_sampling")
def plan_sampling(body: SamplingIn):
    """自动选样（首/中/尾/对话密集/叙述密集，上限 8）+ 成本预告——
    烧模型前必走此步：N 篇/X 字/预计调用与 tokens（技能 2.1 纪律网页化）。"""
    cfg = appstate.load_config()
    rows = _sample_rows(cfg, body.corpus_dir, body.exclude)
    selection = distillation.plan_sampling(rows)
    total = sum(r["chars"] or 0 for r in selection)
    mode = "single" if total <= distillation.READ_SINGLE_MAX else "map"
    chunks = 1 if mode == "single" else max(
        1, -(-total // distillation.CHUNK_CHARS))
    est_tokens = int(total * 0.75) + distillation.READ_MAX_TOKENS * chunks
    return {"selection": selection, "total_chars": total, "mode": mode,
            "chunks": chunks, "est_calls": chunks, "est_tokens": est_tokens,
            "limits": {"single_max": distillation.READ_SINGLE_MAX,
                       "chunk_chars": distillation.CHUNK_CHARS}}


class ReadIn(BaseModel):
    pack: str
    corpus_dir: str
    files: list[str] = []


def _distill_call(cfg: dict, sid: str, prompt: str, max_tokens: int) -> dict:
    base, key, model = _rc._resolve_model(cfg, "write")  # D3：蒸馏用写作路由
    _rc._guard(cfg, sid, int(len(prompt) * 0.8) + max_tokens)
    try:
        result = model_client.chat(base, key, model,
                                   [{"role": "system",
                                     "content": distillation.SYSTEM_READ},
                                    {"role": "user", "content": prompt}],
                                   temperature=distillation.READ_TEMPERATURE,
                                   max_tokens=max_tokens)
    except ValueError as exc:
        raise HTTPException(502, str(exc))
    _rc._record_usage(sid, result)
    return result


def _pack_cost(pack_dir: Path, usage: dict, note: str) -> None:
    """蒸馏账本：stylepacks/<包>/cost.jsonl（gitignore，不进仓库）。"""
    entry = {"date": datetime.date.today().isoformat(), "skill": "web-distill",
             "model": usage.get("model", ""),
             "tokens": (usage.get("prompt_tokens", 0)
                        + usage.get("completion_tokens", 0)),
             "note": note}
    with (pack_dir / "cost.jsonl").open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


@router.post("/read")
def read_samples(body: ReadIn):
    """精读选样（≤100k 字单次；超出自动 map-reduce）→ analysis.json（工作数据，
    gitignore；不定稿入包）。提案是模型的，指纹/motif 数字仍是脚本的。"""
    if not body.files:
        raise HTTPException(400, "选样为空——先自动选样或勾选文件")
    cfg = appstate.load_config()
    cdir = _corpus_dir(cfg, body.corpus_dir)
    collected = {f.name: f for f in splib.collect_text_files([str(cdir)])}
    bad = [f for f in body.files if f not in collected]
    if bad:
        raise HTTPException(400, f"选样不在语料集内：{'、'.join(bad[:3])}")
    samples = [(name, splib.read_text(collected[name])[0]) for name in body.files]
    total = sum(len(t) for _, t in samples)
    pack_dir = _pack_dir_checked(body.pack)
    sid = f"distill-{uuid.uuid4().hex[:8]}"
    usage_total: dict = {}
    if total <= distillation.READ_SINGLE_MAX:
        result = _distill_call(cfg, sid, distillation.read_prompt(samples),
                               distillation.READ_MAX_TOKENS)
        analysis = creation.extract_json(result["text"])
        mode = "single"
        usage_total = result
    else:
        chunks = distillation.chunk_files(samples)
        obs = []
        for chunk in chunks:
            r = _distill_call(cfg, sid, distillation.chunk_prompt(chunk),
                              distillation.OBS_MAX_TOKENS)
            obs.append(creation.extract_json(r["text"]))
        result = _distill_call(cfg, sid, distillation.reduce_prompt(obs),
                               distillation.READ_MAX_TOKENS)
        analysis = creation.extract_json(result["text"])
        mode = "map"
        usage_total = result
    record = {"pack": pack_dir.name,
              "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
              "mode": mode, "files": body.files, "total_chars": total,
              "usage": {"prompt_tokens": usage_total.get("prompt_tokens", 0),
                        "completion_tokens": usage_total.get("completion_tokens", 0),
                        "model": usage_total.get("model", "")},
              "analysis": analysis}
    (pack_dir / "analysis.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    _pack_cost(pack_dir, record["usage"],
               f"精读 {len(body.files)} 篇 {total} 字（{mode}）")
    return {"ok": True, "mode": mode, "analysis": analysis,
            "usage": record["usage"], "files": body.files,
            "cli": "技能路径：style-analyze（分层采样精读，六问题+思想四问；"
                   "网页端以写作路由完成同一流程）"}


class AnalysisIn(BaseModel):
    pack: str
    analysis: dict


@router.get("/analysis")
def analysis_get(pack: str):
    d = _pack_dir_checked(pack)
    p = d / "analysis.json"
    if not p.is_file():
        raise HTTPException(404, "该包还没有精读记录（analysis.json）")
    return splib.load_json(p)


@router.post("/analysis")
def analysis_save(body: AnalysisIn):
    """人工校订后的分析存档（工作数据，可编辑重跑；不定稿入包）。"""
    d = _pack_dir_checked(body.pack)
    record = (splib.load_json(d / "analysis.json")
              if (d / "analysis.json").is_file() else {})
    record["analysis"] = body.analysis
    record["edited_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    (d / "analysis.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return {"ok": True}


# ---- 阶段 C：草案生成 + 逐节校订 + 定稿 ----

EDITABLE_FILES = {"card.md", "profile.md", "exemplars.md", "lexicon.md",
                  "limits.md", "thought.md"}


class PackOnly(BaseModel):
    pack: str


@router.post("/preview_draft")
def preview_draft(body: PackOnly):
    """草案生成成本预告：N 次调用（范例/九章/三件套/思想可选）+ tokens 估算。"""
    d = _pack_dir_checked(body.pack)
    rec = (splib.load_json(d / "analysis.json")
           if (d / "analysis.json").is_file() else None)
    if not rec:
        raise HTTPException(404, "先跑阶段 B 精读（analysis.json 不存在）")
    total = int(rec.get("total_chars") or 0)
    calls = 4  # 范例 / 九章 profile / 三件套 / card 内含
    est = int(total * 0.75) + distillation.EXEMPLARS_MAX_TOKENS \
        + distillation.PROFILE_MAX_TOKENS + distillation.TRIO_MAX_TOKENS
    return {"est_calls": calls, "est_tokens": est, "mode_hint": "逐文件低温生成",
            "note": "另可选生成 thought.md（+1 次调用）；motif 验证是脚本不计费"}


class GenDraftIn(BaseModel):
    pack: str
    corpus_dir: str
    include_thought: bool = True


@router.post("/gen_draft")
def gen_draft(body: GenDraftIn):
    """草案生成：范例（引文逐字校验，伪造整条剔除）→ 九章 profile（引用范例
    序号）→ card/lexicon/limits 三件套 → thought（可选）→ motif_count --write
    → pack.json 补全（诚实 corpus/provenance）。提案是模型的，校验是脚本的。"""
    d = _pack_dir_checked(body.pack)
    rec_path = d / "analysis.json"
    if not rec_path.is_file():
        raise HTTPException(404, "先跑阶段 B 精读（analysis.json 不存在）")
    rec = splib.load_json(rec_path)
    analysis = rec.get("analysis") or {}
    files = rec.get("files") or []
    cfg = appstate.load_config()
    cdir = _corpus_dir(cfg, body.corpus_dir)
    collected = {f.name: f for f in splib.collect_text_files([str(cdir)])}
    samples = [(n, splib.read_text(collected[n])[0]) for n in files if n in collected]
    if not samples:
        raise HTTPException(400, "精读记录的选样文件已不在语料集——请重跑阶段 B")
    corpus_text = "\n".join(t for _, t in samples)
    sid = f"distill-{uuid.uuid4().hex[:8]}"
    spend = {"prompt_tokens": 0, "completion_tokens": 0}
    report: list[dict] = []

    def call(name: str, prompt: str, max_tokens: int) -> str:
        r = _distill_call(cfg, sid, prompt, max_tokens)
        spend["prompt_tokens"] += r.get("prompt_tokens", 0)
        spend["completion_tokens"] += r.get("completion_tokens", 0)
        report.append({"file": name, "completion_tokens": r.get("completion_tokens", 0)})
        return r["text"]

    # 1) 范例（引文逐字校验）
    ex_md = call("exemplars.md",
                 distillation.exemplars_prompt(analysis, samples),
                 distillation.EXEMPLARS_MAX_TOKENS)
    ex_md, dropped, labels = distillation.verify_exemplar_quotes(ex_md, corpus_text)
    (d / "exemplars.md").write_text(ex_md, encoding="utf-8", newline="\n")

    # 2) 九章 profile（引用范例序号）
    fp = splib.load_json(d / "fingerprint.json") if (d / "fingerprint.json").is_file() else {}
    sl = ((fp.get("genres") or {}).get("narrative", {}).get("metrics")
          or {}).get("sentence_length", {})
    metrics_note = (f"句长 P50={sl.get('p50', {}).get('target', '实测值')}、"
                    f"P25={sl.get('p25', {}).get('target', '—')}、"
                    f"P75={sl.get('p75', {}).get('target', '—')}（build_delta 实测）")
    (d / "profile.md").write_text(
        call("profile.md",
             distillation.profile_prompt(analysis, ex_md, metrics_note),
             distillation.PROFILE_MAX_TOKENS),
        encoding="utf-8", newline="\n")

    # 3) card/lexicon/limits 三件套（JSON 包装）
    top_chars: list[str] = []
    fp_ext = d / "fp_extract.json"
    if fp_ext.is_file():
        tc = splib.load_json(fp_ext).get("top_chars") or []
        # fp_extract 的 top_chars 是 [{char, per_1k}...] 列表（真语料实测形态）
        top_chars = ([x.get("char", "") for x in tc if isinstance(x, dict)]
                     if isinstance(tc, list) else list(tc.keys()))
    trio = creation.extract_json(call(
        "card+lexicon+limits",
        distillation.trio_prompt(analysis, top_chars, ex_md),
        distillation.TRIO_MAX_TOKENS))
    for key, fname in (("card_md", "card.md"), ("lexicon_md", "lexicon.md"),
                       ("limits_md", "limits.md")):
        (d / fname).write_text(str(trio.get(key) or ""), encoding="utf-8",
                               newline="\n")

    # 4) thought（可选）+ motif 脚本验证
    motif_report = ""
    if body.include_thought:
        (d / "thought.md").write_text(
            call("thought.md", distillation.thought_prompt(analysis),
                 distillation.THOUGHT_MAX_TOKENS),
            encoding="utf-8", newline="\n")
        mc = _run_script("motif_count.py", [str(cdir), "--pack", str(d), "--write"],
                         timeout=300)
        motif_report = (mc.stdout or "") + (mc.stderr or "")
        if mc.returncode != 0:
            motif_report += "（motif 验证失败不阻塞草案——可修词表行后重跑）"

    # 5) pack.json 补全（诚实 corpus/provenance）
    meta = splib.load_json(d / "pack.json")
    works = []
    total_chars = 0
    for w in sorted(cdir.iterdir()):
        if w.is_dir() and (w / "provenance.json").is_file():
            prov = splib.load_json(w / "provenance.json")
            works.append(w.name)
            total_chars += int(prov.get("total_chars") or 0)
            meta.setdefault("provenance", []).append({
                "type": "ingest", "work": w.name,
                "url": prov.get("source_url", ""),
                "fetched_at": prov.get("fetched_at", ""),
                "notes": f"原编码 {prov.get('original_encoding', '?')}；"
                         f"去广告 {prov.get('ads_removed_lines', 0)} 行"})
    if not works:  # 平铺语料：作者目录即语料集
        works = [cdir.name]
        total_chars = sum(r["chars"] for r in
                          _sample_rows(cfg, body.corpus_dir))
        meta.setdefault("provenance", []).append({
            "type": "ingest", "work": cdir.name, "url": "", "fetched_at": "",
            "notes": "平铺语料（逐文件 provenance 见语料目录）"})
    meta["corpus"] = {"works": works, "total_chars": total_chars,
                      "sampling": f"分层采样精读 {len(files)} 篇（自动选样："
                                  f"首/中/尾/对话密集/叙述密集）",
                      "confidence": "低（新蒸馏草案，未盲测）"}
    meta["thought"] = bool(body.include_thought)
    splib.dump_json(meta, d / "pack.json")
    _pack_cost(d, spend, f"草案生成（thought={body.include_thought}）")
    return {"ok": True, "files": [r["file"] for r in report], "report": report,
            "quotes_dropped": dropped, "quotes_dropped_labels": labels,
            "motif_report": motif_report[-800:], "usage": spend,
            "cli": "技能路径：style-analyze 步 3（九章草案 → motif_count --write）"}


@router.get("/file")
def file_get(pack: str, name: str):
    if name not in EDITABLE_FILES:
        raise HTTPException(400, f"该文件不在可编辑清单：{name}")
    d = _pack_dir_checked(pack)
    p = d / name
    if not p.is_file():
        raise HTTPException(404, f"{name} 不存在（先草案生成）")
    return {"name": name, "content": p.read_text(encoding="utf-8")}


class FileIn(BaseModel):
    pack: str
    name: str
    content: str


@router.post("/file")
def file_save(body: FileIn):
    """逐节校订：人工编辑档案文件（白名单内；thought 需草案期勾选生成）。"""
    if body.name not in EDITABLE_FILES:
        raise HTTPException(400, f"该文件不在可编辑清单：{body.name}")
    d = _pack_dir_checked(body.pack)
    (d / body.name).write_text(body.content, encoding="utf-8", newline="\n")
    return {"ok": True}


class PublishIn(BaseModel):
    pack: str
    tier: str = "public"  # public | local
    license_note: str = ""
    confidence: str = "低（新蒸馏，未盲测）"


@router.post("/publish")
def publish(body: PublishIn):
    """定稿：validate 必须通过；按层落位（公版顶层 / 本地 local 层）并置
    status: published——此后创作页/站点/装配可见。"""
    d = _pack_dir_checked(body.pack)
    v = _run_script("validate_pack.py", [str(d)], timeout=300)
    if v.returncode != 0:
        raise HTTPException(400, "validate 未通过，定稿被拒绝：\n"
                                 + ((v.stdout or "") + (v.stderr or ""))[-900:])
    meta = splib.load_json(d / "pack.json")
    meta.pop("status", None)
    meta["corpus"]["confidence"] = body.confidence or "低（新蒸馏，未盲测）"
    if body.tier == "local":
        meta["license_note"] = (body.license_note
                                or "本地层：含受版权语料的分析，不得公开再分发")
    today = datetime.date.today().isoformat()
    meta.setdefault("changelog", []).append(
        {"version": meta.get("version", "0.1.0"), "date": today,
         "changes": "蒸馏台定稿（阶段 C）"})
    splib.dump_json(meta, d / "pack.json")
    if body.tier == "local":
        local = STYLEPACKS / "local"
        local.mkdir(exist_ok=True)
        target = local / d.name
        if target.exists():
            raise HTTPException(409, f"local 层已有同名包：{d.name}")
        d = d.rename(target)
    return {"ok": True, "path": _pack_rel(d),
            "visible": "创作页包下拉 / 包浏览站点 / 装配（钉扎即用）",
            "cli": f"python scripts/validate_pack.py {_pack_rel(d)}；"
                   f"手动定稿 = 编辑 pack.json 去 status 字段（local 层再移动目录）"}
