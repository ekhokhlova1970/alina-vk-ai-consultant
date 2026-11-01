"""Тесты загрузки и валидации конфигурации."""

from __future__ import annotations

import pytest

import alina_bot.config as config
from alina_bot.config import ConfigurationError, load_settings

ENV_NAMES = [
    "PROXY_API_KEY",
    "VK_TOKEN",
    "VK_ACCESS_TOKEN",
    "VK_GROUP_ID",
    "OPENAI_MODEL",
    "LEAD_FORM_URL",
    "LOG_LEVEL",
    "MAX_REPLY_TOKENS",
    "MAX_HISTORY_MESSAGES",
    "HISTORY_TTL_SECONDS",
    "REQUEST_TIMEOUT_SECONDS",
    "KNOWLEDGE_BASE_PATH",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Изолировать тесты от локального `.env` разработчика."""
    monkeypatch.setattr(config, "load_dotenv", lambda *args, **kwargs: None)
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PROXY_API_KEY", "proxy-key")
    monkeypatch.setenv("VK_TOKEN", "vk-token")
    monkeypatch.setenv("VK_GROUP_ID", "241746021")


def test_loads_required_values():
    settings = load_settings()

    assert settings.proxy_api_key == "proxy-key"
    assert settings.vk_token == "vk-token"
    assert settings.group_id == 241746021
    assert settings.model == "gpt-4o-mini"
    assert settings.history_messages == 12
    assert settings.knowledge_base_path == config.DEFAULT_KNOWLEDGE_BASE_PATH


def test_accepts_legacy_token_variable(monkeypatch):
    monkeypatch.delenv("VK_TOKEN")
    monkeypatch.setenv("VK_ACCESS_TOKEN", "legacy-token")

    assert load_settings().vk_token == "legacy-token"


def test_negative_group_id_becomes_positive(monkeypatch):
    monkeypatch.setenv("VK_GROUP_ID", "-241746021")

    assert load_settings().group_id == 241746021


@pytest.mark.parametrize("name", ["PROXY_API_KEY", "VK_TOKEN", "VK_GROUP_ID"])
def test_missing_required_variable(monkeypatch, name):
    monkeypatch.delenv(name)

    with pytest.raises(ConfigurationError, match=name):
        load_settings()


def test_group_id_must_be_numeric(monkeypatch):
    monkeypatch.setenv("VK_GROUP_ID", "zerocoder")

    with pytest.raises(ConfigurationError, match="VK_GROUP_ID"):
        load_settings()


def test_group_id_must_be_positive(monkeypatch):
    monkeypatch.setenv("VK_GROUP_ID", "0")

    with pytest.raises(ConfigurationError, match="положительным"):
        load_settings()


@pytest.mark.parametrize(
    "url",
    ["ftp://example.com/form", "https://example.com/form?x=1 2", "not-a-url"],
)
def test_invalid_lead_form_url(monkeypatch, url):
    monkeypatch.setenv("LEAD_FORM_URL", url)

    with pytest.raises(ConfigurationError, match="LEAD_FORM_URL"):
        load_settings()


def test_numeric_limits_are_validated(monkeypatch):
    monkeypatch.setenv("MAX_REPLY_TOKENS", "50")
    with pytest.raises(ConfigurationError, match="MAX_REPLY_TOKENS"):
        load_settings()

    monkeypatch.setenv("MAX_REPLY_TOKENS", "700")
    monkeypatch.setenv("MAX_HISTORY_MESSAGES", "many")
    with pytest.raises(ConfigurationError, match="MAX_HISTORY_MESSAGES"):
        load_settings()


def test_knowledge_base_must_be_markdown(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BASE_PATH", "notes.txt")

    with pytest.raises(ConfigurationError, match="Markdown"):
        load_settings()


def test_optional_overrides(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("LEAD_FORM_URL", "https://zerocoder.ru/form")
    monkeypatch.setenv("KNOWLEDGE_BASE_PATH", "docs/knowledge.md")

    settings = load_settings()

    assert settings.model == "gpt-4o"
    assert settings.log_level == "DEBUG"
    assert settings.lead_form_url == "https://zerocoder.ru/form"
    assert settings.knowledge_base_path == config.PROJECT_ROOT / "docs/knowledge.md"


def test_secrets_are_hidden_in_repr():
    representation = repr(load_settings())

    assert "proxy-key" not in representation
    assert "vk-token" not in representation
