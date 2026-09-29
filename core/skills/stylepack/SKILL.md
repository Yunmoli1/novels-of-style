---
name: stylepack
description: 风格包管理工具：export 导出单文件包、validate 校验自包含性、list 列出可用包、pin 把包按版本钉扎进项目。当用户要求"导出风格包 / 校验风格包 / 列出风格包 / 钉扎 / pin / stylepack"时使用。
---

# stylepack：包管理

统一入口（脚本均在仓库 `scripts/`，零依赖）：

## export —— 导出自包含单文件

```bash
python scripts/export_pack.py stylepacks/<包名> --out <输出路径>.md
```

单文件 = 使用说明 + 精华卡 + 完整档案 + 范例 + 词汇 + 边界 + JSON 附录。
贴进任何裸 agent 对话即可按该文风写作，无需插件、无需原文、无需语料。

## validate —— 校验自包含性

```bash
python scripts/validate_pack.py stylepacks/<包名>
```

检查：必备文件、pack.json 字段、card ≤400 字、范例 ≥6 条且单条引文 ≤200 字、
指纹指标带容差 ≥5 项、无包外链接（自包含）、profile 章节骨架。
报错先修后用；此命令也是 CI 关卡。

## list —— 列出可用包

遍历 `stylepacks/`，对每个子目录读 `pack.json` 汇报：
包名 | 展示名 | 语言 | 类型 | 版本 | 语料置信度。

## pin —— 把包钉扎进项目

1. 确认目标项目（含 `style/` 目录；没有则先走 style-setup 建工作区）
2. 读包的 `pack.json` 取 `version`
3. 运行 export 输出到 `<项目>/style/pinned-pack.md`，文件头注明：
   `<!-- pinned: <包名> v<版本> at <日期> -->`
4. 提醒用户：**钉扎后项目内验收一律以该版本为准**；升版本需重新 pin，
   已写章节的历史验收不受影响（版本钉扎语义）
