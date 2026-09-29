# Cursor 适配

Cursor 目前没有原生 Agent Skills 机制，按退化阶梯用「中间态 / 最低保障」两级：

## 中间态：规则文件 + 仓库即文档

1. 把本仓库克隆到本地（与你的写作项目并列或任意位置）
2. 在写作项目根目录的 Cursor Rules（或 `AGENTS.md`）中加入一段指引：

```markdown
## 写作风格工作流（StylePack）
- 风格包库位于 <仓库路径>/stylepacks/，先读其中的 profile.md 与 card.md
- 写作前按 <仓库路径>/core/skills/style-apply/SKILL.md 的协议加载上下文
- 写完运行：python <仓库路径>/scripts/fp_check.py <包目录> <稿子路径>
- 批改按 core/skills/style-critique/SKILL.md 的维度与格式输出
```

Cursor 的 agent 会把这些 SKILL.md 当作过程文档遵循——这正是设计中的降级能力：
**技能文件本身就是可读的操作手册**。

## 最低保障：单文件包

```bash
python scripts/export_pack.py stylepacks/luxun --out luxun.stylepack.md
```

把单文件直接贴进 Cursor 对话（或放进项目让 @ 引用），说「按这个文风写」即可。
无需任何配置。

## 说明

- v0.2 的 MCP server 发布后，Cursor 可通过 MCP 配置获得包检索 / 统计工具
- 指纹验收脚本在 Cursor 内置终端里直接运行，效果与 ZCode 一致
