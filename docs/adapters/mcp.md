# MCP 记忆层适配（v0.2）

StylePack MCP server 把"故事状态机 + 全文检索 + 指纹验收"以标准 MCP 工具暴露给
任何支持 MCP 的宿主。stdlib 手写 JSON-RPC（零依赖），`--project` 指向写作项目目录。

## 启动命令（各宿主通用）

```
python <stylepack仓库>/server/mcp_server.py --project <写作项目目录>
```

## 工具一览（10 个，单次返回 ≤ 2KB，自动记账）

| 工具 | 用途 |
|---|---|
| `story.sync` | bible/corpus 文件 → 状态机重建索引（初始化或 bible 变更后） |
| `story.search` | 全文检索（返回路径+片段，绝不返回全文） |
| `story.character` | 人物卡：设定摘要 + tier + 最近 3 条状态 |
| `story.recap` | 前情提要：最近 n 章摘要 + 未回收伏笔 + pending 滞留提醒 |
| `story.foreshadow` | 伏笔账本查询 |
| `story.propose_delta` | 写完一章登记状态变更（入隔离区） |
| `story.merge_delta` | 分级合并（低风险自动，中/高风险需 force） |
| `story.cost_forecast` | 剩余成本预测 |
| `stylepack.info` | 风格包清单查询 |
| `fp.check` | 指纹验收（阈值 + Delta 距离） |

## ZCode

工作区级（团队共享，随仓库走）：`<写作项目>/.zcode/config.json`

```json
{
  "mcp": {
    "servers": {
      "stylepack": {
        "command": "python",
        "args": ["<stylepack仓库路径>/server/mcp_server.py", "--project", "<写作项目目录>"]
      }
    }
  }
}
```

用户级（所有工作区可用）：`~/.zcode/cli/config.json` 同结构。保存后重开会话自动连接
（Settings → MCP 可查看状态）。

## Claude Code

项目根目录 `.mcp.json`：

```json
{
  "mcpServers": {
    "stylepack": {
      "command": "python",
      "args": ["<stylepack仓库路径>/server/mcp_server.py", "--project", "."]
    }
  }
}
```

## Cursor

`~/.cursor/mcp.json` 或项目 `.cursor/mcp.json`，结构与 Claude Code 相同
（`mcpServers` 键）。

## 无 MCP 宿主

全部能力有 CLI 等价物（同一实现、两个壳）：

```bash
python scripts/story.py sync          # 其余子命令：search/character/recap/
                                      # foreshadow/propose/merge/aging
python scripts/fp_check.py <包> <稿>  # 含 --delta
```

## 说明

- 状态机数据库在 `<项目>/style/memory.db`（已 gitignore，可随时删除重建——文件才是权威源）
- 首次使用先调 `story.sync`（或 `story.py sync`）
- 修改 bible 后记得再次 sync；写作流程产出的 delta 走 propose → merge 两段式
- 每次 MCP 调用自动写入 `<项目>/style/cost.jsonl`，`cost.py report` / `forecast` 出账
