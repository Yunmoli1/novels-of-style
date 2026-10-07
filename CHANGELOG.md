# Changelog

所有显著变更记录于此。格式参照 Keep a Changelog，版本遵循 SemVer。

## [0.5.2] - 2026-10-07

### Added
- **网页工作台阶段 0**（计划书 r4 落地；原定版本号 v0.5.0 已被 canon 层占用，
  顺延为 0.5.2；零依赖静态站点）：
  - `web/build_site.py`：判读台（8 回合人工判读，纯客户端 localStorage +
    导出 JSON）/ 包浏览器（全档渲染）/ 测量可视化（指标容差表、LOO 留一线、
    motif SVG 横条图）
  - **双击入口**：`启动工作台.bat` → `web/launch.py`（构建站点 + http.server
    仅绑 127.0.0.1 随机端口 + 自动开浏览器，无需手动命令行）
  - `scripts/migrate_human_judging.py`：盲测人工判读包 md → 双 JSON，守卫断言
    （8 回合 / 带包臂序列 乙甲乙甲甲乙乙乙 / 子代理战绩 6/8）；
    `evals/human_judging.json` 入仓库，**答案卷 gitignore**（红线 6）
  - `scripts/score_human_judging.py`：判读导出计分——辨认带包臂命中率 +
    与子代理判官一致率（同源偏差度量），答案卷缺失时给出补救指引
- `tests/test_web.py`（12 项）：产物无全文（语料 250 字窗口断言 > 短引上限）、
  判读页无答案、封闭构建、仅本机绑定、bat 入口接线；总测试 100+9 → **112+9**
- `web/README.md`；计划书：网页控制台-计划书-r4.md（代码库核实版）+
  阶段 0 执行规划

### Changed
- `.gitignore`：`web/site/`、`evals/human_judging_answers.json`

## [0.5.1] - 2026-10-07

### Changed
- **zhuifang 包 0.1.0 → 0.2.0（四路联网核查 + 仲裁子代理终审）**：
  - 艾莫号前身**定稿格里芬资产说**（2064 穆罗梅兹行动已作格里芬移动指挥车）；
    "医疗舰说"（环太平洋救援组织 / 盖亚扩散 / 遗迹战争）经三源核查判定为
    百科不实内容，明令不得使用
  - 存在性清账：黛烟存在（季风乐队，QBZ-95 烙印）【强】；弗必安存在（坍塌辐射
    计量单位，黑区 >10000 / 白区 0）【中】；"委托人"仅为第三章登场角色称谓，
    禁止当组织名使用【弱】
  - **OOC 红线定稿（附证据强度）**：闪电 / 纳美西丝 / 克罗丽科 / 维普蕾 / 寇尔芙
    五人。关键发现：原作寇尔芙为"人家"自称 + 夹子音撒娇腔 + 讨好型 + 对瓦良格帮
    灭队之仇——与灰区回声既有写法严重 OOC，仲裁裁定**渐进迁移**：第 1—11 章
    不改稿，第 12 章起引入原作声线，迁移说明入项目 bible/characters.md
  - 漂移词反哺 ban：抗辐剂 / 信用点 / 污染区字母分区；conventions 增晶条计价纪律

### Data
- **canon 盲测扩样 n=4 → n=10**（canon_blind_v050）：canon 臂 **8 胜 2 负**
  （两负均中置信，八胜含七局高置信）；场景覆盖委托/侦察/帮派/生骸/日常/检查站。
  判官噪声两例入档（黑区、非军事力量管理局被误判为非原作——判官裁词应以包内
  facts 为准，v0.5.2 可给判官发事实卡）

### Added
- 灰区回声第 12 章《失效坐标》：新红线端到端验证（寇尔芙"人家"声线迁移首章、
  弗必安读数、晶条记账）；consistency-check 增量模式首跑——canon/names/timeline
  三脚本全绿 + 模型审查（P0 零、P1×2、P2×6，全部按报告修复后复检通过）

