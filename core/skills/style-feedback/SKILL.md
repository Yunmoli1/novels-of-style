---
name: style-feedback
description: 零摩擦记录用户对风格生成结果的反馈到 feedback.log，累积满 5 条后提出风格包修订提案（含 diff），经确认后应用并升版本。当用户说"feedback / 记住这个反馈 / 这段不像，记下来"时使用。
---

# style-feedback：反馈沉淀

## 记录（零摩擦：一句就收，不多问）

向 `<项目>/style/feedback.log` 追加：

```
## 2026-09-28 21:05
- <用户原话或一句话概括>（<可选：章节/段落定位>）
```

记录即返回，除非用户继续追问，不做分析、不展开。

## 批量修订提案（自上次「APPLIED」标记后累计 ≥ 5 条时主动触发）

1. 通读新反馈，聚类成主题（如"对话太文""节奏拖""某个词出戏"）
2. 逐主题给出档案修订提案：改 `profile.md` 哪一节（附 diff 草案）、
   `lexicon.md` 增删哪些词、`fingerprint.json` 是否需要调容差
3. **逐条请用户确认**，确认后应用并：
   - `pack.json` 的 `version` 升一位（0.1.x → 0.2.0 或 0.1.1，视改动面）
   - `changelog` 追加 `{version, date, changes}`
   - 在 feedback.log 追加 `## APPLIED <日期> → v<版本>` 标记
   - 重跑 `validate_pack`，并提示：**已写章节仍按旧版验收**（版本钉扎语义）

## 边界

- 反馈涉及"像不像"的判断，一律以钉扎包为准；用户想换包/升版本走 stylepack pin
- 提案只改档案，不改 manuscript；改稿走 style-apply / style-critique
