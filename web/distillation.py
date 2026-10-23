# -*- coding: utf-8 -*-
"""distillation：蒸馏台阶段 B——采样与精读的提示词与选样算法。

纪律（style-analyze 技能 2/2.1 节网页化）：
- 精读只回答问题，严禁全文复述；范例引文到草案阶段才定点取；
- 每个判断尽量溯源到具体篇目，不可溯源的条目在草案阶段删除；
- ≤100k 字单次注入；超出自动 map-reduce（块摘要 ≤800 字，主汇总只读摘要）。
- 提案是模型的，数字是脚本的（motif/指纹仍由脚本验证）。
"""
from __future__ import annotations

import json

READ_SINGLE_MAX = 100_000  # 字：单次精读上限，超出走 map-reduce
CHUNK_CHARS = 60_000       # map 块的字数预算
READ_MAX_TOKENS = 2600     # 精读 JSON 输出上限
OBS_MAX_TOKENS = 1200      # 块观察输出上限
READ_TEMPERATURE = 0.3     # 分析任务低温

SYSTEM_READ = ("你是严谨的文风分析师。只依据给出的语料文本作答，每个判断尽量能"
               "指认到具体篇目；不做语料中无依据的断言。所有输出必须是可解析 JSON，"
               "不要寒暄、不要解释流程。")

_READ_SCHEMA = ('{{"视角": "", "节奏": "", "对话": "", "场景": "", "情绪": "", '
                '"手法": [{{"手法": "", "依据": ""}}], '
                '"选择": "", "立意动作": [{{"动作": "", "依据": ""}}], '
                '"细节": "", "意象族": ["词1"]}}')


def _body(samples: list[tuple[str, str]]) -> str:
    return "\n\n".join(f"【{name}】\n{text}" for name, text in samples)


def read_prompt(samples: list[tuple[str, str]]) -> str:
    """单次精读（≤100k 字）：六问题（写法层）+ 思想四问（选择层）。"""
    return f"""请精读以下 {len(samples)} 篇语料（同一位作者），回答十个问题。

六问题（写法层）：
1. 叙事视角与人称
2. 句子如何制造节奏（长短/停顿/排比等具体手段）
3. 对话如何区分人物（措辞/句式/口癖）
4. 场景如何转换
5. 情绪如何外化（不直呼情绪时的载体）
6. 标志性手法清单（逐条给依据篇目）

思想四问（选择层）：
A. 作者选择写什么、拒绝写什么
B. 从题材到角度的招式（立意动作，逐条给动作名 + 依据篇目）
C. 作者的眼睛反复落在哪几类细节上
D. 反复出现的意象族（提案词表：文本中字面反复出现的词，10–30 个）

只输出 JSON：
{_READ_SCHEMA}

——语料——
{_body(samples)}"""


def chunk_prompt(samples: list[tuple[str, str]]) -> str:
    """map 块观察（≤800 字五项，只看自己那块）。"""
    return f"""以下是某作者语料中的一块（{len(samples)} 篇）。只依据文本输出不超过 800 字的观察 JSON：
{{"视角": "", "节奏": "", "对话": "", "场景": "", "手法": ["……"]}}

——文本——
{_body(samples)}"""


def reduce_prompt(observations: list[dict]) -> str:
    """reduce 主汇总：只读块摘要融合为最终答案；无据可提的思想四问置空，不得编造。"""
    obs = json.dumps(observations, ensure_ascii=False, indent=1)
    return f"""以下是对同一位作者语料分块精读后的 {len(observations)} 份观察摘要。
请融合为最终答案（思想四问若摘要无据可提，相应字段置空字符串/空数组，不得编造）。

只输出 JSON：
{_READ_SCHEMA}

——分块观察——
{obs}"""


def plan_sampling(rows: list[dict]) -> list[dict]:
    """自动选样：首/中/尾各 1–2 + 对话密集 1 + 叙述密集 1（去重，上限 8）。
    rows 须已按语料顺序排列，元素含 file/chars/dialogue。"""
    order = list(rows)
    n = len(order)
    if n == 0:
        return []
    picks: dict[str, list[str]] = {}

    def take(idx: int, reason: str) -> None:
        r = order[max(0, min(n - 1, idx))]
        if reason not in picks.setdefault(r["file"], []):
            picks[r["file"]].append(reason)

    take(0, "开头")
    if n > 1:
        take(1, "开头")
    if n > 6:
        take((n - 1) // 2, "中段")
        take((n - 1) // 2 + 1, "中段")
    elif n > 2:
        take(n // 2, "中段")
    take(n - 1, "结尾")
    if n > 2:
        take(n - 2, "结尾")
    with_d = [r for r in order if isinstance(r.get("dialogue"), (int, float))]
    if with_d:
        dense = max(with_d, key=lambda r: r["dialogue"])
        sparse = min(with_d, key=lambda r: r["dialogue"])
        take(order.index(dense), "对话密集")
        take(order.index(sparse), "叙述密集")
    out = [{**r, "reason": "、".join(picks[r["file"]])}
           for r in order if r["file"] in picks]
    return out[:8]


def chunk_files(samples: list[tuple[str, str]],
                chunk_chars: int = CHUNK_CHARS) -> list[list[tuple[str, str]]]:
    """按字数预算切 map 块（保篇完整，不切半篇）。"""
    chunks: list[list[tuple[str, str]]] = []
    cur: list[tuple[str, str]] = []
    cur_chars = 0
    for item in samples:
        cur.append(item)
        cur_chars += len(item[1])
        if cur_chars >= chunk_chars:
            chunks.append(cur)
            cur, cur_chars = [], 0
    if cur:
        chunks.append(cur)
    return chunks
