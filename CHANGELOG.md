# Changelog

所有显著变更记录于此。格式参照 Keep a Changelog，版本遵循 SemVer。

## [0.2.9] - 2026-09-30

### Added
- **调子分区 registers.md（R0）**：luxun 包新增可选文件——情感轴 3 分区
  （沉郁哲思 11 / 冷峻讽刺 9 / 温情回忆 7）+ 节奏轴 3 分区（对话场 20 /
  白描场 7 / 抒情场 7），61 篇逐篇标注主/次调子 + 一句依据；朝花夕拾·后记
  除名（考据跋文自述声口稀薄，不适配任何调子）。写作时按**声明的调子**
  路由示范段——只影响上下文选择，不参与验收判定（验收端指纹分区
  `--stratum` 属后续版本）
- exemplars.md 全部 12 条带「调子：」机器可读行，与 registers 示范段路由
  互为镜像；新增示范段 11（温情回忆·《从百草园到三味书屋》）、
  12（冷峻讽刺·《父亲的病》），六个分区均有示范段
- validate_pack 新增 registers 六项校验：引用完整性 / 调子值域 / 跨文件
  查重（分区名 vs profile 章节 vs 范例标题）/ 注入扫描覆盖 / 引文 ≤200 字 /
  双向一致；pack.json 增可选能力标记 `registers`
- export_pack 条件段机制：包内有 registers.md 才并入「调子分区」节
  （定位断言锁定正文区段），无则导出与旧版完全一致；v0.3 的 thought.md
  将复用同一机制
- tests/test_registers.py：14 项正负例（luxun 副本变异法）

### Changed
- MCP `stylepack.info` 返回的 info 载荷中 changelog 只保留最新一条：
  changelog 随包增长必然撑爆 2KB 返回纪律（luxun 0.3.0 实测触发
  truncated，结构性问题而非个例）
- pack.json corpus 元数据对齐 62 篇现实（v0.2.8 遗留缺口：仍列 5 篇
  19080 字）→ 集级条目 + 208,039 字 + 置信度更新；pack.json 0.2.1→0.3.0
- 技能路由：style-apply 拍子确认增加**调子声明位**、示范段按声明调子的
  分区挑选；writing 轻模式按请求中的调子词路由；`.zcode/skills/` 与
  `core/skills/` 双副本同步

## [0.2.8] - 2026-09-29

### Added
- **鲁迅语料扩充（Case G 主体完成）**：《野草》全本 24 篇 +《朝花夕拾》13 篇 +
  《呐喊》《彷徨》全部小说（含《阿Q正传》）共 62 篇 20.4 万字入库
  （GitHub Ac-heron/luxun，commit 固定；SSH 克隆 + git show 读对象库，
  绕开 raw.githubusercontent 不可达与 API 限流）
- 分层指纹重建（语料扩充即触发 pack.json 0.2.0→0.2.1 联动升版）：
  **essay 层 n=2→26，留一线从不可标定 → 1.677**；**narrative 层 n=3→36，
  留一线 18.99 → 1.981（收紧 9.6 倍）**——v0.2.3 时代的两大已知限制解除
- docs/corpus-sources.md 登记表更新：抓取经验（对象库读取法）、清洗纪律
  （编者脚注区整段截断、□ 缺字符保留原则）、朱自清/新作者待源状态

### Changed
- **跨包归因测试改分层口径**（test_cross_validation_layered）：每篇真迹按文体
  选层比较自包/对方包同层档案——预分层混合档案口径随 luxun 语料结构变化失真
- **如实下调归因声明**：luxun 侧 5/5 全对；zhuziqing 语料仅 4 篇（源站当日
  不可达待补），essay 层对自家作品归因余量 < 0.2，两篇误归——当前诚实下限
  7/9（阈值 0.7 + 误归清单断言）；**散文层作者鉴别结论改为"跨包相对归因"，
  绝对包络只答"是否在真迹范围内"**（背影→luxun 在 26 篇包络内通过，如实记录）
- evals Case F 更新（新线数值 + 包络宽度教训）；Case G 标记 luxun 完成、
  zhuziqing 待源

### 诚实声明
- 朱自清补篇与新作者语料：维基文库 / ccview / raw.githubusercontent 当日均
  不可达，GitHub 无全集类仓库——登记表已列备选源与最快路径（用户侧提供 txt）
- 语料不入仓库（版权红线）；本次仅包指纹与元数据入仓库

## [0.2.7] - 2026-09-29

