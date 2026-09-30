# StylePack

**让任何 AI agent 获得"作者文风沉淀与模仿"能力的开源插件。自包含、可验收、跨平台。**

把一位作者的文风蒸馏成一个**自包含的风格包**（StylePack）：量化指纹 + 写作指导 + 短句范例。
写作时按需加载，写完自动跑指纹验收；风格"像不像"从感觉变成可测指标。

```
采集 → 量化 → 蒸馏 → 人工校订 → 调用 → 指纹验收 → 反馈 → 档案迭代
```

## 特性

- **自包含**：风格包不依赖原文与插件，`export` 成单文件后贴进任何裸 agent 对话即可用
- **可验收**：句长分布、对话占比、标点指纹、叠词率等指标带容差阈值，生成后逐章比对，漂移当场抓住；Burrows Delta 给出对作者语料库的总体风格距离分值
- **MCP 记忆层（v0.2）**：故事状态机 + 全文检索 + 人物卡/前情提要精准提取，10 个工具单次返回 ≤2KB，调用自动记账
- **跨平台**：任何支持 Agent Skills 目录与/或 MCP 的宿主均可完整使用；无宿主时用单文件包（各宿主安装适配见 [docs/adapters/](docs/adapters/)）
- **零依赖**：所有脚本与 MCP server 仅用 Python 标准库（3.8+），无 pip / npm 安装
- **长篇友好**：人设圣经、时间线、伏笔账本的一致性检查；逐章风格漂移检测
- **诚实档案**：每个包记录语料来源、采样方式与置信度；limits.md 明说哪几维模仿不了

## 快速开始（3 分钟）

```bash
# 0. 环境：Python 3.8+，无任何第三方依赖
# 1. 校验自带风格包（鲁迅 / 朱自清，公版作者）
python scripts/validate_pack.py stylepacks/luxun

# 2. 导出单文件包
python scripts/export_pack.py stylepacks/luxun --out my.stylepack.md

# 3a. 有 agent 宿主 → 安装 skills 后走 style-setup 引导（各宿主路径见 docs/adapters/）
# 3b. 没有任何宿主 → 把 my.stylepack.md 贴进对话，说"按这个文风写一段冬天的集市"
```

完整流程见 **[docs/usage.md](docs/usage.md)**（使用说明书）。

## 仓库结构

```
core/skills/     12 个技能：建档、写作、批改、验收、一致性、反馈、精读、盲测…
packs/           类型包（narrative 已发布；game / learning 于后续版本）
stylepacks/      风格包（自带公版示例：luxun、zhuziqing，含 Delta 档案）
schemas/         pack.json JSON Schema（版本化）
scripts/         零依赖脚本：ingest / fp_extract / fp_check / validate / export / story / cost…
server/          MCP server（JSON-RPC stdio，10 工具）+ 状态机 store
docs/            使用说明与各宿主安装适配
```

## 设计原则

1. **插件不改模型，只改模型看到的上下文与流程** —— 文风学习 = 蒸馏—沉淀—调用闭环
2. **档案是操作手册不是体检报告** —— 描述层（指纹）+ 生成层（指导）+ 示范层（范例）缺一不可
3. **工具不设限，仓库不自带** —— 用户语料保持中立（本地上传 / 联网公开内容均可分析）；
   仓库自身只收录公版示例与短引
4. **不做生成管线** —— 模型会写字，本插件供给上下文与验收标准

版本决策与设计取舍的完整记录见 [CHANGELOG.md](CHANGELOG.md)。

## 路线图

- **v0.2（当前）**：MCP 记忆层、分层指纹与真迹包络（Burrows Delta）、语料扩充与跨包归因、调子分区与示范段路由
- **v0.3（已规划）**：思想层——thought.md 蒸馏"思路的动作"（立意招式 / 意象系统 / 价值姿态）
- **后续**：验收端调子分区（--stratum）、跨作者风格区间、game / learning 类型包、社区档案征集

## 许可与贡献

[Apache-2.0](LICENSE) 。欢迎 PR 新的风格包与类型包 —— 见 [CONTRIBUTING.md](CONTRIBUTING.md)
（含版权纪律：仓库永不收录受版权保护的全文；范例遵循短引 + 批注）。

English: see [README.en.md](README.en.md).
