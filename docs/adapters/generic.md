# 通用宿主 / 裸 agent 适配

目标：**任何能读文件、能跑命令的 agent** 都能用上 StylePack；实在什么都没有，
一个能贴长文本的聊天窗口也能用。这就是退化阶梯的最低两级。

## 层级 1：有文件与命令执行能力

1. 克隆仓库：`git clone <仓库地址>`（或直接下载 zip 解压）
2. 让 agent 读 `docs/usage.md`（本文件），按需读对应 `core/skills/<技能>/SKILL.md`
3. SKILL.md 是完整的过程文档：步骤、命令、纪律齐全，agent 照做即可
4. 脚本只要求 Python 3.8+ 标准库，任何平台直接跑

适合：自己的 agent 框架、开源 agent（如各类 CLI agent）、IDE agent 等。

## 层级 2：只有聊天窗口（无文件系统）

```bash
python scripts/export_pack.py stylepacks/luxun --out luxun.stylepack.md
```

单文件包内含使用说明 + 精华卡 + 完整档案 + 范例 + 词汇 + 边界 + 指纹附录，
自包含、无外部引用。贴进对话，说「按这份文风档案写作」即可。

局限（如实告知）：
- 没有指纹验收（fp_check 需要本地脚本）——像不像只能靠人判断
- 没有版本钉扎与反馈闭环——迭代靠手工替换文件内容

## 层级 3（规划中）：MCP 宿主

v0.2 发布 MCP server 后，支持 MCP 的宿主（Claude Desktop、Cursor、Cline 等）
可获得包检索、统计、反馈沉淀工具，配置一次全局可用。