### Changed
- **GBK 冒烟补强（codex v0.2.6 复审三条低危残留，全采纳）**：
  - timeline_check 从 --help 换成**真实工具路径**（最小 timeline.json fixture，
    断言"时间线一致"）
  - cost report 补关键词断言（"读取字符"表头）
  - 8 个 CLI 拆为 `subTest`——失败精确指认到具体 CLI，不再一揽子报一个 failure
- windows-gbk CI job 导出补齐 zhuziqing，与 ubuntu job 完全对齐

## [0.2.6] - 2026-09-29

### Fixed
- **story.py 全量崩溃（GBK 冒烟测试当场抓获）**：v0.2.5 自动插桩
  `force_utf8_stdio()` 时，story.py 没有模块层 splib 导入，任何调用都在
  main 第一行 NameError——补 `import splib` 与 scripts 路径
- encoding 纪律说明：本条证明「代码层调用了」≠「实跑可用」，冒烟测试
  （而非仅看代码）是编码纪律的最终验证

### Added
- **全 CLI GBK 冒烟测试**（codex 复审 P2）：fp_extract / ingest / export_pack /
  cost log+report / story sync / names_check 真实实跑并断言关键词
  （"总字符数 / 入库完成 / 已导出 / 已记账 / ok"），timeline_check 走
  --help 路径——不只看返回码，防 errors=replace 把编码错误吞成乱码漏判
- windows-gbk CI job 镜像 ubuntu job 的 validate/export 冒烟（codex 复审 P3.1）

### Changed
- usage.md 编码说明补充 stdin 契约：stdin 亦按 UTF-8 严格解析（当前仅 MCP
  读 stdin），将来新增读 stdin 的 CLI 时宿主需按 UTF-8 输入（codex 复审 P3.2）

## [0.2.5] - 2026-09-29

### Fixed
- **v0.2.4 回归：默认 cp936 下 test_genre 两项报错（codex 复审 P1，已复现）**：
  force_utf8_stdio 让子进程输出 UTF-8，但 test_genre 的 `subprocess(text=True)`
  未指定 encoding，父进程按 locale（cp936）解码 → UnicodeDecodeError →
  stdout=None。5 处全部补 `encoding="utf-8", errors="replace"`
- **编码纪律补全**：v0.2.4 只重配了三个"崩溃点"入口；build_delta / fp_extract /
  export_pack / ingest / cost / story / names_check / timeline_check 在 cp936
  管道输出 GBK 字节，UTF-8 宿主读到乱码——**所有 CLI 入口**统一 force_utf8_stdio

### Changed
- CI 新增 **windows-gbk job**（PYTHONIOENCODING=cp936 跑全量测试）——"默认环境
  健壮"由 CI 持续守护，不再依赖本地环境巧合（codex 复审 P1 建议 2）
- 「接近及格线」措辞修正为"仅供判读留意，不影响判定"（codex 复审 P3.2；
  判定语义本就未变，改措辞消除歧义）
- schema 说明 format_version = pack.json 结构版本，与内容版本 version 无关
  （codex 复审 P3.1：本版变更在 fingerprint.json，pack.json 结构未动，
  format_version "0.1" 保持正确，不升）
- usage.md 编码说明：CLI/MCP 恒为 UTF-8 字节，legacy cp936 交互终端建议
  `chcp 65001` 或 Windows Terminal（codex 复审 P2 采纳文档化变体；拒绝
  ASCII 降级——乱码仅是显示问题且 errors=replace 已防崩，ASCII 化牺牲
  UTF-8 主流场景）

### Measured
- 三环境全绿（47 项）：默认 / 强制 PYTHONIOENCODING=cp936 / cp936 父环境
  跑 GBK·分层·stdio 三套子进程测试

## [0.2.4] - 2026-09-29

### Fixed
- **Windows 默认 GBK 控制台/管道下的编码崩溃（codex 审查 P1，已复现）**：
  validate_pack / fp_check 的 emoji 报告与 MCP 的 ensure_ascii=False JSON 载荷
  在 cp936 流上 UnicodeEncodeError 或被本地代码页污染。三入口（两个 CLI main
  + MCP run_stdio）统一 `force_utf8_stdio()` 重配标准流为 UTF-8（流被宿主
  替换时静默跳过，errors 容错保输出不断流）。旧测试全绿系侥幸——中文可被
  GBK 编码而 emoji 不能
- `build_delta` 普通模式漏写盘的回归（v0.2.3 引入：只在 --layered 分支写文件）
- **pending_aging 字典序错乱（codex 审查 P3）**：章节号 "010" 与 "9" 混排时
  滞留估计失真——chapters_meta 新增 ord 列（文件名数字前缀），按章序排列；
  旧库自动迁移（db 是可重建缓存，schema 不合即删表待 sync 重建）

