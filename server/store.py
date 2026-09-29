# -*- coding: utf-8 -*-
"""store：StylePack v0.2 记忆层 —— SQLite 故事状态机 + 全文检索。

设计铁律（见 v0.2-计划书）：
- 文件是权威源：bible/*.md、names.json、timeline.json 由 sync() 单向导入，
  SQLite 只是索引与提取服务，删掉 memory.db 随时可重建
- 状态更新走 delta：写作流程 propose（入隔离区）→ merge（分级合并），
  绝不从全文提取状态
- 极简返回：所有查询结果经 fit() 裁剪，单次 ≤ 2KB
- 双暴露：本模块被 server/mcp_server.py 与 scripts/story.py 共用

零第三方依赖。FTS5 缺席时自动回退 LIKE 检索（章节数千级性能可接受）。
"""
from __future__ import annotations

import datetime
import json
import re
import sqlite3
from pathlib import Path

import splib

RETURN_LIMIT = 2000  # 单次返回字节上限（极简返回纪律）
PENDING_AGING_CHAPTERS = 5  # pending 滞留告警阈值

SCHEMA = """
CREATE TABLE IF NOT EXISTS entities(
  name TEXT PRIMARY KEY, kind TEXT NOT NULL, tier TEXT,
  aliases TEXT, summary TEXT);
CREATE TABLE IF NOT EXISTS entity_state(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity TEXT NOT NULL, chapter TEXT, field TEXT NOT NULL,
  value TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS pending_deltas(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chapter TEXT, entity TEXT, field TEXT, value TEXT,
  risk TEXT DEFAULT 'medium', note TEXT, ts TEXT,
  status TEXT DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS chapter_digests(
  chapter TEXT PRIMARY KEY, digest TEXT, source TEXT, chars INTEGER, ts TEXT);
CREATE TABLE IF NOT EXISTS foreshadowing(
  id TEXT PRIMARY KEY, title TEXT, planted_chapter TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS events(
  id TEXT PRIMARY KEY, ord INTEGER, date TEXT, description TEXT, chapters TEXT);
CREATE TABLE IF NOT EXISTS chapters_meta(
  path TEXT PRIMARY KEY, title TEXT, chars INTEGER, ord INTEGER);
"""

