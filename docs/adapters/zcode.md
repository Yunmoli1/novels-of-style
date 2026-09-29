# ZCode 适配

ZCode 原生支持 Agent Skills（SKILL.md 格式），本仓库技能可直接安装。

## 安装方式

### 方式一：工作区级（推荐先体验）

把技能复制到当前工作区的 `.zcode/skills/`，只在该工作区生效：

```bash
# 在仓库根目录执行（Windows Git Bash / macOS / Linux 通用）
mkdir -p <你的工作区>/.zcode/skills
cp -r core/skills/* <你的工作区>/.zcode/skills/
```

Windows CMD 可用 robocopy：

```bat
robocopy core\skills "<你的工作区>\.zcode\skills" /E
```

### 方式二：用户级（所有工作区生效）

```bash
mkdir -p ~/.zcode/skills
cp -r core/skills/* ~/.zcode/skills/
```

### 方式三：软链接（跟随仓库更新，无需重复复制）

```bash
# macOS / Linux
ln -s <仓库路径>/core/skills/style-apply ~/.zcode/skills/style-apply
# Windows（开发者模式或管理员命令行）
mklink /D "%USERPROFILE%\.zcode\skills\style-apply" "<仓库路径>\core\skills\style-apply"
```

## 注意事项

- 同名技能**先发现先加载**（用户级优先于工作区级）；升级后重开一个会话生效
- 技能内引用的脚本路径是相对仓库根目录的 `scripts/…`，请保持 skills 与 scripts
  的相对位置（整个仓库一起克隆/复制最省事）
- 需要 Python 3.8+ 在 PATH 中（`python --version` 可查）
- 验证安装：会话中直接说「帮我用 stylepack 建个写作工作区」，style-setup 应被触发；
  或在技能管理界面（Settings → Skills）确认技能已列出
