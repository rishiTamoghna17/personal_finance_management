"""Pluggable model providers. All return the model's JSON answer as a dict. Default: Ollama on this machine."""
import json

import httpx
from django.conf import settings


class LLMError(Exception):
    pass


def _post(url, payload, headers=None, transport=None):
    try:
        with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS, transport=transport) as client:
            response = client.post(url, json=payload, headers=headers or {})
    except httpx.HTTPError as exc:
        raise LLMError(f"model unreachable ({type(exc).__name__})") from None
    if response.status_code >= 400:
        raise LLMError(f"model returned HTTP {response.status_code}")
    return response.json()


def _json(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        raise LLMError("model did not return JSON") from None


def ask(system, user, transport=None):
    provider = settings.LLM_PROVIDER
    if provider == "ollama":
        body = _post(f"{settings.LLM_OLLAMA_URL}/api/chat", {
            "model": settings.LLM_MODEL, "stream": False, "format": "json", "options": {"temperature": 0},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }, transport=transport)
        return _json(body.get("message", {}).get("content"))
    if provider == "groq":
        body = _post("https://api.groq.com/openai/v1/chat/completions", {
            "model": settings.LLM_MODEL, "temperature": 0, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }, headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"}, transport=transport)
        return _json(body["choices"][0]["message"]["content"])
    if provider == "gemini":
        body = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent", {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }, headers={"x-goog-api-key": settings.LLM_API_KEY}, transport=transport)
        return _json(body["candidates"][0]["content"]["parts"][0]["text"])
    raise LLMError(f"unknown LLM_PROVIDER {provider!r}")


def is_cloud():
    return settings.LLM_PROVIDER in ("gemini", "groq")


def chat(messages, tools=None, transport=None):
    """One chat turn with optional tool definitions. Local model only (Ollama): the advisor sends ledger summaries,
    including payee names, which must not leave this machine. Returns {"content", "tool_calls"}."""
    if settings.LLM_PROVIDER != "ollama":
        raise LLMError("the advisor chat runs only on the local model (LLM_PROVIDER=ollama)")
    payload = {"model": settings.LLM_MODEL, "stream": False, "options": {"temperature": 0.2}, "messages": messages}
    if tools:
        payload["tools"] = tools
    body = _post(f"{settings.LLM_OLLAMA_URL}/api/chat", payload, transport=transport)
    message = body.get("message") or {}
    return {"content": message.get("content") or "", "tool_calls": message.get("tool_calls") or []}
