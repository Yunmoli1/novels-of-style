# -*- coding: utf-8 -*-
"""model_client：OpenAI 兼容端点直连客户端（httpx，不引重型 SDK；r4 §五）。

安全纪律（r4 红线 5）：api_key 只经内存请求头，不落日志/异常文本/返回值——
所有异常先经 _sanitize 剥离 key 字样。
"""
from __future__ import annotations

import json

import httpx


def _sanitize(text: str, api_key: str | None) -> str:
    if api_key:
        text = text.replace(api_key, "***")
    return text


def _candidates(base_url: str, path: str) -> list[str]:
    """base 带 / 不带 /v1 都能用的自动回退（DeepSeek 等官方即两种写法）。"""
    base = base_url.rstrip("/")
    urls = [base + path]
    if not base.endswith("/v1"):
        urls.append(base + "/v1" + path)
    return urls


def chat(base_url: str, api_key: str | None, model: str, messages: list[dict],
         temperature: float = 0.8, max_tokens: int = 3500,
         timeout: float = 240.0) -> dict:
    """一次对话调用。空稿/截断防护（v0.6.2/v0.6.5）：思考型模型可能把 max_tokens
    全花在内部推理上（content 空），或正文写到一半被截断（finish=length）——
    两种情况都自动加倍预算重试（最多 3 次，取最长结果），仍空则报可行动的错
    （换非思考模型/关思考/调大 max_tokens），绝不把空稿放进创作环；截断结果
    原样返回但带 finish_reason=length 供前端警告。
    usage 记账含重试消耗（真实花费），并带 finish_reason/retries 诊断字段。
    """
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    last_err: Exception | None = None
    url: str | None = None
    data: dict | None = None
    text, finish = "", None
    best, best_finish = "", None
    acc = {"prompt_tokens": 0, "completion_tokens": 0}
    retries = 0
    budget = max_tokens
    for attempt in range(4):  # 首次 + 最多 3 次加倍重试
        payload["max_tokens"] = budget
        candidates = [url] if url else _candidates(base_url, "/chat/completions")
        data = None
        for cand in candidates:
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(cand, json=payload, headers=headers)
                    if resp.status_code == 404 and cand != candidates[-1]:
                        last_err = httpx.HTTPStatusError("404", request=resp.request,
                                                         response=resp)
                        continue  # /v1 回退
                    resp.raise_for_status()
                    data = resp.json()
                    url = cand
                    break
            except httpx.HTTPStatusError as exc:
                body = _sanitize(exc.response.text[:300], api_key)
                raise ValueError(f"模型端点返回 {exc.response.status_code}：{body}") from exc
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                last_err = exc
        if data is None:
            raise ValueError(f"模型调用失败：{_sanitize(str(last_err), api_key)}")
        choices = data.get("choices") or []
        if not choices:
            raise ValueError(f"模型响应缺少 choices：{_sanitize(str(data)[:200], api_key)}")
        msg = choices[0].get("message") or {}
        finish = choices[0].get("finish_reason")
        has_reasoning = bool(msg.get("reasoning_content"))
        usage = data.get("usage") or {}
        acc["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
        acc["completion_tokens"] += int(usage.get("completion_tokens") or 0)
        text = msg.get("content") or ""
        if len(text) > len(best):  # 阶梯越加越大，取最长结果
            best, best_finish = text, finish
        if text.strip() and finish != "length":
            break  # 完整正文（截断 finish=length 也重试——v0.6.5：修订缩水根因）
        if attempt == 3:
            break
        retries += 1
        budget *= 2
    text, finish = best, best_finish
    if not text.strip():
        hint = ("响应含思考内容（reasoning_content）——思考型模型把 token 花在推理上；"
                if has_reasoning else "")
        raise ValueError(
            f"模型返回空正文（finish_reason={finish}，已自动加倍预算重试 "
            f"{retries} 次至 {budget} tokens 仍为空）。{hint}"
            "对策：换非思考模型、在供应商侧关闭思考模式、或调大「正文 max_tokens」")
    return {"text": text, **acc, "model": data.get("model") or model,
            "finish_reason": finish, "retries": retries}


_CPT = 0.75  # 1 字 ≈ 0.75 token（与 assemble.CHARS_PER_TOKEN 同口径）


def chat_stream(base_url: str, api_key: str | None, model: str, messages: list[dict],
                temperature: float = 0.8, max_tokens: int = 3500,
                timeout: float = 240.0):
    """流式对话（SSE）。逐事件产出：
      {"type": "delta", "text": 增量正文}
      {"type": "reasoning", "text": 思考增量}  # 仅供"思考中"状态展示，不入正文
      {"type": "done", "usage": {...}, "finish_reason": ...}
    供应商不认 stream_options 时自动裸流重试；usage 缺失按字数粗估（estimated）。
    读超时按 chunk 间隔计——长文生成不再被"整段等待"掐断（v0.6.4）。
    """
    base = dict(model=model, messages=messages, temperature=temperature,
                max_tokens=max_tokens, stream=True)
    variants = [ {**base, "stream_options": {"include_usage": True}}, dict(base)]
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    text_parts: list[str] = []
    finish = None
    usage = None
    last_err: Exception | None = None
    for cand in _candidates(base_url, "/chat/completions"):
        for payload in variants:
            opened = False
            try:
                with httpx.Client(timeout=timeout) as client:
                    with client.stream("POST", cand, json=payload,
                                       headers=headers) as resp:
                        if resp.status_code == 404:
                            last_err = httpx.HTTPStatusError(
                                "404", request=resp.request, response=resp)
                            break  # 下一候选（/v1 回退）
                        resp.raise_for_status()
                        opened = True
                        for line in resp.iter_lines():
                            if not line.startswith("data:"):
                                continue
                            data = line[5:].strip()
                            if data == "[DONE]":
                                break
                            obj = json.loads(data)
                            if obj.get("usage"):
                                usage = obj["usage"]
                            choices = obj.get("choices") or []
                            if not choices:
                                continue
                            delta = choices[0].get("delta") or {}
                            if delta.get("reasoning_content"):
                                yield {"type": "reasoning",
                                       "text": delta["reasoning_content"]}
                            if delta.get("content"):
                                text_parts.append(delta["content"])
                                yield {"type": "delta", "text": delta["content"]}
                            if choices[0].get("finish_reason"):
                                finish = choices[0]["finish_reason"]
                u = usage or {}
                got = {"prompt_tokens": int(u.get("prompt_tokens") or 0),
                       "completion_tokens": int(u.get("completion_tokens") or 0)}
                if not got["prompt_tokens"] and not got["completion_tokens"]:
                    est_in = sum(len(m.get("content") or "") for m in messages)
                    got = {"prompt_tokens": int(est_in * _CPT),
                           "completion_tokens":
                               int(len("".join(text_parts)) * _CPT),
                           "estimated": True}
                yield {"type": "done", "usage": got, "finish_reason": finish}
                return
            except httpx.HTTPStatusError as exc:
                if not opened and exc.response.status_code == 400 \
                        and "stream_options" in payload:
                    last_err = exc
                    continue  # 裸流兜底
                try:
                    body_txt = exc.response.text[:300]
                except Exception:
                    body_txt = ""
                raise ValueError(f"模型端点返回 {exc.response.status_code}："
                                 f"{_sanitize(body_txt, api_key)}") from exc
            except (httpx.HTTPError, json.JSONDecodeError, KeyError,
                    TypeError) as exc:
                last_err = exc
                break  # 网络层失败 → 下一候选
    raise ValueError(f"模型流式调用失败：{_sanitize(str(last_err), api_key)}")


def list_models(base_url: str, api_key: str | None, timeout: float = 30.0) -> list[str]:
    """测试连接：GET /models（/v1 自动回退）。异常文本同样剥 key。"""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    last: Exception | None = None
    for url in _candidates(base_url, "/models"):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            items = data.get("data") if isinstance(data, dict) else data
            ids = sorted({m.get("id") for m in (items or [])
                          if isinstance(m, dict) and m.get("id")})
            if ids:
                return ids
            last = ValueError(f"端点未返回模型列表（{url}）")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                last = exc
                continue  # /v1 回退
            raise ValueError(f"端点返回 {exc.response.status_code}："
                             f"{_sanitize(exc.response.text[:200], api_key)}") from exc
        except httpx.HTTPError as exc:
            last = exc
    raise ValueError(f"连接失败：{_sanitize(str(last), api_key)}")
