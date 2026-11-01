"""Тесты обработки событий Long Poll ВКонтакте."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from vk_api.bot_longpoll import VkBotEventType

from alina_bot.config import Settings
from alina_bot.handlers import process_event
from alina_bot.history import ConversationStore
from alina_bot.knowledge import KnowledgeBase
from alina_bot.messages import (
    FALLBACK_REPLY,
    MAX_USER_MESSAGE_CHARS,
    START_REPLY,
)

KB_TEXT = "# Программы\n\nВайб-кодинг на Claude Code и нейросети."


def make_event(text: str = "Привет", **message_fields: object) -> SimpleNamespace:
    message = {"from_id": 7, "peer_id": 7, "text": text}
    message.update(message_fields)
    return SimpleNamespace(type=VkBotEventType.MESSAGE_NEW, message=message)


def run_event(event, vk, client, store, settings, knowledge_base=None):
    process_event(
        event,
        vk,
        client,
        store,
        settings,
        "Ты Алина, консультант Zerocoder.",
        knowledge_base or KnowledgeBase(KB_TEXT),
    )


@pytest.fixture
def store() -> ConversationStore:
    return ConversationStore(max_messages=10, ttl_seconds=60)


def test_ignores_non_message_events(fake_vk, make_client, store, settings):
    event = SimpleNamespace(type=VkBotEventType.WALL_POST_NEW, message={})

    run_event(event, fake_vk, make_client(), store, settings)

    assert fake_vk.messages.calls == []


def test_ignores_outgoing_messages(fake_vk, make_client, store, settings):
    run_event(make_event(out=1), fake_vk, make_client(), store, settings)

    assert fake_vk.messages.calls == []


def test_ignores_empty_text(fake_vk, make_client, store, settings):
    run_event(make_event(text="   "), fake_vk, make_client(), store, settings)

    assert fake_vk.messages.calls == []


def test_start_command_clears_history_and_greets(
    fake_vk, make_client, store, settings
):
    store.append(7, "user", "Старое сообщение")

    run_event(make_event("/start"), fake_vk, make_client(), store, settings)

    assert fake_vk.messages.calls[0]["message"] == START_REPLY
    assert store.get_history(7) == []


def test_regular_question_goes_to_model_with_knowledge(
    fake_vk, make_client, store, settings
):
    client = make_client(reply="Расскажу о вайб-кодинге.")

    run_event(make_event("Что такое вайб-кодинг?"), fake_vk, client, store, settings)

    assert fake_vk.messages.calls[0]["message"] == "Расскажу о вайб-кодинге."
    request = client.requests[0]
    assert request[0]["role"] == "system"
    assert "НАЧАЛО БАЗЫ ЗНАНИЙ" in request[0]["content"]
    assert "Вайб-кодинг" in request[0]["content"]
    assert request[-1] == {"role": "user", "content": "Что такое вайб-кодинг?"}


def test_second_question_includes_previous_history(
    fake_vk, make_client, store, settings
):
    client = make_client(reply="Ответ")

    run_event(make_event("Первый вопрос"), fake_vk, client, store, settings)
    run_event(make_event("Второй вопрос"), fake_vk, client, store, settings)

    second_request = client.requests[1]
    assert [item["role"] for item in second_request] == [
        "system",
        "user",
        "assistant",
        "user",
    ]


def test_api_error_returns_fallback_and_keeps_history(
    fake_vk, make_client, store, settings
):
    client = make_client(error=RuntimeError("network"))

    run_event(make_event("Вопрос"), fake_vk, client, store, settings)

    assert fake_vk.messages.calls[0]["message"] == FALLBACK_REPLY
    assert len(store.get_history(7)) == 2


def test_too_long_message_is_rejected_without_model_call(
    fake_vk, make_client, store, settings
):
    client = make_client()

    run_event(make_event("а" * (MAX_USER_MESSAGE_CHARS + 1)), fake_vk, client, store, settings)

    assert client.requests == []
    assert "покороче" in fake_vk.messages.calls[0]["message"]


def test_reply_to_chat_uses_peer_id(fake_vk, make_client, store, settings):
    event = make_event(peer_id=2000000001, chat_id=5)

    run_event(event, fake_vk, make_client(reply="Привет"), store, settings)

    assert fake_vk.messages.calls[0]["peer_id"] == 2000000001


def test_vk_send_failure_is_logged_not_raised(make_client, store, settings):
    class BrokenVk:
        def __init__(self):
            self.messages = self

        def send(self, **kwargs):
            raise RuntimeError("vk is down")

    run_event(make_event("Вопрос"), BrokenVk(), make_client(), store, settings)


def test_lead_form_is_added_to_system_prompt(fake_vk, make_client, store, settings):
    settings_with_form = Settings(
        proxy_api_key="key",
        vk_token="token",
        group_id=1,
        lead_form_url="https://zerocoder.ru/form",
    )
    client = make_client()

    run_event(make_event("Вопрос"), fake_vk, client, store, settings_with_form)

    assert "https://zerocoder.ru/form" in client.requests[0][0]["content"]
