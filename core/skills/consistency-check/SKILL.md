---
name: consistency-check
description: 长篇一致性检查：分层体检（增量模式默认 + 定期全量漂移网），专名表与时间线脚本校验，加人物行为 OOC、认知边界、伏笔回收的模型审查。当用户要求"查一致性 / 查人名 / 查时间线 / 查伏笔 / OOC"时使用。
---

# consistency-check：一致性引擎（分层体检）

**增量模式（默认）**：检查对象 = 新写/变更章节 × 影响面实体——随"变化量"扩展，
不通读全稿。**全量模式（定期漂移网）**：每卷结束 / 每 20–30 章 / 用户要求时触发，
专抓增量抓不住的问题：慢性漂移、全局约束（时间线总量、地理）、弃线复活。
全量用子代理分块（见成本纪律）。

## 第一层：脚本校验（两模式都先跑，零模型成本）

```bash
# 专名一致性（需要 bible/names.json，常见错写放 aliases 里可顺带统计）
python scripts/names_check.py --names <项目>/bible/names.json <项目>/manuscript

# 时间线（需要 bible/timeline.json）
python scripts/timeline_check.py --timeline <项目>/bible/timeline.json --manuscript <项目>/manuscript

# canon 术语保真（二创项目，canon/canon-terms.json 存在时；v0.5）
python scripts/canon_terms_check.py --terms <项目>/canon/canon-terms.json \
  --per-chapter <项目>/manuscript
```

`names.json` / `timeline.json` 缺失时：先提议从 `characters.md` / 现有章节中
抽取生成（列出提取结果请用户确认），再运行检查。
`names_check` 的逐人名出场计数 = 本批影响面清单，直接决定第二层装什么。

## 第二层：模型语义审查（增量范围内的稿件）

对影响面实体（本章出场的 + pending 变更涉及的），只装载这些实体的 bible 条目
与相关章节片段，逐项检查并给证据（章节 + 段落引用 ≤ 40 字）：

1. **OOC**：人物言行是否越出 `characters.md` 的行为边界与声线；
   二创项目的原作人物以 **canon 人物卡（characters.json 的 redline）优先**——
   检查"原作人物像不像原作的人"，项目自拟性格与 canon 冲突时按 canon 报 P1
2. **认知边界**：人物是否说出了/使用了不该知道的信息（谁知道什么，对照 world.md）
3. **伏笔账本**：`foreshadowing.md` 中"已埋未收"条目在本批章节的回收情况；
   新埋伏笔是否已登记
4. **设定冲突**：地名 / 组织 / 规则与 `world.md` 矛盾之处；二创项目加查
   `facts.md` 红线（时间线 / 地理 / 组织 / 科技水平），矛盾即 P1
5. **原作保真（仅二创项目）**：OC 接口核查——names.json 中 OC 实体是否登记了
   接口声明（她是谁 / 为何原作名单里没有她 / 与哪些原作实体相连）；canon core
   人物长期缺勤对照 cast_policy（min_active_canon_chars_per_volume）给提示

## 报告置顶：健康度三行（任何模式都要给）

- **pending 滞留**：`bible/pending/` 中滞留超过 5 章未合并的条目清单
  （稿子可能在用未入库设定，按 pending 内容而非旧 bible 判定这几条）
- **全量距今**：上次全量检查以来新增章数，超过阈值即建议安排漂移网
- **自动合并复核**：`bible/pending/merged.log` 中本批自动合并条目数与摘要
  （低风险自动合并项的抽查对象）

## 成本纪律（硬性）

- **开跑预告 + 落账**：审查前向用户预告模式（增量/全量）与预计读取的章数/字数；
  完成后记一笔账：
  `python scripts/cost.py log --skill consistency-check --chars <字数> --project <项目>`
- **脚本先行缩小范围**：names_check / timeline_check 零模型成本，永远先跑，
  模型只审查脚本覆盖不了的语义项
- **分批装载**：增量模式每次只装 3–5 章 + 相关实体条目，同一轮并行读齐；
  全量模式 > 10 万字按卷分派子代理，各回问题清单，主会话只汇总去重

## 输出

报告写入 `<项目>/reviews/consistency-<日期>.md`：
按严重度排序（P0 逻辑硬伤 / P1 设定矛盾 / P2 遗漏 / P3 建议），
每条附定位与修法建议，并区分"改稿"还是"改 bible"（设定冲突常是 bible 落后于稿——
若冲突源于滞留 pending，先走落库仪式合并再复验）。
