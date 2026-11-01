"""Тесты текстов ответов, команд и отправки сообщений."""

from __future__ import annotations

import pytest

from alina_bot.messages import (
    HELP_REPLY,
    START_REPLY,
    command_reply,
    contact_reply,
    extract_command,
    is_outgoing_message,
    message_destination,
    send_reply,
    split_for_vk,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/start", "/start"),
        ("/START", "/start"),
        ("  /help  ", "/help"),
        ("/contact@alina_bot", "/contact"),
        ("/reset@alina_bot напиши заново", "/reset"),
        ("привет", None),
        ("", None),
    ],
)
def test_extract_command(text, expected):
    assert extract_command(text) == expected


def test_split_short_text_returns_single_part():
    assert split_for_vk("Привет!") == ["Привет!"]


def test_split_empty_text_returns_no_parts():
    assert split_for_vk("   ") == []


def test_split_long_text_by_spaces():
    parts = split_for_vk("слово " * 100, max_length=100)

    assert len(parts) > 1
    assert all(len(part) <= 100 for part in parts)
    assert all(part for part in parts)


def test_split_does_not_lose_words():
    text = "альфа бета гамма дельта эпсилон дзета эта тета"

    parts = split_for_vk(text, max_length=20)

    assert all(len(part) <= 20 for part in parts)
    assert " ".join(parts).split() == text.split()


def test_command_reply_for_known_commands(settings):
    assert command_reply("/start", settings) == START_REPLY
    assert command_reply("/unknown", settings) == HELP_REPLY


def test_contact_reply_without_form(settings):
    reply = contact_reply(settings)

    assert "официальных контактах" in reply
    assert "http" not in reply


def test_contact_reply_with_form(settings):
    settings_with_form = type(settings)(
        proxy_api_key="key",
        vk_token="token",
        group_id=1,
        lead_form_url="https://zerocoder.ru/form",
    )

    assert "https://zerocoder.ru/form" in contact_reply(settings_with_form)


@pytest.mark.parametrize("value", [1, "1", True, "true", "True"])
def test_outgoing_detection_true(value):
    assert is_outgoing_message({"out": value}) is True


@pytest.mark.parametrize("value", [0, "0", False, None, 2])
def test_outgoing_detection_false(value):
    assert is_outgoing_message({"out": value}) is False


def test_destination_for_private_dialog():
    assert message_destination({"peer_id": 7}, 7) == (None, False)


def test_destination_for_chat():
    message = {"peer_id": 2000000001, "chat_id": 5}

    assert message_destination(message, 7) == (2000000001, True)


def test_destination_with_invalid_peer_id():
    assert message_destination({"peer_id": "abc"}, 7) == (None, False)


def test_send_reply_to_user(fake_vk):
    send_reply(fake_vk, user_id=7, reply="Привет!")

    call = fake_vk.messages.calls[0]
    assert call["user_id"] == 7
    assert call["message"] == "Привет!"
    assert 1 <= call["random_id"] <= 2147483647


def test_send_reply_to_chat(fake_vk):
    send_reply(fake_vk, user_id=7, reply="Привет!", peer_id=2000000001, use_peer_id=True)

    assert fake_vk.messages.calls[0]["peer_id"] == 2000000001
    assert "user_id" not in fake_vk.messages.calls[0]