### Added
- **GBK 环境回归测试**（tests/test_gbk_console.py，3 项）：显式
  PYTHONIOENCODING=cp936 的最恶劣环境下，validate_pack / fp_check 入口不崩、
  MCP stdio 按 UTF-8 字节可解析——把"侥幸绿"变结构性绿，同时补齐
  validate_pack.main / fp_check.main 的入口级覆盖（codex 审查 P2）
- **指纹变更联动 pack.json 升版**：build_delta 比对新旧指纹内容，实际变化才
  patch +1、刷新 updated、changelog 追加重建记录；无变化明确打印"版本不动"
  （codex 审查 P2：两包元数据曾停在 0.1.0 而指纹已分层化，两包已手动对齐 0.2.0）
- 文体判定输出**边界距 margin 连续值**（报告行可见，软化决策留待后续调参）；
  Delta 超及格线 80% 时报告追加"接近及格线，置信降级"（codex 审查 P3 轻量版）
- 统计口径文档化：叠词率仅 AA 型、四字组为非重叠滑窗（style-analyze 与
  fingerprint schema 注明，勿夸大特征覆盖面）

### Changed
- 每版本改动清单移入工作区 `Zcode改动清单及版本/`（自本版起）
- 测试 47 项（+3 GBK 回归）

## [0.2.3] - 2026-09-29

### Added
- **分层指纹（per_genre）**：fingerprint.json 新增 `genres.{narrative,essay}`
  （各层独立阈值树 + Delta 档案）与 `self_check`（层内留一真迹包络）；
  语料阈值容差由**层内各篇实测散布 ×1.2** 推导（固定比例容差会被罕见指标的
  跨篇波动击穿——真迹曾挂自己层线）；稀疏标点不入树防「指标缺失」误杀
- **文体检测器**：双信号（段首引号段占比 + 引号字占比）——嵌入叙述段的对话
  （孔乙己型）靠引号字占比识别；边界附近置信降级为 medium 并如实入报告
- **统一验收路径 layered_check**：fp_check CLI 与 MCP fp.check 共用——auto
  按待测文本文体选层（无层降级混合并明示）、Delta 及格线=层内真迹留一最差篇
  （"至少要像真迹里最不像的那篇"）、短文（<800 字）Delta 只作参考不进判定、
  800–1200 字标"置信中"
- `fp_extract --genre-layers` 分层预览；`build_delta --layered` 一键重建分层指纹；
  validate_pack 对 genres/self_check 施加与顶层同等的阈值纪律
- **evals Case F/G**：分层验收金标准（9 校准点固化，离线可跑）+ 语料扩充重算流程；
  docs/corpus-sources.md 公版源登记表（工具链不内容）

### Fixed
- build_delta_profile 的 std 下限被 `round(…,4)` 归零的潜在除零（仅防零，
  不改既有数值——交叉验证 9/9 保持）
- n=2 层的 Delta 档案是数学退化（任意文本距离恒为 1.0），不再入库，
  运行时回退混合档案作参考值
- 频率语义下「没写=0」：阈值树内缺失路径补 0.0，不再按「指标缺失」判死

### Measured（分层验收矩阵，9 校准点）
- 真迹过线 5/5：秋夜/风筝→luxun essay ✅；孔乙己/故乡/祝福→luxun narrative ✅；
  背影→zhuziqing ✅（混合指纹时代真《秋夜》曾挂 9/12）
- 错作者拒绝 3/3：背影→luxun ❌6/11、匆匆→luxun ❌7/11、秋夜→zhuziqing ❌3/12
- AI 文本落位正确：文1/文2 均不达标，Delta 排序 文2(1.55)<文1(1.67)<真迹(≈1.03)
- 已知限制如实入档：luxun essay 层 n=2 线不可标定；narrative 层留一线偏松
  （小样本方差）；essay 层绝对包络尚不能单独区分作者（指标与 Delta 互补）

### Changed
- **通用性正式化（作者无关）**：新增 schemas/fingerprint.schema.json——分层指纹
  格式契约，genres 层名开放（v0.3 类型包可扩展），全部字段对任意作者语料同构；
  style-analyze 建档流程把 `build_delta --layered` 分层指纹列为标准步骤
  （替换被实测证伪的手拍容差指引）；evals Case H 固化任意作者建档验收模板；
  测试 TestGenericAuthorPipeline 以合成语料走 CLI 全链路，不依赖自带包
