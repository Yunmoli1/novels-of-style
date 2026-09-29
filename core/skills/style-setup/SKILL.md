---
name: style-setup
description: StylePack 冷启动引导：创建写作项目工作区、选择作品类型、接入语料并生成第一个风格包，或直接用自带公版风格包快速体验。当用户说"开始使用 stylepack / 初始化写作项目 / 建工作区 / 新建风格包 / style-setup"时使用。
---

# style-setup：项目初始化引导

本技能是 StylePack 仓库的入口。仓库根目录含 `scripts/`（零依赖 Python 脚本）、
`stylepacks/`（自带风格包）、`core/skills/`（全部技能）。先定位仓库根目录再继续。

## 引导流程（对话式，逐项确认，不要一次问全部）

### 第 1 步：选择作品类型
- 叙事（网络小说 / 文艺小说 / 短篇）→ 默认，加载 `packs/narrative/REFERENCE.md`
- 游戏剧情脚本、学习资料 → v0.3 类型包尚未发布，如实告知，先按叙事建档

### 第 2 步：创建项目工作区
询问项目名与位置（默认在用户指定目录下创建），生成以下结构：

```
<项目名>/
  manuscript/          # 正文，按章分文件（001-xxx.md）
  bible/
    characters.md      # 人物设定（声线、口头禅、行为边界）
    world.md           # 世界观
    timeline.json      # 时间线（机器可校验，格式见 scripts/timeline_check.py 文档头）
    names.json         # 人名与别名表（供 names_check 使用）
    foreshadowing.md   # 伏笔账本（埋设处 / 回收处）
    pending/           # 设定隔离区：拍子 / 正文产生的新设定先落这里，
                       # 经脚本校验 + 用户确认后才合并进正式文件
  style/
    pinned-pack.md     # 钉扎的风格包（含版本号，勿手改内容）
    feedback.log       # 反馈日志
    calibration.json   # A/B 盲测记录
  reviews/             # 批改与验收报告
  corpus/              # 语料（本地文件，提醒用户加入 .gitignore）
```

### 第 3 步：选择风格来源（三选一）
1. **已有语料建档** → 引导至 `corpus-ingest` 技能，随后 `style-analyze`
2. **联网获取语料** → v0.2 功能，v0.1 请用户自行下载 txt 后走分支 1
3. **先用自带包体验** → 列出 `stylepacks/` 下可用包（如 luxun / zhuziqing），
   直接把所选包内容钉扎进 `style/pinned-pack.md`，跳到试写环节

**收尾动作（不可省略）**：工作区建好后立即 `git init` 并完成首次提交
（`.gitignore` 排除 `corpus/` 与 `style/memory.db`）——这是设定撤销、章节回退与
多机同步的保底机制；用户拒绝时如实告知风险并建议至少手动备份 bible/。

### 第 4 步：收尾验证
- 运行 `python scripts/validate_pack.py <包目录>`（自带包必须通过）
- 若走了建档流程：运行 `python scripts/export_pack.py <包目录> --out <项目>/style/pinned-pack.md`
- 告知用户下一步可用命令：试写（style-apply）、批改（style-critique）、验收（style-check）

## 约束
- 语料属用户本地文件，绝不建议用户把受版权保护全文提交进 git 仓库
- 全程零第三方依赖；只需 Python 3.8+ 与本仓库
