# StylePack 使用说明

> 版本 0.1.0 · 一句话：把作者文风蒸馏成自包含的风格包，让任何 AI agent 按包写作，
> 并用量化指纹验收"像不像"。

---

## 目录

1. [环境要求](#1-环境要求)
2. [安装](#2-安装)
3. [五分钟上手](#3-五分钟上手)
4. [完整工作流](#4-完整工作流)
5. [技能与脚本参考](#5-技能与脚本参考)
6. [风格包管理](#6-风格包管理)
7. [长篇写作工作区](#7-长篇写作工作区)
8. [常见问题](#8-常见问题)
9. [清理与卸载](#9-清理与卸载)
10. [MCP 记忆层（v0.2）](#10-mcp-记忆层v02)

---

## 1. 环境要求

- **Python 3.8+**（仅标准库，无需 `pip install` 任何东西）
- 一个 AI agent 宿主（可选但推荐）：ZCode / Claude Code 等；
  没有宿主也能用单文件包（见 §3 路线 C）
- 磁盘上任意位置存放本仓库；写作项目与仓库可以分开
- **编码说明**：CLI 与 MCP 恒以 UTF-8 字节输出，stdin 亦按 UTF-8 严格解析
  （当前仅 MCP 服务器读 stdin；将来新增读 stdin 的 CLI 时宿主需按 UTF-8 输入）。
  Windows legacy cp936 交互终端显示中文/emoji 乱码时，执行 `chcp 65001`
  或改用 Windows Terminal；管道与 MCP 协议不受影响

## 2. 安装

按你的宿主选择（详细步骤见 `docs/adapters/` 对应文件）：

| 宿主 | 做法 |
|---|---|
| ZCode | 复制 `core/skills/*` 到 `<工作区>/.zcode/skills/`（工作区级）或 `~/.zcode/skills/`（用户级） |
| Claude Code | 复制 `core/skills/*` 到 `<项目>/.claude/skills/` 或 `~/.claude/skills/` |
| Cursor | 用 Rules/AGENTS.md 指向本仓库技能文件；或直接用单文件包 |
| 其他 / 无宿主 | 仓库克隆下来，agent 读 `docs/usage.md` 与各 SKILL.md；或只用单文件包 |

安装后重开一个会话让技能被发现。验证：对 agent 说「用 stylepack 帮我建个写作工作区」。

## 3. 五分钟上手

> 只是想随手写点什么？不用建工作区、不用懂任何概念——直接对 agent 说
> 「随便写写」「帮我仿一下鲁迅」或「朋友圈文案来一段」，writing 前门会自动
> 走最短路径。下面的路线 A/B/C 是想正经使用时的完整入口。

### 路线 A：我什么都没有，先看看效果（无宿主）

```bash
python scripts/export_pack.py stylepacks/luxun --out luxun.stylepack.md
```

打开 `luxun.stylepack.md`（鲁迅风格包，公版作者，指纹来自真实语料统计），
整份贴进任意 AI 对话，说：

> 按这份文风档案写一段 200 字：冬天清晨的校园。

### 路线 B：有 ZCode / Claude Code，直接开写（自带包）

对 agent 说：

1. 「用 stylepack 建一个写作工作区，项目名叫 my-novel」→ 生成工作区结构
2. 「把鲁迅风格包 pin 进项目」→ 生成 `style/pinned-pack.md`
3. 「按鲁迅风格写第一章：主角回乡」→ style-apply 写作 + 自动指纹验收
4. 「对新写的章节跑一次批改」→ style-critique 独立审计

### 路线 C：我有语料，想蒸馏自己的风格包

见 §4 完整工作流（建档六步）。

## 4. 完整工作流（建档六步）

```
① setup → ② ingest → ③ analyze → ④ 校订 → ⑤ apply+check → ⑥ feedback
```

**① 初始化**：对 agent 说「用 style-setup 建写作工作区」。得到：

```
my-novel/
  manuscript/    bible/    style/    reviews/    corpus/
```

**② 语料入库**：把作者的 txt（任何常见编码）交给 agent：

> 把 C:\books\luxun-full.txt 用 corpus-ingest 入库，作品名"故乡"

脚本自动：编码探测（GBK/UTF-8/UTF-16/BOM）→ 去广告水印 → 章节切分 →
按章落盘 + 统计缓存 + 来源记录。联网抓取的语料请让 agent 记录 URL 与日期
（写进 provenance.json）。

**③ 蒸馏**：

> 用 style-analyze 从语料蒸馏风格包，包名 luxun

脚本算指纹 → agent 分层抽样精读（不通读全书，控成本）→ 产出九章档案 +
范例（短引+批注）+ 词汇表 + **分层量化指纹（按文体自动分层，含层内真迹留一
及格线——任意作者同一流程，见 evals Case H）** + 诚实元数据。

**④ 人工校订（不可跳过）**：agent 逐节呈上草案，你确认/修改；
重点看「生成指导」映射表和「禁用清单」。确认后自动 validate + 钉扎进项目。

**⑤ 写作与验收**：

> 按风格包写第二章：……（style-apply，写完自动 fp_check）
> 对 manuscript 全目录跑一次漂移检测（style-check --per-file）

**⑥ 反馈迭代**：写作中随时一句「feedback：这段对话太文绉绉了」→
记录进日志；累计 5 条后 agent 主动提出档案修订提案，你确认后升版本。
每月可跑一次 A/B 盲测（style-calibrate）看胜率。

## 5. 技能与脚本参考

### 技能（core/skills/，对话触发）

| 技能 | 干什么 | 典型说法 |
|---|---|---|
| writing | 前门路由：口语创作请求分流到下方技能或轻模式 | 「随便写写」「帮我仿一下鲁迅」 |
| style-setup | 建工作区、选类型、接语料或用自带包 | 「初始化写作项目」 |
| corpus-ingest | 语料清洗入库（编码/广告/拆章/统计） | 「把这本 txt 入库」 |
| style-analyze | 蒸馏风格包（统计+精读+档案草案） | 「分析这个作者的文风」 |
| style-apply | 按包写作/续写/改写，写完自动验收 | 「按鲁迅风格写第三章」 |
| style-critique | 独立审计者逐维批改（不改稿） | 「批改这一章」 |
| style-check | 指纹验收 + 逐章漂移检测 | 「检查文风漂移」 |
| consistency-check | 人名/时间线/伏笔/OOC 一致性 | 「查一下设定有没有崩」 |
| style-feedback | 一句话记录反馈，攒批提修订 | 「feedback：……」 |
| stylepack | export/validate/list/pin 包管理 | 「导出单文件风格包」 |
| close-read | 精读拆解（人物图谱/时间线/伏笔表） | 「精读这本小说」 |
| style-calibrate | A/B 盲测胜率校准 | 「测测档案准不准」 |

### 脚本（scripts/，均可独立运行，`-h` 看完整参数）

| 脚本 | 用途 | 一行示例 |
|---|---|---|
| ingest.py | 语料清洗入库 | `python scripts/ingest.py --input a.txt --out corpus/luxun --work 故乡` |
| fp_extract.py | 指纹原始指标 | `python scripts/fp_extract.py corpus/luxun --json fp.json` |
| fp_check.py | 指纹验收/漂移/回归对比 | `python scripts/fp_check.py stylepacks/luxun manuscript --per-file`；`--save-metrics` 留档实测指标，`--baseline` 逐指标前后对比（revise 回归判定） |
| validate_pack.py | 包自包含校验 | `python scripts/validate_pack.py stylepacks/luxun` |
| export_pack.py | 单文件导出 | `python scripts/export_pack.py stylepacks/luxun --out x.md` |
| names_check.py | 专名一致性 | `python scripts/names_check.py --names bible/names.json manuscript` |
| timeline_check.py | 时间线一致性 | `python scripts/timeline_check.py --timeline bible/timeline.json` |
| cost.py | 成本账本（记账/出账/预测） | `python scripts/cost.py log --skill style-analyze --chars 32000`；`cost.py report`；`cost.py forecast --chapters-total 100` |
| story.py | 状态机 CLI（MCP 的等价物） | `python scripts/story.py sync`；`story.py search --query 玉佩`；`story.py recap` |
| build_delta.py | 构建 Burrows Delta 档案 | `python scripts/build_delta.py corpus/luxun --pack stylepacks/luxun` |

退出码约定：0 成功 / 1 未通过（脚本可进 CI）/ 2 用法错误。

## 6. 风格包管理

- **结构**：每个包 7 个必备文件（pack.json / card.md / profile.md / fingerprint.json /
  exemplars.md / lexicon.md / limits.md），可选 tests/（盲测题）
- **自包含是硬约束**：`validate_pack` 拦截包外链接与超长引文（≤200 字）；
  CI 对自带包全量校验
- **单文件**：`export` 产物贴进任何对话即用；分享/PR 以单文件或整个目录为单位
- **版本钉扎**：pin 进项目后，验收一律以钉扎版本为准；包升级重新 pin，
  已写章节历史验收不受影响
- **自带包**：luxun（鲁迅）、zhuziqing（朱自清）——公版作者；
  fingerprint 来自真实语料统计，`pack.json.corpus` 记录了作品清单与置信度

## 7. 长篇写作工作区

| 路径 | 内容 | 谁维护 |
|---|---|---|
| `manuscript/` | 正文按章 `NNN-标题.md` | style-apply |
| `bible/characters.md` | 人物：欲望/恐惧/说话特征/行为红线 | consistency-check 对照 |
| `bible/world.md` | 世界观设定 | 同上 |
| `bible/timeline.json` | 事件（id/order/date/chapters） | timeline_check 校验 |
| `bible/names.json` | 人名+别名（常见错写也放这） | names_check 校验 |
| `bible/foreshadowing.md` | 伏笔账本（埋设/回收/状态） | consistency-check 对账 |
| `style/pinned-pack.md` | 钉扎的风格包（勿手改） | stylepack pin |
| `style/feedback.log` | 反馈流水 | style-feedback |
| `reviews/` | 批改/验收/一致性报告 | 各检查技能 |

约定：**设定冲突以 bible 为准**；bible 落后于稿子时先改 bible。

## 8. 常见问题

**Q：技能没有触发？**
确认复制到了正确目录（`.zcode/skills/` 或 `~/.zcode/skills/`）、重开了会话；
同名技能先发现先加载，检查是否被旧版本遮蔽。

**Q：语料是 GBK 编码 / 乱码？**
ingest.py 自动探测（BOM → UTF-8 → GB18030 → Big5）；极端情况先手动转 UTF-8 再入库。

**Q：fp_check 总是不通过？**
先看偏差最大的 1–2 项：是文本真跑偏（改文本），还是当初容差定得过紧
（改包的 fingerprint，走 style-feedback 流程升版本）。禁止机械凑数字。

**Q：模仿效果一般？**
看 limits.md——本来的预期就分「可模仿 / 部分 / 难模仿」三档。
用 style-calibrate 盲测定位薄弱维度，转 style-feedback 迭代档案。
表层特征（句长、词汇、标点、结构）模仿效果好；世界观、真正的幽默感、独创性只能部分迁移。

**Q：中文分词不准？**
v0.1 用免依赖的字级统计（句长、标点、叠词、字频、四字组），已足够刻画指纹；
装有 jieba 时 fp_extract 自动附加词频增强。

**Q：英文作品能用吗？**
管线通用，v0.1 的指纹口径偏中文（标点集、叠词、四字组对英文意义有限）。
英文包建议以 profile/exemplars 为主、fingerprint 只取句长与对话比。

**Q：怎么控制 token 成本？**
记住四条：
① 全流程只有"模型读正文"最贵，脚本环节（统计 / 验收 / 清洗）零成本——能算的别读；
② 任何多文件读取（建档采样、写作加载、批改）都放在**同一轮并行调用**里读完，
   禁止逐个串行读——agent 每次调用都重发会话历史，串行的实际开销是并行的数倍；
③ 语料 > 10 万字走子代理分工（各读一块、各回 ≤ 800 字摘要），主会话只读摘要；
④ 长篇写作按需降载：短篇段落只装 card + 禁用清单 + 本章 bible 条目；
   多章批改与一致性审查同样分批 / 分派子代理；
⑤ 开销预告与记账：检查类技能开跑前先预告读取规模，大读取后记入
   `<项目>/style/cost.jsonl`（`python scripts/cost.py report` 随时出账）。
以上均已写入相应技能（style-analyze / style-apply / style-critique / consistency-check）
的"成本纪律"小节，agent 执行技能时会自动遵循。

**Q：版权上我要注意什么？**
本地分析你拥有的任何文本，工具不设限。但**不要把受版权保护的全文提交进仓库**；
分享风格包时范例只收短句批注（validate 会拦）；公版作者不受限。

## 9. 清理与卸载

- 卸载技能：删除 `<工作区>/.zcode/skills/` 或 `~/.zcode/skills/` 下对应目录
- 删除项目：写作项目目录是普通文件夹，直接删除
- 删除风格包：删除 `stylepacks/<包名>/`
- 仓库本身：删除克隆目录即可，无注册表/全局状态残留
- 构建期下载物（构建本项目的语料与许可证副本）：见工作区 `downloads/RECORD.md`，
  删除 `downloads/` 目录即可完全清理，不影响本仓库任何功能

## 10. MCP 记忆层（v0.2）

有 MCP 宿主时，agent 可以用 10 个工具替代"直读文件"完成记忆与验收
（配置方法见 [docs/adapters/mcp.md](adapters/mcp.md)）：

- `story.sync / search / character / recap / foreshadow`：检索与提取——
  人物卡、前情提要、伏笔原文，全部返回路径+片段（≤2KB），不再整文件装载
- `story.propose_delta / merge_delta`：写完一章登记状态变更（隔离区）→
  风险分级合并（低风险自动留痕，中/高风险需确认）——与 v0.1.4 的落库仪式同一纪律
- `story.cost_forecast`：记账历史 × 章节进度预测剩余成本
- `stylepack.info`：查包清单与元数据——**name 缺省即列出全部可用包**，name 支持
  目录名（luxun）或中文名（鲁迅）；找不到时返回值带 available 清单，照单可选
- `fp.check`：分层指纹验收——按待测文本文体**自动选层**（小说/散文阈值分开），
  逐指标阈值 + **Burrows Delta 距离**，及格线=层内真迹留一最差篇（n<3 的层
  Delta 仅参考不进判定）；短文（<800 字）Delta 同样只作参考
  （交叉验证 9/9 正确归因）

原则不变：**文件是权威源**。memory.db 只是索引与提取服务，删掉即重建；
无 MCP 宿主时 `scripts/story.py` 提供全部等价能力。