- style-check / style-apply / usage.md / MCP fp.check 描述同步分层语义；
  测试 +10（检测器 / 散布容差 / 层内留一 / 统一路径 / CLI 退出码 / 通用性），
  共 44 项

## [0.2.2] - 2026-09-29

### Fixed
- **stylepack.info 三处接口缺陷**（实测"仿鲁迅"暴露，宿主全程未取到包清单）：
  - name 缺省时返回可用包清单（成功路径），不再落入错误路径——"列出包"是
    高频意图，不该走报错
  - 协议层 isError 包装不再丢弃载荷其余字段：此前错误返回里的 `available`
    自救清单被整体替换成一行错误文本，宿主从未收到可用包列表，是误判
    "没有风格包"的直接原因
  - 支持中文名查找：pack.json 的 `display_name`（鲁迅 / 朱自清）作为查找别名，
    与目录名（luxun / zhuziqing）等价
- **writing 前门补三条实测教训**：仓库根定位协议（特征目录法：`stylepacks/` +
  `scripts/` + `core/skills/`，cwd 与仓库根不同层是常态）；取包路径改 MCP 首选
  （stylepack.info 自定位，与 cwd 无关，优先于文件浏览）；失败行为规范——
  未亲眼列出的目录禁止断言"为空 / 不存在"，点名作者套包失败必须上报选项
  （修路径套包写 vs 凭印象直写并声明无验收），禁止静默滑向后者

### Added
- 测试 +1（协议级）：stylepack.info 缺省清单 / 中文别名 / 错误载荷保留 available

### Changed
- stylepack.info 工具描述同步新语义；docs/usage.md MCP 工具表补 stylepack.info 行

## [0.2.1] - 2026-09-29

### Added
- **前门技能 writing**：只路由不写正文的接待员——口语创作请求（随便写写 /
  朋友圈文案 / 续写第三章 / 拆解这本书）从上往下匹配路由表分流到对应技能；
  锚点 + 类别泛化匹配（非穷举），条件默认双向成立（提及自己的章节走项目模式，
  项目目录内说"直接写"走轻模式）；路由落定后读取目标技能 SKILL.md 执行，
  不复述流程；description 含显式排除项（非创作请求不触发）
- **轻模式**：一次性小写作最短路径（≤3 个工具调用）——气质匹配优先于默认包
  （"朋友圈文案"不硬套鲁迅），套包只装 card + 禁用清单（≤1KB），支持单文件包
  直读，跳过拍子确认 / 工作区 / 落库 / 记账
- style-apply 增 **MCP 自动化条款（透明编排）**：连接 MCP 时 story.sync →
  story.recap / story.character 替代直读 bible 与上章结尾，写完
  story.propose_delta 登记、fp.check 快速判定；正式验收留档仍走本地
  fp_check.py（MCP 版暂不带留档与 --baseline 参数）；无 MCP 按原协议读文件，
  两条路径不混用

### Changed
- style-apply description 显式让位：无项目的一次性小写作由 writing 前门承接
- 输出语域规则（意图语言面向用户、工具名只出现在诊断语境）同时写入
  writing 与 style-apply
- docs/usage.md 入口更新：非作者用户从 writing 前门进入；技能表新增 writing 行

## [0.2.0] - 2026-09-28

### Added
- **MCP server**（stdlib 手写 JSON-RPC 2.0 over stdio，最小子集 initialize / tools /
  ping）：10 个工具——story.sync / search / character / recap / foreshadow /
  propose_delta / merge_delta / cost_forecast、stylepack.info、fp.check；
  单次返回 ≤ 2KB、每次调用自动记账（与 cost.py 同账本）
- **记忆层 store.py**：SQLite 状态机（entities / entity_state / pending_deltas /
  chapter_digests / foreshadowing / events / chapters_meta）；
  FTS5 全文检索，缺席自动回退 LIKE；文件仍是权威源（sync 单向导入，可删可重建）
- **Burrows Delta 指纹**：splib 档案构建与距离计算；fp_extract --delta-profile、
  fp_check --delta / --delta-max、build_delta.py；两个自带包已内嵌 Delta 档案
- **双暴露 CLI**：scripts/story.py（sync / search / character / recap / foreshadow /
  propose / merge / aging），与 MCP 工具共用同一实现
- **交叉验证实验**：鲁迅 / 朱自清全部 9 部作品对自包 Delta 距离均小于对方包（9/9）
- 测试 +10：状态机风险分级与合并、MCP 协议握手、交接测试（机械化）、返回纪律、
  真实子进程 stdio 端到端、Delta 分离（合成 + 真实包）

## [0.1.4] - 2026-09-28

