"""Точка входа: настройка логирования, подключение к VK и цикл Long Poll."""

from __future__ import annotations

import logging
import os
import sys
import time

import vk_api
from dotenv import load_dotenv
from vk_api.bot_longpoll import VkBotLongPoll

from .config import (
    DEFAULT_PROMPT_PATH,
    ENV_PATH,
    ConfigurationError,
    load_settings,
)
from .handlers import process_event
from .history import ConversationStore
from .knowledge import KnowledgeBase, load_text_file
from .llm import ProxyAnswerClient

logger = logging.getLogger("alina_bot")


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )


def run() -> int:
    """Запустить бота. Возвращает код выхода процесса."""
    load_dotenv(ENV_PATH)
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))

    try:
        settings = load_settings()
        system_prompt_template = load_text_file(
            DEFAULT_PROMPT_PATH, "системный промпт"
        )
        knowledge_base = KnowledgeBase.from_file(settings.knowledge_base_path)
    except ConfigurationError as exc:
        logger.error("Запуск остановлен: %s", exc)
        return 1

    logger.info("Запуск Алины. Модель: %s", settings.model)
    logger.info("База знаний загружена: %d фрагментов", len(knowledge_base.chunks))

    try:
        answer_client = ProxyAnswerClient(settings)
        vk_session = vk_api.VkApi(token=settings.vk_token)
        vk = vk_session.get_api()
        group = vk.groups.getById(group_id=settings.group_id)
        group_name = group[0].get("name", "") if group else ""
        suffix = ": " + group_name if group_name else ""
        logger.info("Подключение к ВКонтакте установлено%s", suffix)
    except Exception as exc:
        logger.error("Не удалось инициализировать подключения: %s", type(exc).__name__)
        return 1

    conversation_store = ConversationStore(
        max_messages=settings.history_messages,
        ttl_seconds=settings.history_ttl_seconds,
    )
    logger.info("Ожидание сообщений ВКонтакте")
    longpoll: VkBotLongPoll | None = None

    while True:
        try:
            if longpoll is None:
                longpoll = VkBotLongPoll(vk_session, settings.group_id)
                logger.info("Long Poll подключён")
            for event in longpoll.listen():
                process_event(
                    event,
                    vk,
                    answer_client,
                    conversation_store,
                    settings,
                    system_prompt_template,
                    knowledge_base,
                )
            longpoll = None
        except KeyboardInterrupt:
            logger.info("Остановка по запросу пользователя")
            return 0
        except Exception as exc:
            error_code = getattr(exc, "error_code", None)
            if error_code is None:
                logger.error("Ошибка цикла Long Poll: %s", type(exc).__name__)
            else:
                logger.error("Ошибка цикла Long Poll: код %s", error_code)
            longpoll = None
            time.sleep(5)


def main() -> int:
    return run()
