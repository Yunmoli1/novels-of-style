## 改动说明

（做什么、为什么；关联 issue #）

## 版权纪律自查（风格包相关 PR 必填）

- ☐ 未提交任何语料全文（含"参考/附录"形式）
- ☐ exemplars 单条引文 ≤ 200 字（`validate_pack` 会拦）
- ☐ 在保护期作者只有短引 + 批注
- ☐ pack.json 如实记录 corpus 规模 / 采样 / 置信度

## 自检三连（全绿才请求 review）

```bash
python scripts/validate_pack.py stylepacks/<包名>   # 风格包 PR
python -m unittest discover -s tests -v              # 全部 PR
```

- ☐ 全部通过（贴末尾几行输出）
