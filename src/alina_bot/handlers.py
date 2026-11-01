"""Обработка событий Long Poll: команды, поиск по базе знаний, ответ модели."""

from __future__ import annotations

import logging
from typing import Any

from vk_api.bot_longpoll import VkBotEventType

from .config import Settings
from .history import ConversationStore
from .knowledge import KnowledgeBase, build_system_prompt
from .llm import ProxyAnswerClient
from .messages import (
    FALLBACK_REPLY,
    MAX_USER_MESSAGE_CHARS,
    command_reply,
    extract_command,
    extract_message,
    is_outgoing_message,
    message_destination,
    send_reply,
)

logger = logging.getLogger("alina_bot")


def process_event(
    event: Any,
    vk: Any,
    answer_client: ProxyAnswerClient,
    conversation_store: ConversationStore,
    settings: Settings,
    system_prompt_template: str,
    knowledge_base: KnowledgeBase,
) -> None:
    """Обработать одно событие Long Poll ВКонтакте."""
    if getattr(event, "type", None) != VkBotEventType.MESSAGE_NEW:
        return

    message = extract_message(event)
    if message is None or is_outgoing_message(message):
        return

    try:
        from_id = int(message.get("from_id", 0))
    except (TypeError, ValueError):
        return
    if from_id <= 0:
        return

    user_id = from_id
    peer_id, use_peer_id = message_destination(message, user_id)
    text = message.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return
    text = text.strip()

    command = extract_command(text)
    if command:
        if command in ("/start", "/reset"):
            conversation_store.clear(user_id)
        reply = command_reply(command, settings)
    elif len(text) > MAX_USER_MESSAGE_CHARS:
        reply = "Пожалуйста, отправьте вопрос покороче — так я смогу дать точный ответ."
    else:
        history = conversation_store.get_history(user_id)
        knowledge_context = knowledge_base.context_for(text)
        system_prompt = build_system_prompt(
            system_prompt_template,
            knowledge_context,
            settings.lead_form_url,
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": text})
        try:
            reply = answer_client.complete(messages)
        except Exception as exc:
            logger.warning("Proxy API request failed: %s", type(exc).__name__)
            reply = FALLBACK_REPLY
        conversation_store.append(user_id, "user", text)
        conversation_store.append(user_id, "assistant", reply)

    try:
        send_reply(
            vk,
            user_id,
            reply,
            peer_id=peer_id,
            use_peer_id=use_peer_id,
        )
    except Exception as exc:
        logger.error("VK message sending failed: %s", type(exc).__name__)
