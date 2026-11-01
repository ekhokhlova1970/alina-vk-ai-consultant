"""Клиент OpenAI-совместимого Chat Completions API (ProxyAPI)."""

from __future__ import annotations

from openai import OpenAI

from .config import Settings

PROXY_API_BASE_URL = "https://api.proxyapi.ru/openai/v1"


class ProxyAnswerClient:
    """Тонкая обёртка над OpenAI SDK, привязанная к ProxyAPI."""

    def __init__(self, settings: Settings):
        self._client = OpenAI(
            api_key=settings.proxy_api_key,
            base_url=PROXY_API_BASE_URL,
            timeout=settings.request_timeout_seconds,
            max_retries=2,
        )
        self._model = settings.model
        self._max_reply_tokens = settings.max_reply_tokens

    def complete(self, messages: list[dict[str, str]]) -> str:
        """Отправить диалог модели и вернуть текст ответа."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_completion_tokens=self._max_reply_tokens,
        )
        content = response.choices[0].message.content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                value = (
                    part.get("text")
                    if isinstance(part, dict)
                    else getattr(part, "text", None)
                )
                if value:
                    text_parts.append(str(value))
            content = "".join(text_parts)
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Proxy API returned an empty response")
        return content.strip()
