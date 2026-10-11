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
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    data = None
    last_err: Exception | None = None
    for url in _candidates(base_url, "/chat/completions"):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                if resp.status_code == 404 and url == _candidates(base_url, "/chat/completions")[0]:
                    last_err = httpx.HTTPStatusError("404", request=resp.request, response=resp)
                    continue  # /v1 回退
                resp.raise_for_status()
                data = resp.json()
                break
        except httpx.HTTPStatusError as exc:
            body = _sanitize(exc.response.text[:300], api_key)
            raise ValueError(f"模型端点返回 {exc.response.status_code}：{body}") from exc
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            last_err = exc
    if data is None:
        raise ValueError(f"模型调用失败：{_sanitize(str(last_err), api_key)}")
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