测试：100 项全绿（无新增用例，canon 分支回归通过）

## [0.5.0] - 2026-10-06

### Added
- **canon 层（二创约束引导，计划书 v0.5）**：新增 `canonpacks/` 包类型，与风格包
  对称——card / facts / conventions / terms.json（must/allow/ban 三级术语表，
  错译进 wrong 变体）/ characters.json（roster+tier+OOC 红线+OC 接口规则）/
  sources.md（URL+抓取日期审计）。首包 `canonpacks/zhuifang`《少女前线2：追放》
  （闪电小队 roster、2074 时代锚点、黑→红→黄→净化区→绿→白污染分级）
- **canon_terms_check.py**：must 覆盖（volume/chapter 两档阈值）+ ban/错写
  0 容忍 + 千字浓度 advisory（防硬塞指标）；7 项行为测试
- **validate/export/pin 的 canon 分支**：pack.json.kind=="canon" 分派；canon 校验
  （必备文件、cast_policy、ban 必须给理由、core 角色红线缺失警告、sources 审计、
  引文 >100 字违反摘要纪律、注入启发式复用）；canon 单文件导出
  （CANONPACK-SINGLE-FILE）；pin 同步写 canon-terms.json 快照（_pinned_from 记版本）
- **技能（双副本同步）**：style-setup 第 3.5 步"原作锚定"（二创分支：联网双源
  核对 → canon 档案逐节校订 → validate → pin → outline 双轨声明"事件原创、
  设定恪守"）；style-apply 上下文协议第 6 条（canon 层必载）、拍子表"原作锚点"行、
  验收加 canon 检查、自检表加"canon 检查"项；consistency-check 第一层
  canon_terms_check、第二层"原作保真"（OOC 以 canon 人物卡优先、facts 红线 P1、
  OC 接口核查）；stylepack list/pin 支持 canon 包
- schemas/canonpack.schema.json

### Fixed
- 灰区回声 P0（案例修复，reviews/p0-验收报告.md）：埃尔莫→艾莫号错译 47 处清零、
  "沙暴"→"坍塌风暴"46 处规范；第 8—10 章连续性接缝修复（旧人形下落三版统一、
  存储盒"只够播放一次"与第 9 章长录音矛盾、文件【她们】穿越引用、第 10 章开头
  重演返程段删除）

### Data
- canon 盲测 canon_blind_v050（项目 style/calibration.json）：n=4，canon 臂
  3 胜 1 负（负局中置信，胜局均高置信）。发现：无包臂凭模型先验也能产出
  琼玖 / 佩里缇亚 / ELID——canon 层的边际优势在**术语体系化与委托-结算经济
  脚手架**，与计划书 v0.5 论点一致；n=4 只记趋势

测试：95 → 100（canon_check 7 项 + validate/export canon 5 项）

## [0.4.2] - 2026-10-06

### Added
- **borrow_check.py 借句初筛**（遗留 #8 机器初筛层）：草稿 vs exemplars
  引文 ≥12 字逐字重叠检测（规范化后滑窗 + 最大重叠延展），exit 0/1 可作
  交付自检可选门；**初筛不是终判**，化用/骨架雷同仍靠盲测与人工判读兜底；
  6 项行为测试 + GBK 全入口冒烟纳入（总测试 82→88）
- style-apply 交付自检增"借句初筛"项（双副本同步）
- **迷你辨认盲测**（calibration.json `recognition_v043`）：profile r2 后
  2 回合，辨认 2/2、乱真归属 2/2——r3 后 zhuziqing 辨认分歧的有利数据点
  （n=2 只记趋势）
- evals/cases.md Case K

