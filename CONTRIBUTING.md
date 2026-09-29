# 贡献指南

感谢参与 StylePack。本项目最欢迎的贡献是**新的风格包**与**新的类型包**，
其次是脚本改进与文档。开工前请先读设计原则（README「设计原则」一节）。

## 贡献风格包（最常见路径）

1. Fork → 建分支 `pack/<包名>`
2. 准备语料：**语料留在你本地**，通过 `corpus-ingest` + `style-analyze` 产出档案；
   仓库里只出现档案（统计结果 + 短引批注），不出现语料全文
3. 包目录 `stylepacks/<包名>/` 必须含 7 个必备文件
   （pack.json / card.md / profile.md / fingerprint.json / exemplars.md / lexicon.md / limits.md），
   建议附 `tests/`（A/B 盲测题）
4. 自检三连，全绿才能提 PR：

```bash
python scripts/validate_pack.py stylepacks/<包名>
python scripts/export_pack.py stylepacks/<包名> --out /tmp/<包名>.md
python -m unittest discover -s tests -v
```

5. PR 描述附：语料规模与采样方式（将写入 pack.json.corpus）、
   A/B 盲测结果（≥50% 才可合并，格式见 evals/cases.md Case E）

## 版权纪律（红线，机器会在 CI 拦）

- **仓库永不收录受版权保护的全文**——无论是语料、附录还是"参考"
- 范例（exemplars.md）遵循**短引 + 批注**：单条引文 ≤ 200 字，`validate_pack` 会拦截超长
- 公版作者（作者逝世超过 50 年，依中华人民共和国著作权法）可收录较多原文；
  在世或仍在保护期的作者，只收短引且建议同时提供"风格描述替代范例"的方案
- `pack.json.license_note` 必须如实说明版权状态；不写"仅供学习"来搪塞
- 用户本地语料（自己的 txt、联网公开内容）如何使用由用户决定，工具保持中立；
  本纪律只约束**进入本仓库分发**的内容

## 贡献类型包（packs/）

v0.3 开放 game / learning。类型包是领域知识文档（REFERENCE.md 形式），
需覆盖：结构约定、bible 文件格式、与风格包的协作点、红线。开 issue 先对齐结构再动笔。

## 脚本贡献

- **只用 Python 标准库**——引入任何第三方依赖的 PR 会被拒绝（零安装摩擦是硬约束）
- Windows / macOS / Linux 三平台可跑；不写 bash 专属语法；不硬编码路径
- 新功能必须带 unittest（tests/），并保证既有 16 项测试全绿
- 输出人类可读优先，JSON 输出结构变更需同步 schemas/ 与文档

## 语义安全（review 必查）

风格包的 profile 指导、exemplars 批注、lexicon 条目**会进入宿主模型的上下文**，
等同依赖代码审查：

- 不得包含指令型语句（"忽略以上规则"类）、伪装的系统提示、或任何诱导宿主
  改变既有工作流的文案
- `validate_pack` 的注入 lint 命中会给出警告——reviewer 必须人工复核语义后才能放行
- 使用者也应只安装可信来源的包；lint 是线索，不是保证

## 提交规范

- commit message：`<area>: <change>`，如 `packs: add luxun stylepack v0.1.0`
- 一次 PR 聚焦一件事；风格包 PR 与脚本 PR 分开提
