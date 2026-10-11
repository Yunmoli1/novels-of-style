# -*- coding: utf-8 -*-
"""model_client：OpenAI 兼容端点直连客户端（httpx，不引重型 SDK；r4 §五）。

安全纪律（r4 红线 5）：api_key 只经内存请求头，不落日志/异常文本/返回值——
所有异常先经 _sanitize 剥离 key 字样。
"""
from __future__ import annotations

import httpx


def _sanitize(text: str, api_key: str | None) -> str:
    if api_key:
        text = text.replace(api_key, "***")
    return text


def chat(base_url: str, api_key: str | None, model: str, messages: list[dict],
         temperature: float = 0.8, max_tokens: int = 3500,
         timeout: float = 240.0) -> dict:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        body = _sanitize(exc.response.text[:300], api_key)
        raise ValueError(f"模型端点返回 {exc.response.status_code}：{body}") from exc
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise ValueError(f"模型调用失败：{_sanitize(str(exc), api_key)}") from exc
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"模型响应缺少 choices/message：{_sanitize(str(data)[:200], api_key)}") from exc
    usage = data.get("usage") or {}
    return {"text": text,
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "model": data.get("model") or model}


def list_models(base_url: str, api_key: str | None, timeout: float = 30.0) -> list[str]:
    """测试连接：GET /models。异常文本同样剥 key。"""
    url = base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        raise ValueError(f"端点返回 {exc.response.status_code}："
                         f"{_sanitize(exc.response.text[:200], api_key)}") from exc
    except httpx.HTTPError as exc:
        raise ValueError(f"连接失败：{_sanitize(str(exc), api_key)}") from exc
    items = data.get("data") if isinstance(data, dict) else data
    return sorted({m.get("id") for m in (items or []) if isinstance(m, dict) and m.get("id")})