### Changed
- **zhuziqing 散文层与思想层同步重蒸馏（遗留 #1 闭环）**：profile.md r2
  （10 篇逐条重裁决、每条指认篇目）——对话改按关系分层（推翻 4 篇时代
  "对话极少"）、议论改三通道条件项（对齐 thought r3）、结构补纪游列叙/
  忆人三叠/自省忏悔三构型、情感谱扩、"你"呼告升高频；exemplars 8→12 条
  （童语成串/对答窘态/幻灭收束/实事托住直抒收束）；lexicon（叠词/纪游词
  扩充、议论条改条件项）、limits（语料描述改 10 篇四路、分层对话入"可
  模仿"）、card 同步；pack.json 0.4.3。指纹不动（已 n=10，essay LOO 1.486）

## [0.4.1] - 2026-10-05

### Added
- **三仪交叉终审**（用户授权子代理终审）：自由辨认（不点名作者）+ 判据合规
  盲评 + 乱真归属（真迹锚），加 r2 对抗审查——全部由互不共享上下文的子代理
  执行，结果入 calibration.json `final_verdict_v040`
- 结论：**luxun 三仪俱证**（辨认 6/6 vs 3/6；合规 6×18/18 vs 均值 13.67；
  归属 6/6 vs 2/6 同手）——思想层带包增益成立，且带包方差为零（每篇都保持
  在判据内）；**zhuziqing 分歧如实记录**（辨认反向/归属混合/合规无区分）

### Changed
- **thought.md r3**（对抗终审 3 条改判采纳）：社会冲突回条件项、虚构禁写
  限定散文体、"居高临下"改"禁居高临下而无自省"、议论三条件改三选一、
  反讽三分、体罚/刑罚拆分、低频姿态条目标注"不必强求"、师友作镜改
  "引他人评价自照"；profile.md 同步列为遗留待办

## [0.4.0] - 2026-10-05

### Added
- **zhuziqing 语料 4→10 篇（Case G 收官）**：桨声灯影里的秦淮河 / 绿 /
  白种人——上帝的骄子 / 儿女 / 冬天 / 南京，全部来自中文维基文库（当日
  可达性恢复；MediaWiki API wikitext + opencc t2s 本地简体化 + 繁体标记字
  断言 + 语境核查），逐篇 provenance
- downloads/_raw/fetch_zhuziqing_wikisource.py：抓取/清洗/转换管线（可复跑）
- thought.md r2 重蒸馏（zhuziqing）：10 篇精读逐条裁决 4 篇时代的结论——
  **2 条弱禁用被推翻**（社会冲突/多人对话强冲突）、2 条降条件项、1 条转正
  硬规则（虚构人物禁写）、新增 3 条；motif 词表 12 词重算（旧表 5 词系
  4 篇选样假象，跌破剔除线删除）
- **思想盲测续跑**：4 回合（luxun 2 + zhuziqing 2）——带包 3/4，累计 6/8；
  zhuziqing r2 两轮全胜，判官获胜理由即 r2 判据（thought_blind_v040）

### Changed
- **跨包归因仪器修正（重要）**：复测发现旧口径（各自包 top-150 字符集
  Delta）随基准选择**翻转方向**（评测集 luxun 0/5、大语料又 62/62，p 全不
  显著）——v0.2.8 的 7/9 与 zhuziqing n=4 的 2/4 均属仪器伪影，如实撤销；
  改用**度量空间 + 全局基准**（Case J 同源机器）：**13/15（0.867），
  p=0.004，zhuziqing 侧 9/10**——"补齐后回 ≥0.9"的预测在正确仪器上兑现。
  test_cross_validation 重写（test_delta.py），evals Case G 收官补记
- zhuziqing essay 层留一线 2.112 → 1.486（n=10）；pack.json 0.4.1；
  82→84 项测试全绿

## [0.3.1] - 2026-09-30

### Added
- **registers_dryrun.py**：调子分区统计真实性检验 CLI——层间归因率 + 置换检验
  p 值 + 候选分法（k=现状 / k-1 合并）对照表；**全局基准纪律写死在代码里**
- splib 归因/置换机器：`parse_registers_md`（含标定行）、`match_labels_to_files`、
  `build_register_layers`、`build_metric_matrix`（12 维句法度量向量）、
  `attribution_detail / permutation_test`（固定种子可复现；预计算矩阵让
  1000 次置换秒级可跑）
