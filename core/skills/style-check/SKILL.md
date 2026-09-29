---
name: style-check
description: 逐章运行风格指纹验收与风格漂移检测（fp_check --per-file），输出量化报告与逐章趋势。当用户要求"检查文风 / 验收 / 漂移检测 / style-check"时使用。
---

# style-check：指纹验收与漂移检测

## 用法

```bash
# 单章 / 合并验收
python scripts/fp_check.py <包目录> <文本或目录> --report <项目>/reviews/fp-report.md

# 逐章漂移检测（manuscript 全目录）
python scripts/fp_check.py <包目录> <项目>/manuscript --per-file --report <项目>/reviews/drift-report.md
```

退出码 0 = 通过；1 = 存在不达标项。`--per-file` 时逐章给出一行结论，便于横向看漂移。
分层包（fingerprint 含 genres）自动按每章文体选层——对话多的章走小说阈值，
纯叙述走散文阈值；报告首行给出文体判定与置信度，置信 medium 的章说明文体
混杂，判读时留意。
留档用：加 `--save-metrics <路径>.json` 保存实测指标，之后任何一次复验都可用
`--baseline <该文件>` 做逐指标前后对比——style-apply 的 revise 回归判定即依赖它。

## 报告解读

- 单指标偶发偏差：该章局部问题，按偏差最大的 1–2 项定向修订
- 连续多章同向偏差（如句长 P50 逐章上升）：**风格漂移**，回看最近几章的写作上下文
  是否漏了章节锚定，必要时整段重写而不是局部补丁
- 「指标缺失」：输出文本太短或全空行，先补文本再验

## 与 style-critique 的分工

本技能只管**可测指标**（句长、对话比、标点、叠词）；像不像的"质感"判断交给
style-critique。两者都通过才算验收通过。

## 纪律

- 验收用项目钉扎的包版本；换包版本需走 stylepack pin 并记录
- 报告统一落 `reviews/`，文件名含日期，不覆盖历史报告
