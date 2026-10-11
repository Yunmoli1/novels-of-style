# -*- coding: utf-8 -*-
"""creation：创作环提示词与状态机辅助（v0.6.0）。

蓝本 = style-apply 两级共创（照搬不发明）：
  第一级·立意确认：依 thought.md 提 2–3 个立意方向（题材角度+拟用立意动作
  【引条目】+价值姿态落点）
  第二级·拍子表确认：开场承接/场景/结尾钩子，每拍一行（写什么、出现谁、
  给读者什么）+ 调子声明（无 registers 写"不指定"）+ 二创原作锚点
生成严格按拍子推进，不新增情节线；收尾检查为思想层硬性条目的模型化实现。
"""
from __future__ import annotations

import json
import re


def _repair_truncated(text: str) -> str:
    """best-effort 修复被 max_tokens 截断的 JSON：补引号、去尾逗号、闭合括号。"""
    stack: list[str] = []
    in_str = esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
    out = text + ('"' if in_str else "")
    out = re.sub(r"[,:\s]+$", "", out)
    out = re.sub(r",\s*(?=[}\]]|$)", "", out)
    for ch in reversed(stack):
        out += "}" if ch == "{" else "]"
    json.loads(out)  # 仍失败则抛给调用方
    return out


def extract_json(text: str) -> dict:
    """从模型回复中提取第一个 JSON 对象（容忍围栏/废话/max_tokens 截断——
    截断时按括号栈 best-effort 补齐，真实场景（立意 2–3 项被 1200 token
    截断）实测可救回前几项）。"""
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    if start < 0:
        raise ValueError("模型回复中未找到 JSON")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    try:
        return json.loads(_repair_truncated(text[start:]))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"模型回复中 JSON 未闭合且无法修复（{exc}）") from exc


SYSTEM = ("你是严格的网文章节共创助手。所有输出必须是可解析的 JSON 或纯正文，"
          "不要寒暄、不要解释流程。风格约束来自装配上下文中的风格包档案，"
          "必须严格遵守其中的 profile/thought/lexicon/limits。")


def outline_prompt(chapter_no: int, title: str, keywords: list[str],
                   context_blocks: list[str], user_notes: str) -> str:
    return f"""请为第 {chapter_no} 章（题：《{title}》）提出 2–3 个立意方向。

要求（第一级·立意确认）：每个方向 = 题材角度 + 拟用立意动作（必须引用风格包
thought.md「立意动作」中的条目编号与名称）+ 价值姿态落点。立意要服务本章
关键词：{'、'.join(keywords) or '（无）'}。{('用户补充：' + user_notes) if user_notes else ''}

只输出 JSON：
{{"options": [{{"title": "方向名", "angle": "题材角度", "action": "立意动作（引条目）", "stance": "价值姿态落点"}}], "recommended": 0}}

——以下是装配上下文——
{chr(10).join(context_blocks)}"""


def beats_prompt(chapter_no: int, title: str, chosen: dict,
                 context_blocks: list[str], canon_note: str) -> str:
    return f"""第 {chapter_no} 章（题：《{title}》）已选定立意：
方向：{chosen.get('title', '')}
角度：{chosen.get('angle', '')}
立意动作：{chosen.get('action', '')}
价值姿态：{chosen.get('stance', '')}

请产出本章拍子表（第二级·拍子表确认）：开场承接 / 场景 1 / 场景 2 / 结尾钩子
（可 4–8 拍），每拍一行，写明【写什么、出现谁、给读者什么】。
并附一行"调子声明"（无调子分区写"不指定"）与一行"原作锚点"（本章用到的
术语/人物/事实红线；非二创写"无"）。{canon_note}

只输出 JSON：
{{"beats": [{{"no": 1, "beat": "……"}}], "tone_note": "……", "canon_anchor": "……"}}

——以下是装配上下文——
{chr(10).join(context_blocks)}"""


def reroll_beat_prompt(chapter_no: int, title: str, chosen: dict,
                       beats: list[dict], index: int,
                       context_blocks: list[str]) -> str:
    neighbors = "\n".join(f"拍{b['no']}：{b['beat']}" for b in beats
                          if abs((b.get("no") or 0) - index) <= 1)
    return f"""第 {chapter_no} 章（题：《{title}》）立意：{chosen.get('title', '')}——{chosen.get('angle', '')}。
现有拍子表：
{neighbors}

请重掷第 {index} 拍：与相邻拍自然衔接、承担相同的叙事职责（承接/推进/钩子），
但给出明显不同的走向。

只输出 JSON：{{"no": {index}, "beat": "……"}}

——以下是装配上下文——
{chr(10).join(context_blocks)}"""


def prose_prompt(chapter_no: int, title: str, chosen: dict, beats: list[dict],
                 tone_note: str, canon_anchor: str,
                 context_blocks: list[str], target_chars: int) -> str:
    beat_lines = "\n".join(f"拍{b.get('no')}：{b.get('beat')}" for b in beats)
    return f"""请写第 {chapter_no} 章正文（题：《{title}》）。

立意：{chosen.get('title', '')}——{chosen.get('angle', '')}（动作：{chosen.get('action', '')}；姿态：{chosen.get('stance', '')}）
拍子表（严格按此推进，不新增情节线）：
{beat_lines}
调子声明：{tone_note or '不指定'}｜原作锚点：{canon_anchor or '无'}

硬性要求：
- 严格使用装配上下文中风格包档案的语言纪律：profile 的句式节奏与对话分层、
  lexicon 的签名词与禁用清单、limits 的分寸警告、thought 的禁区（尤其收尾）。
- 篇幅约 {target_chars} 字。
- 收尾执行思想层收尾检查：不给人物立抒情碑、不安慰读者、不点题升华；
  物化收束或实事托住的直抒才合法。

只输出正文本身（不要标题、不要解释）。


——以下是装配上下文——
{chr(10).join(context_blocks)}"""


def ending_check_prompt(title: str, draft_tail: str) -> str:
    return f"""请对《{title}》的结尾段做思想层收尾检查（硬性条目）：
1. 是否在给人物立抒情碑（用意象为角色定格、树碑立传式收束）？
2. 是否在安慰读者（给温暖保证、给廉价比 sentiment）？
3. 是否在点题升华（把主题说破）？

只输出 JSON：{{"violation": true/false, "reason": "一句话依据（引用原文）"}}

——结尾段——
{draft_tail}"""
