"""Тексты ответов, разбор команд и отправка сообщений ВКонтакте."""

from __future__ import annotations

import secrets
from typing import Any

from .config import Settings

MAX_USER_MESSAGE_CHARS = 4000
MAX_VK_MESSAGE_CHARS = 4000

FALLBACK_REPLY = (
    "Извините, сейчас не удалось получить ответ. Попробуйте повторить вопрос немного позже "
    "или напишите менеджеру."
)

START_REPLY = (
    "Привет! Я Алина — консультант онлайн-университета Zerocoder.\n\n"
    "Помогу вам разобраться в программах, форматах обучения и выбрать подходящее "
    "направление. Расскажите, какую цель вы хотите достичь?"
)

HELP_REPLY = (
    "Я могу рассказать о программах Zerocoder, помочь сравнить направления и подсказать, "
    "как начать обучение.\n\n"
    "Команды:\n"
    "/start — начать консультацию\n"
    "/reset — очистить историю диалога\n"
    "/contact — получить информацию о связи с отделом продаж\n\n"
    "Напишите свой вопрос обычным сообщением."
)

RESET_REPLY = "История диалога очищена. Я помогу вам выбрать подходящую программу."


def contact_reply(settings: Settings) -> str:
    reply = (
        "Я помогу подготовить вопрос для отдела продаж и уточнить условия выбранной программы."
    )
    if settings.lead_form_url:
        reply += f"\n\nОставьте заявку через форму:\n{settings.lead_form_url}"
    else:
        reply += (
            "\n\nОставьте заявку через форму отдела продаж в официальных контактах "
            "Zerocoder, чтобы уточнить актуальные условия."
        )
    return reply


def command_reply(command: str, settings: Settings) -> str:
    if command == "/start":
        return START_REPLY
    if command == "/help":
        return HELP_REPLY
    if command == "/reset":
        return RESET_REPLY
    if command == "/contact":
        return contact_reply(settings)
    return HELP_REPLY


def extract_command(text: str) -> str | None:
    """Вернуть команду из текста, отбросив упоминание бота (`/start@bot`)."""
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None
    first_token = stripped.split(maxsplit=1)[0].casefold()
    return first_token.split("@", 1)[0]


def split_for_vk(text: str, max_length: int = MAX_VK_MESSAGE_CHARS) -> list[str]:
    """Разбить длинный ответ на части не длиннее лимита ВКонтакте."""
    remaining = text.strip()
    if not remaining:
        return []

    parts: list[str] = []
    while len(remaining) > max_length:
        candidates = []
        for separator in ("\n", " "):
            candidate = remaining.rfind(separator, 0, max_length)
            if candidate >= max_length // 2:
                candidates.append(candidate)
        split_at = max(candidates) if candidates else max_length
        part = remaining[:split_at].strip()
        if part:
            parts.append(part)
        remaining = remaining[split_at:].strip()
    if remaining:
        parts.append(remaining)
    return parts


def send_reply(
    vk: Any,
    user_id: int,
    reply: str,
    peer_id: int | None = None,
    use_peer_id: bool = False,
) -> None:
    """Отправить ответ в личный чат или беседу, разбив его на части."""
    target = (
        {"peer_id": peer_id}
        if use_peer_id and peer_id is not None
        else {"user_id": user_id}
    )
    for part in split_for_vk(reply):
        vk.messages.send(
            **target,
            message=part,
            random_id=secrets.randbelow(2147483647) + 1,
        )


def extract_message(event: Any) -> dict[str, Any] | None:
    message = getattr(event, "message", None)
    if message is None:
        event_object = getattr(event, "object", None)
        if isinstance(event_object, dict):
            message = event_object.get("message")
    return message if isinstance(message, dict) else None


def message_destination(
    message: dict[str, Any], user_id: int
) -> tuple[int | None, bool]:
    """Определить, отвечать в беседу (peer_id) или в личные сообщения."""
    try:
        peer_id = int(message.get("peer_id", 0))
    except (TypeError, ValueError):
        return None, False
    has_chat_id = message.get("chat_id") not in (None, 0, "0")
    use_peer_id = peer_id > 0 and (peer_id != user_id or has_chat_id)
    return (peer_id if use_peer_id else None), use_peer_id


def is_outgoing_message(message: dict[str, Any]) -> bool:
    value = message.get("out", 0)
    return value in (1, "1", True) or str(value).casefold() == "true"
