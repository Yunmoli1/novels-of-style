# StylePack

**Open-source plugin that gives any AI agent the ability to distill, store, and imitate an author's writing style. Self-contained, verifiable, cross-platform.**

StylePack distills an author's style into a **self-contained style pack**: quantitative fingerprints + generative guidance + annotated exemplar quotes. Load it on demand when writing, then run automated fingerprint acceptance checks — style similarity becomes a measurable metric instead of a feeling.

```
collect → quantify → distill → human-review → apply → fingerprint check → feedback → iterate
```

## Highlights

- **Self-contained**: a pack needs no source corpus and no plugin; `export` compiles it into a single Markdown file you can paste into any bare agent chat
- **Verifiable**: sentence-length distribution, dialogue ratio, punctuation fingerprint, reduplication rate — each with tolerance thresholds, checked per chapter to catch style drift
- **Cross-platform**: full experience on ZCode; skills work directly on Claude Code / Cursor; single-file packs work anywhere
- **Zero dependencies**: all scripts are Python stdlib only (3.8+)
- **Long-form friendly**: character bible, timeline and foreshadowing consistency checks; per-chapter drift detection
- **Honest profiles**: every pack records corpus provenance, sampling method and confidence; `limits.md` states plainly which dimensions cannot be imitated

## Quick start

```bash
python scripts/validate_pack.py stylepacks/luxun     # built-in public-domain packs
python scripts/export_pack.py stylepacks/luxun --out my.stylepack.md
# Paste my.stylepack.md into any chat: "Write a winter market scene in this style."
```

Full guide: [docs/usage.md](docs/usage.md) (Chinese; adapters in docs/adapters/).

## Layout

`core/skills/` — 11 skills · `packs/` — genre packs · `stylepacks/` — style packs ·
`schemas/` — JSON Schema · `scripts/` — stdlib-only tools · `evals/` — golden cases · `docs/`

## Roadmap

v0.1 (current): narrative loop MVP · v0.2: MCP server, ZCode plugin packaging, web corpus ingestion ·
v0.3: game/learning packs, format v1 freeze.

License: [Apache-2.0](LICENSE). Contributing: [CONTRIBUTING.md](CONTRIBUTING.md) — copyright discipline applies: the repo never hosts copyrighted full texts; exemplars are short annotated quotes only.
