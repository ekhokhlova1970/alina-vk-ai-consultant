"""Тесты истории диалогов: лимиты, TTL и очистка."""

from __future__ import annotations

import pytest

import alina_bot.history as history_module
from alina_bot.history import ConversationStore


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch):
    fake_clock = FakeClock()
    monkeypatch.setattr(history_module.time, "monotonic", fake_clock.monotonic)
    return fake_clock


def test_append_and_get_history(clock):
    store = ConversationStore(max_messages=10, ttl_seconds=60)

    store.append(1, "user", "Привет")
    clock.now = 1.0
    store.append(1, "assistant", "Здравствуйте")

    assert store.get_history(1) == [
        {"role": "user", "content": "Привет"},
        {"role": "assistant", "content": "Здравствуйте"},
    ]


def test_empty_content_is_ignored(clock):
    store = ConversationStore(max_messages=10, ttl_seconds=60)

    store.append(1, "user", "")

    assert store.get_history(1) == []


def test_history_is_limited_by_max_messages(clock):
    store = ConversationStore(max_messages=2, ttl_seconds=60)

    store.append(1, "user", "раз")
    store.append(1, "assistant", "два")
    store.append(1, "user", "три")

    assert [item["content"] for item in store.get_history(1)] == ["два", "три"]


def test_history_expires_after_ttl(clock):
    store = ConversationStore(max_messages=10, ttl_seconds=60)
    store.append(1, "user", "Привет")

    clock.now = 61.0

    assert store.get_history(1) == []


def test_history_survives_within_ttl(clock):
    store = ConversationStore(max_messages=10, ttl_seconds=60)
    store.append(1, "user", "Привет")

    clock.now = 59.0

    assert store.get_history(1) == [{"role": "user", "content": "Привет"}]


def test_clear_removes_only_one_user(clock):
    store = ConversationStore(max_messages=10, ttl_seconds=60)
    store.append(1, "user", "Первый")
    store.append(2, "user", "Второй")

    store.clear(1)

    assert store.get_history(1) == []
    assert store.get_history(2) == [{"role": "user", "content": "Второй"}]


def test_oldest_users_are_evicted(clock):
    store = ConversationStore(max_messages=10, ttl_seconds=600, max_users=2)

    store.append(1, "user", "Первый")
    clock.now = 1.0
    store.append(2, "user", "Второй")
    clock.now = 2.0
    store.append(3, "user", "Третий")

    assert len(store.get_history(2)) == 1
    assert len(store.get_history(3)) == 1
    assert store.get_history(1) == []