_HEAD_RE = re.compile(r"^##\s+(.+?)\s*$")
Bullet_RE = re.compile(r"^\s*[-*]\s+(.+)$")
NUM_RE = re.compile(r"(\d{3}|\d+)")


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def fit(obj, limit: int = RETURN_LIMIT):
    """极简返回纪律：序列化结果超限时逐步裁剪列表与片段，直到 ≤ limit 字节。"""
    s = json.dumps(obj, ensure_ascii=False)
    if len(s.encode("utf-8")) <= limit:
        return obj
    if isinstance(obj, dict):
        for key in ("results", "rows", "items", "digests", "states", "foreshadow"):
            v = obj.get(key)
            if isinstance(v, list) and len(v) > 1:
                obj = {**obj, key: v[: len(v) // 2]}
                return fit(obj, limit)
        if "snippet" in obj:
            return fit({**obj, "snippet": str(obj["snippet"])[:80] + "…"}, limit)
        if "text" in obj:
            return fit({**obj, "text": str(obj["text"])[: limit // 3] + "…"}, limit)
    if isinstance(obj, list) and obj:
        return fit(obj[: len(obj) // 2], limit)
    return {"truncated": True, "hint": "结果过大，请缩小查询范围"}


class Store:
    def __init__(self, project: Path):
        self.project = Path(project)
        self.db_path = self.project / "style" / "memory.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self.fts = True

    # ---- 基础
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            c = sqlite3.connect(self.db_path)
            c.row_factory = sqlite3.Row
            c.executescript(SCHEMA)
            # 轻量迁移：db 只是可重建的缓存（文件才是权威源），schema 不合即删表，
            # 下次 sync 重建——v0.2.4 给 chapters_meta 补 ord 列（数字前缀排序）
            cols = {r[1] for r in c.execute("PRAGMA table_info(chapters_meta)")}
            if "ord" not in cols:
                c.execute("DROP TABLE chapters_meta")
                c.executescript(SCHEMA)
            try:
                c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_chapters "
                          "USING fts5(path UNINDEXED, title UNINDEXED, body)")
            except sqlite3.OperationalError:
                self.fts = False
            self._conn = c
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ---- sync：文件（权威源）→ DB
    def sync(self) -> dict:
        c = self.conn()
        for table in ("entities", "events", "foreshadowing", "chapters_meta"):
            c.execute(f"DELETE FROM {table}")
        c.execute("DELETE FROM fts_chapters") if self.fts else None

        stats = {"characters": 0, "settings": 0, "foreshadow": 0, "events": 0, "chapters": 0}

        # names.json：tier 与别名
        names = {}
        nj = self.project / "bible" / "names.json"
        if nj.is_file():
            for p in json.loads(nj.read_text(encoding="utf-8")):
                names[p.get("name", "")] = p
        # characters.md / world.md：## 标题 = 实体
        for fname, kind, key in (("characters.md", "character", "characters"),
                                 ("world.md", "setting", "settings")):
            f = self.project / "bible" / fname
            if not f.is_file():
                continue
            text, _ = splib.read_text(f)
            cur_name, cur_body = None, []
            sections: list[tuple[str, str]] = []
            for line in text.splitlines():
                m = _HEAD_RE.match(line)
                if m:
                    if cur_name:
                        sections.append((cur_name, "\n".join(cur_body).strip()))
                    cur_name, cur_body = m.group(1), []
                else:
                    cur_body.append(line)
            if cur_name:
                sections.append((cur_name, "\n".join(cur_body).strip()))
            for name, body in sections:
                meta = names.get(name, {})
                aliases = json.dumps(meta.get("aliases", []), ensure_ascii=False)
                c.execute("INSERT OR REPLACE INTO entities VALUES (?,?,?,?,?)",
                          (name, kind, meta.get("tier", "minor"), aliases, body[:600]))
                stats[key] += 1
        # 名字在 names.json 但未写进 characters.md 的，也登记（空摘要）
        for name, meta in names.items():
            row = c.execute("SELECT 1 FROM entities WHERE name=?", (name,)).fetchone()
            if not row:
                c.execute("INSERT OR REPLACE INTO entities VALUES (?,?,?,?,?)",
                          (name, "character", meta.get("tier", "minor"),
                           json.dumps(meta.get("aliases", []), ensure_ascii=False), ""))
                stats["characters"] += 1
        # foreshadowing.md：条目行
        ff = self.project / "bible" / "foreshadowing.md"
        if ff.is_file():
            text, _ = splib.read_text(ff)
            for i, line in enumerate(text.splitlines(), 1):
                m = Bullet_RE.match(line)
                if not m:
                    continue
                item = m.group(1).strip()
                status = "closed" if ("已回收" in item or "已收回" in item) else "planted"
                nums = NUM_RE.findall(item)
                c.execute("INSERT OR REPLACE INTO foreshadowing VALUES (?,?,?,?)",
                          (f"f{i}", item[:120], nums[0] if nums else None, status))
                stats["foreshadow"] += 1
        # timeline.json
        tj = self.project / "bible" / "timeline.json"
        if tj.is_file():
            for e in json.loads(tj.read_text(encoding="utf-8")).get("events", []):
                c.execute("INSERT OR REPLACE INTO events VALUES (?,?,?,?,?)",
                          (e.get("id"), e.get("order"), e.get("date"),
                           e.get("description"), json.dumps(e.get("chapters", []),
                                                            ensure_ascii=False)))
                stats["events"] += 1
        # manuscript 章节正文 → 检索表（ord = 文件名数字前缀，供滞留估计按章序排列）
        ms = self.project / "manuscript"
        if ms.is_dir():
            for p in sorted(ms.glob("*.md")):
                text, _ = splib.read_text(p)
                n = splib._clen(text)
                m = re.match(r"\s*(\d+)", p.name)
                c.execute("INSERT OR REPLACE INTO chapters_meta VALUES (?,?,?,?)",
                          (p.name, p.stem, n, int(m.group(1)) if m else None))
                if self.fts:
                    c.execute("INSERT INTO fts_chapters VALUES (?,?,?)", (p.name, p.stem, text))
                # 无摘要的章节回填抽取式摘要（占位；写作流程会覆盖为正规格记）
                has = c.execute("SELECT 1 FROM chapter_digests WHERE chapter=?",
                                (p.name,)).fetchone()
                if not has:
                    first = splib.split_sentences(text)[:2]
                    digest = "".join(first)[:120]
                    c.execute("INSERT OR REPLACE INTO chapter_digests VALUES (?,?,?,?,?)",
                              (p.name, digest, "extractive", n, _now()))
                stats["chapters"] += 1
        c.commit()
        return {"ok": True, "fts": self.fts, **stats}

    # ---- 检索
    def search(self, query: str, k: int = 5) -> list[dict]:
        c = self.conn()
        k = max(1, min(k, 20))
        rows: list[dict] = []
        if self.fts:
            try:
                for r in c.execute(
                    "SELECT path, title, snippet(fts_chapters, 2, '【', '】', '…', 12) AS sn "
                    "FROM fts_chapters WHERE fts_chapters MATCH ? LIMIT ?",
                    (query, k)).fetchall():
                    rows.append({"path": r["path"], "title": r["title"], "snippet": r["sn"]})
            except sqlite3.OperationalError:
                rows = []  # 查询语法不匹配等，走 LIKE 兜底
        if not rows:
            for r in c.execute("SELECT path, title FROM chapters_meta").fetchall():
                fp = self.project / "manuscript" / r["path"]
                body = None
                if self.fts:
                    row = c.execute("SELECT body FROM fts_chapters WHERE path=?",
                                    (r["path"],)).fetchone()
                    body = row["body"] if row else None
                if body is None and fp.is_file():
                    body, _ = splib.read_text(fp)
                if body and query in body:
                    i = body.find(query)
                    rows.append({"path": r["path"], "title": r["title"],
                                 "snippet": body[max(0, i - 40): i + len(query) + 60]})
                if len(rows) >= k:
                    break
        return rows[:k]

    def character(self, name: str) -> dict | None:
        c = self.conn()
        row = c.execute("SELECT * FROM entities WHERE name=? OR aliases LIKE ?",
                        (name, f'%"{name}"%')).fetchone()
        if not row:
            row = c.execute("SELECT * FROM entities WHERE name LIKE ?",
                            (f"%{name}%",)).fetchone()
        if not row:
            return None
        states = [dict(r) for r in c.execute(
            "SELECT chapter, field, value, ts FROM entity_state WHERE entity=? "
            "ORDER BY id DESC LIMIT 3", (row["name"],))]
        return {"name": row["name"], "kind": row["kind"], "tier": row["tier"],
                "aliases": row["aliases"], "summary": (row["summary"] or "")[:400],
                "recent_states": states}

    def recap(self, n: int = 3) -> dict:
        c = self.conn()
        digests = [dict(r) for r in c.execute(
            "SELECT chapter, digest, source FROM chapter_digests "
            "ORDER BY chapter DESC LIMIT ?", (max(1, min(n, 10)),))]
        open_ff = [dict(r) for r in c.execute(
            "SELECT id, title, planted_chapter FROM foreshadowing WHERE status='planted' "
            "LIMIT 10")]
        pending = c.execute("SELECT COUNT(*) AS n FROM pending_deltas "
                            "WHERE status='pending'").fetchone()["n"]
        return {"recent": digests, "open_foreshadow": open_ff, "pending_count": pending}

    def foreshadow(self, status: str | None = None) -> list[dict]:
        c = self.conn()
        if status:
            rows = c.execute("SELECT id, title, planted_chapter, status FROM foreshadowing "
                             "WHERE status=? LIMIT 20", (status,)).fetchall()
        else:
            rows = c.execute("SELECT id, title, planted_chapter, status FROM foreshadowing "
                             "LIMIT 20").fetchall()
        return [dict(r) for r in rows]

    # ---- delta：propose → merge
    def propose_delta(self, payload: dict) -> dict:
        c = self.conn()
        chapter = str(payload.get("chapter", ""))
        if not chapter:
            return {"ok": False, "error": "payload 缺少 chapter"}
        added = []
        for ch in payload.get("changes", []):
            entity = str(ch.get("entity", "")).strip()
            if not entity:
                continue
            risk = ch.get("risk") or self._auto_risk(entity, ch.get("field", ""))
            cur = c.execute("INSERT INTO pending_deltas(chapter, entity, field, value, "
                            "risk, note, ts) VALUES (?,?,?,?,?,?,?)",
                            (chapter, entity, ch.get("field", "state"),
                             str(ch.get("value", ""))[:200], risk,
                             str(ch.get("note", ""))[:120], _now()))
            added.append({"id": cur.lastrowid, "entity": entity, "risk": risk})
        if payload.get("digest"):
            c.execute("INSERT OR REPLACE INTO pending_deltas(chapter, entity, field, "
                      "value, risk, note, ts) VALUES (?,?,?,?,?,?,?)",
                      (chapter, "_digest", "digest", str(payload["digest"])[:200],
                       "low", "章节摘要", _now()))
        c.commit()
        return {"ok": True, "proposed": added, "chapter": chapter}

    def _auto_risk(self, entity: str, field: str) -> str:
        c = self.conn()
        row = c.execute("SELECT tier FROM entities WHERE name=? OR aliases LIKE ?",
                        (entity, f'%"{entity}"%')).fetchone()
        tier = row["tier"] if row else "new"
        if tier == "core":
            return "high"
        if field in ("location", "possession", "mood"):
            return "low" if tier in ("minor", "new") else "medium"
        return "medium"

    def __del__(self):
        try:
            self.close()
        except Exception:  # noqa: BLE001 —— 解释器退出时的兜底
            pass

    def merge_delta(self, ids: list[int] | None = None, force: bool = False) -> dict:
        c = self.conn()
        blocked: list[dict] = []
        if ids:
            rows = [r for r in (c.execute("SELECT * FROM pending_deltas WHERE id=? AND "
                                          "status='pending'", (i,)).fetchone() for i in ids)
                    if r]
        else:
            rows = [dict(r) for r in c.execute(
                "SELECT * FROM pending_deltas WHERE status='pending'").fetchall()]
        merged = []
        for r in rows:
            if r["risk"] in ("medium", "high") and not force:
                blocked.append({"id": r["id"], "risk": r["risk"],
                                "hint": "中/高风险变更需用户确认后 force=true 合并"})
                continue
            if r["entity"] == "_digest":
                c.execute("INSERT OR REPLACE INTO chapter_digests VALUES (?,?,?,?,?)",
                          (r["chapter"], r["value"], "registered", 0, _now()))
            elif r["field"] == "foreshadow":
                c.execute("INSERT OR REPLACE INTO foreshadowing VALUES (?,?,?,?)",
                          (str(r["id"]), r["value"][:120], r["chapter"], "planted"))
            else:
                c.execute("INSERT INTO entity_state(entity, chapter, field, value, ts) "
                          "VALUES (?,?,?,?,?)",
                          (r["entity"], r["chapter"], r["field"], r["value"], _now()))
            c.execute("UPDATE pending_deltas SET status='merged' WHERE id=?", (r["id"],))
            merged.append(r["id"])
        c.commit()
        if merged:
            log = self.project / "bible" / "pending" / "merged.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8", newline="\n") as f:
                f.write(f"## {_now()}\nmerged ids: {merged}\n")
        return {"ok": True, "merged": merged, "blocked": blocked}

    def pending_aging(self) -> dict:
        """pending 滞留报告：按章序估计滞留章数（ord 数字前缀序，字典序在
        "010" 与 "9" 混排时会错乱——v0.2.4 修复；无前缀章节排在最后）。"""
        c = self.conn()
        chapters = [r["path"] for r in c.execute(
            "SELECT path FROM chapters_meta "
            "ORDER BY (ord IS NULL), ord, path")]
        pos = {name: i for i, name in enumerate(chapters)}
        rows = [dict(r) for r in c.execute(
            "SELECT id, chapter, entity, field, risk, ts FROM pending_deltas "
            "WHERE status='pending' ORDER BY id")]
        for r in rows:
            r["aging"] = (len(chapters) - pos[r["chapter"]]
                          if r["chapter"] in pos else 0)
        stale = [r for r in rows if r["aging"] > PENDING_AGING_CHAPTERS]
        return {"stale": stale[:10], "total_pending": len(rows)}