- `tests/test_stratum.py`：阳性对照（合成双维可分语料必须显著）、阴性对照
  （随机标签必须不显著）、种子确定性、标定行解析、dry-run CLI 冒烟

### Changed
- **R1 检查点 1 裁决（负结果）**：层间归因 + 置换检验（预注册判据，全局基准）
  全轴不显著（情感轴 p=0.336 / 节奏轴 p=0.278）——六分区全部标"仅路由"，
  指纹分区不落地（build_delta --registers / fp_check --stratum 按计划不实现）；
  registers.md r2 落标定状态，示范段路由（R0）不受影响
- 仪器可信度：阳性对照（文体标签，度量空间）归因 0.871 / p=0.0；阴性对照
  （随机标签）p=0.51
- 方法论产出：**基准纪律**——逐轴自建 z-score 基准曾给出 p=0.01 的假显著，
  全局基准下消失；显著性检验的基准选择必须先于看数固定
- evals 新增 Case J（R1 负结果全记录）

## [0.3.0] - 2026-09-30

### Added
- **思想层 thought.md（v0.3 主体）**：可选包文件，六节骨架——选题地平线 /
  立意动作 / 观察清单 / 意象系统 / 价值姿态 / 禁区。蒸馏对象是**思路的动作**
  （选题偏好、立意招式、观察习惯、可执行姿态指令），不是思想的内容；全部
  条目须指认 exemplars 编号或语料篇目，不能溯源的删除
- **luxun / zhuziqing thought.md 定稿**（用户逐节校订通过）：luxun 立意动作
  10 招 + 价值姿态 9 条（全部指令化，如"叙述者后退半步，让事实并置，禁直接
  评判"）+ 禁区 9 条；zhuziqing 各节**置信度逐节标注**（语料仅 4 篇，
  回避 / 禁区为弱禁用）
- **motif_count.py**：验证 thought.md 提案词表的语料频率（递归收集 *.txt/*.md），
  低于剔除线自动剔除，--write 写回 motif_stats 节 + pack.json 版本联动——
  提案是模型的，数字是脚本的（防幻觉意象）
- **fp_check --thought**：输出 motif 密度对照——**advisory，不进判定、
  不影响退出码**（测试锁定）；思想特征全部可 Goodhart（意象可堆砌），
  故永不升级为通过性指标
- **format_version 0.1 → 0.2**：schema 增 thought / registers 可选能力标记，
  可选文件缺失时全流程照常（向后兼容）
- 四技能更新（双副本）：style-analyze 思想四问（一次精读两份产出）、
  style-apply 两级共创（立意确认 → 拍子表）+ **交付声明制**、style-critique
  思想维度 + 贴标签检测、style-calibrate 思想盲测（同题材两问，判读问题 =
  "哪篇更像这个作者在思考"）
- tests/test_thought.py（13 项）+ TestGenericAuthorPipeline.test_thought_layer_cli
  （任意作者思想步端到端）；evals Case I

### Changed
- **motif 剔除线按语料规模校正**：1.5/千字为小语料防幻觉线；luxun 20.8 万字
  语料实测仅剩 3 词（月/夜/死全被杀）→ 校正为 0.5/千字（防幻觉功能不变：
  ≥0.5 即 ≥104 次出现），"头"因方位词复合流量污染计数手动剔除；
  luxun 词表 12 词、zhuziqing 10 词（全部过线）
- pack.json：luxun 0.3.0→0.4.0、zhuziqing 0.2.0→0.3.0（thought 能力声明）
- validate 对无 thought.md 的包给 1 条提示（沿计划 §6.1：0 警告升级为 1 条提示）

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
- 文档面向通用 agent 宿主表述：README / usage 不再绑定特定宿主名称，
  宿主专属安装信息集中到 docs/adapters/（保留）；修复 README 指向仓库外
  设计文档的死链；路线图更新至 0.2.9 现状、技能计数修正为 12

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
