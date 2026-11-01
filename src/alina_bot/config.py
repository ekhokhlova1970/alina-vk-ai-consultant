"""Конфигурация приложения: чтение и валидация переменных окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_PROMPT_PATH = PROJECT_ROOT / "prompts" / "alina_system_prompt.md"
DEFAULT_KNOWLEDGE_BASE_PATH = PROJECT_ROOT / "data" / "knowledge_base.md"

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_REPLY_TOKENS = 700
DEFAULT_HISTORY_MESSAGES = 12
DEFAULT_HISTORY_TTL_SECONDS = 3600
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0


class ConfigurationError(RuntimeError):
    """Некорректная или неполная конфигурация приложения."""


@dataclass(frozen=True)
class Settings:
    """Проверенные настройки, собранные из переменных окружения."""

    proxy_api_key: str = field(repr=False)
    vk_token: str = field(repr=False)
    group_id: int
    model: str = DEFAULT_MODEL
    lead_form_url: str = ""
    log_level: str = "INFO"
    max_reply_tokens: int = DEFAULT_MAX_REPLY_TOKENS
    history_messages: int = DEFAULT_HISTORY_MESSAGES
    history_ttl_seconds: int = DEFAULT_HISTORY_TTL_SECONDS
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
    knowledge_base_path: Path = DEFAULT_KNOWLEDGE_BASE_PATH


def _first_value(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return None


def _required_value(*names: str) -> str:
    value = _first_value(*names)
    if value is None:
        raise ConfigurationError(
            "Не задана переменная окружения {}".format(" или ".join(names))
        )
    return value


def _optional_value(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _integer_setting(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(
            f"Переменная {name} должна содержать целое число"
        ) from exc
    if value < minimum or value > maximum:
        raise ConfigurationError(
            f"Переменная {name} должна быть в диапазоне {minimum}..{maximum}"
        )
    return value


def _float_setting(name: str, default: float, minimum: float, maximum: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ConfigurationError(
            f"Переменная {name} должна содержать число"
        ) from exc
    if value < minimum or value > maximum:
        raise ConfigurationError(
            f"Переменная {name} должна быть в диапазоне {minimum}..{maximum}"
        )
    return value


def load_settings() -> Settings:
    """Прочитать `.env` и переменные окружения, вернуть проверенные настройки."""
    load_dotenv(ENV_PATH)

    proxy_api_key = _required_value("PROXY_API_KEY")
    vk_token = _required_value("VK_TOKEN", "VK_ACCESS_TOKEN")
    raw_group_id = _required_value("VK_GROUP_ID")
    try:
        group_id = abs(int(raw_group_id))
    except ValueError as exc:
        raise ConfigurationError("VK_GROUP_ID должен содержать числовой ID") from exc
    if group_id <= 0:
        raise ConfigurationError("VK_GROUP_ID должен быть положительным ID")

    model = _optional_value("OPENAI_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL
    lead_form_url = _optional_value("LEAD_FORM_URL")
    if lead_form_url and (
        not lead_form_url.startswith(("https://", "http://"))
        or any(character.isspace() for character in lead_form_url)
    ):
        raise ConfigurationError(
            "LEAD_FORM_URL должен быть корректной ссылкой http:// или https://"
        )

    knowledge_path_value = _optional_value("KNOWLEDGE_BASE_PATH")
    knowledge_base_path = (
        Path(knowledge_path_value)
        if knowledge_path_value
        else DEFAULT_KNOWLEDGE_BASE_PATH
    )
    if not knowledge_base_path.is_absolute():
        knowledge_base_path = PROJECT_ROOT / knowledge_base_path
    if (
        knowledge_base_path.name.startswith(".")
        or knowledge_base_path.suffix.casefold() not in {".md", ".markdown"}
    ):
        raise ConfigurationError(
            "KNOWLEDGE_BASE_PATH должен указывать на Markdown-файл"
        )

    return Settings(
        proxy_api_key=proxy_api_key,
        vk_token=vk_token,
        group_id=group_id,
        model=model,
        lead_form_url=lead_form_url,
        log_level=_optional_value("LOG_LEVEL", "INFO").upper() or "INFO",
        max_reply_tokens=_integer_setting(
            "MAX_REPLY_TOKENS", DEFAULT_MAX_REPLY_TOKENS, 100, 4096
        ),
        history_messages=_integer_setting(
            "MAX_HISTORY_MESSAGES", DEFAULT_HISTORY_MESSAGES, 2, 40
        ),
        history_ttl_seconds=_integer_setting(
            "HISTORY_TTL_SECONDS", DEFAULT_HISTORY_TTL_SECONDS, 60, 86400
        ),
        request_timeout_seconds=_float_setting(
            "REQUEST_TIMEOUT_SECONDS", DEFAULT_REQUEST_TIMEOUT_SECONDS, 5.0, 120.0
        ),
        knowledge_base_path=knowledge_base_path,
    )
