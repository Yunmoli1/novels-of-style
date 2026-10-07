# StylePack 本地工作台（阶段 0）

一台引擎，三张脸：CLI / MCP / Web 共用同一套脚本与包文件。本目录是
**本地优先**的网页入口（r4 红线：仅 127.0.0.1、零遥测、答案与全文不出库）。

## 使用（双击即可，无需命令行）

- Windows：双击仓库根的 **启动工作台.bat** —— 自动构建站点、启动本机服务并打开浏览器
- 其他平台 / 手动：`python web/launch.py`
- 只想重新生成静态站点：`python web/build_site.py`（产物 `web/site/`，可离线双击打开）

## 页面

| 页面 | 说明 |
|---|---|
| `/judging/` | 盲测人工判读台（8 回合）：甲/乙/都不像 + 置信 + 理由；进度存本机 localStorage；"导出判读结果"下载 JSON |
| `/packs/<名>/` | 包全档渲染 + 测量可视化（指标容差表 / LOO 留一线 / motif SVG） |

## 判读计分

1. 判读台完成 8 回合 → 导出 `human_judging_results.json`
2. `python scripts/score_human_judging.py human_judging_results.json`
   （对照本机 `evals/human_judging_answers.json`——该文件**不入 git**，
   由 `python scripts/migrate_human_judging.py` 从工作区根的判读包 md 生成）
3. 输出两个一致率：辨认带包臂命中率 / 与子代理判官一致率（同源偏差度量），
   结果按 style-calibrate 协议回填 calibration.json

## 红线（tests/test_web.py 锁定）

- 服务只绑 127.0.0.1；语料全文与答案卷永不进入站点产物；
- 判读页不含答案；包数据写权仍归脚本（本阶段站点纯只读）；
- 零依赖（stdlib only），离线可开（`web/site/index.html` 直接双击亦可）。
