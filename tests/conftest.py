"""Общие фикстуры и вспомогательные объекты для тестов."""

from __future__ import annotations

from pathlib import Path

import pytest

from alina_bot.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Настройки с фиктивными секретами: сетевые вызовы в тестах не выполняются."""
    return Settings(
        proxy_api_key="test-proxy-key",
        vk_token="test-vk-token",
        group_id=241746021,
        knowledge_base_path=Path("data/knowledge_base.md"),
    )


class FakeMessagesApi:
    """Имитация `vk.messages`: запоминает отправленные сообщения."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def send(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


class FakeVk:
    def __init__(self) -> None:
        self.messages = FakeMessagesApi()


class FakeAnswerClient:
    """Имитация клиента ProxyAPI с заранее заданным поведением."""

    def __init__(self, reply: str = "Ответ Алины", error: Exception | None = None):
        self.reply = reply
        self.error = error
        self.requests: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.requests.append(messages)
        if self.error is not None:
            raise self.error
        return self.reply


@pytest.fixture
def fake_vk() -> FakeVk:
    return FakeVk()


@pytest.fixture
def make_client():
    return FakeAnswerClient