### Added
- **落库风险分级**：低风险设定自动合并 + `merged.log` 留痕 + 章末批量摘要；
  中风险批量确认；核心人物变动 / 关键道具 / 伏笔阻断确认——确认成本随风险
  而非数量增长（names.json 新增 `tier` 字段约定）
- **一致性分层体检**：增量模式设为默认（新章 × 影响面实体，不通读全稿），
  全量模式改为卷末 / 每 20–30 章的定期漂移网；报告置顶健康度三行
  （pending 滞留 / 全量距今 / 自动合并复核）
- **注入 lint**：validate_pack 启发式扫描包文件中的指令型语句并警告；
  CONTRIBUTING 增语义安全 review 条款（第三方风格包按第三方代码对待）
- **语料体检**：style-analyze 增多来源交叉验证与离群章节警告，结论进档案元数据
- **盲测制度化**：style-calibrate 每卷必跑，胜率下滑 ≥20 点触发档案复审；
  narrative 包工作流表同步
- **可撤销保底**：style-setup 工作区默认 git init + 首次提交
- style-apply / consistency-check：收尾自检清单（防静默跳步）

### Changed
- v0.2-计划书：工具上限改乘法口径（≤10 元工具 × action ≤5，跨资源不合并）；
  merge_delta 风险分级；指纹 per_genre 分层、跨章趋势检测、盲测为最终裁判
- 版权边界维持既有"仓库不自带全文"纪律，不新增约束（使用侧合规由使用者自负）

## [0.1.3] - 2026-09-28

### Added
- **bible 隔离区**（外部建议采纳）：拍子 / 正文的新设定落 `bible/pending/`，
  经脚本校验（names_check / timeline_check）+ 用户确认两道门后才合并进正式 bible；
  style-setup 工作区模板同步
- fp_check：`--save-metrics` 留档实测指标、`--baseline` 逐指标前后对比，
  「基线通过而本次超差」标记为回归——revise 回滚有了精确的 before/after 数值
- cost.py：`forecast` 子命令——记账历史 × 章节进度预测剩余成本（字符量代理估算，
  明示 ±40% 误差与"生成 token 不可见"口径）

### Changed
- style-apply：写前共创的设定落库改为隔离区仪式；写完验收留档指标；revise 复验引入基线对比
- v0.2-计划书：`apply_delta` 拆分为 `propose_delta` / `merge_delta` 两段式；
  新增 `story.cost_forecast` 工具；新增工具纪律（≤10 上限、描述规范、单一首选路径）

## [0.1.2] - 2026-09-28

### Added
- style-apply：**写前共创**（本章拍子表经用户确认后才生成正文，先干后写防废稿）
  与**局部重写 revise 模式**（按批改报告 P0/P1 定位只改被点名段落，不重写全章）
- 开销预告 + 落账条款写入 style-analyze / style-critique / consistency-check
- `scripts/cost.py`：成本账本（log 记账 / report 出账，落 `<项目>/style/cost.jsonl`）
- `v0.2-计划书.md`：MCP 记忆层设计（故事状态机 + FTS5 RAG + Burrows Delta 指纹）

## [0.1.1] - 2026-09-28

### Changed
- 成本纪律写入技能流程（硬性条款）：style-analyze / style-apply / style-critique /
  consistency-check 强制"同一轮并行批量读取，禁止串行逐个读"；语料 > 100k 字与
  多章批改 / 全篇一致性审查改为子代理 map-reduce（各读一块、各回摘要）
- usage.md 增补「怎么控制 token 成本」FAQ

## [0.1.0] - 2026-09-28

### Added
- 核心脚本（零标准库外依赖）：`ingest`（语料清洗入库）、`fp_extract`（指纹提取）、
  `fp_check`（指纹验收与漂移检测）、`validate_pack`（自包含校验）、`export_pack`
  （单文件导出）、`names_check`（专名一致性）、`timeline_check`（时间线一致性）
- 11 个技能：style-setup / corpus-ingest / style-analyze / style-apply /
  style-critique / style-check / consistency-check / style-feedback /
  stylepack / close-read / style-calibrate
- narrative 类型包结构知识（REFERENCE.md）
- 自带公版风格包：鲁迅（luxun）、朱自清（zhuziqing）——指纹来自真实语料统计
- StylePack 格式 v0.1 定义：pack.json Schema、fingerprint 结构、九章 profile 骨架
- 评估用例（evals/cases.md，Case A–E）与 CI（unittest + 包校验 + 导出冒烟）
- 双语 README、CONTRIBUTING（版权纪律）、docs/usage.md 使用说明与宿主适配文档
