# Claude Code 适配

Claude Code 支持 Agent Skills（SKILL.md 格式），与本仓库技能同构。

## 安装

```bash
# 项目级（跟随仓库，团队共享）
mkdir -p <你的项目>/.claude/skills
cp -r <stylepack仓库>/core/skills/* <你的项目>/.claude/skills/

# 个人级（所有项目）
cp -r <stylepack仓库>/core/skills/* ~/.claude/skills/
```

## 使用

- 触发：对话中表达意图即可，如「用 stylepack 给鲁迅建个风格包」→ style-analyze；
  也可以在提示里点名技能
- 脚本：Claude Code 的 Bash 工具直接运行 `python scripts/…`，需 Python 3.8+
- 子代理：style-critique 建议用 Claude Code 的 Task/subagent 在独立上下文跑
  （符合审计者分离原则）

## 差异说明

- ZCode 特有的配置界面（Settings → Skills）在 Claude Code 中不存在，
  技能发现走 `.claude/skills/` 目录扫描
- 其余技能行为（触发条件、脚本用法）与 docs/usage.md 描述一致
