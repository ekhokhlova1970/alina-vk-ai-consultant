"""Тесты поиска по базе знаний и сборки системного промпта."""

from __future__ import annotations

import pytest

from alina_bot.config import DEFAULT_KNOWLEDGE_BASE_PATH, ConfigurationError
from alina_bot.knowledge import (
    KnowledgeBase,
    build_system_prompt,
    load_text_file,
)

KB_TEXT = """# О компании

Zerocoder обучает нейросетям и зерокодингу.

## Программы

Вайб-кодинг на Claude Code и автоматизация.

## Контакты

Почта care@zerocoder.ru.
"""


def test_splits_markdown_by_headings():
    knowledge_base = KnowledgeBase(KB_TEXT)

    assert len(knowledge_base.chunks) == 3
    assert knowledge_base.chunks[0].startswith("# О компании")
    assert knowledge_base.chunks[1].startswith("## Программы")


def test_context_starts_with_overview_and_adds_relevant_section():
    context = KnowledgeBase(KB_TEXT).context_for("расскажите про вайб-кодинг")

    assert context.startswith("# О компании")
    assert "Вайб-кодинг" in context


def test_context_without_matches_returns_only_overview():
    context = KnowledgeBase(KB_TEXT).context_for("погода на марсе")

    assert context == KB_TEXT.split("\n\n## ")[0].strip()


def test_context_is_truncated():
    knowledge_base = KnowledgeBase("# Раздел\n\n" + "данные " * 100)

    assert len(knowledge_base.context_for("данные", max_chars=30)) == 30


def test_from_file_reads_utf8(tmp_path):
    path = tmp_path / "knowledge.md"
    path.write_text(KB_TEXT, encoding="utf-8")

    assert len(KnowledgeBase.from_file(path).chunks) == 3


def test_from_file_rejects_empty_file(tmp_path):
    path = tmp_path / "empty.md"
    path.write_text("   ", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="пуста"):
        KnowledgeBase.from_file(path)


def test_from_file_reports_missing_file(tmp_path):
    with pytest.raises(ConfigurationError, match="Не удалось прочитать"):
        KnowledgeBase.from_file(tmp_path / "missing.md")


def test_project_knowledge_base_is_loadable():
    knowledge_base = KnowledgeBase.from_file(DEFAULT_KNOWLEDGE_BASE_PATH)

    assert len(knowledge_base.chunks) >= 5
    assert "Zerocoder" in knowledge_base.context_for("какие есть программы")


def test_build_system_prompt_adds_markers():
    prompt = build_system_prompt("Ты Алина.", "Программа", "")

    assert prompt.startswith("Ты Алина.")
    assert "НАЧАЛО БАЗЫ ЗНАНИЙ\nПрограмма\nКОНЕЦ БАЗЫ ЗНАНИЙ" in prompt
    assert "форма" not in prompt.casefold()


def test_build_system_prompt_handles_empty_context():
    prompt = build_system_prompt("Ты Алина.", "", "")

    assert "Подтверждённых сведений в базе знаний нет." in prompt


def test_build_system_prompt_adds_lead_form():
    prompt = build_system_prompt("Ты Алина.", "", "https://zerocoder.ru/form")

    assert "https://zerocoder.ru/form" in prompt


def test_load_text_file_returns_stripped_text(tmp_path):
    path = tmp_path / "prompt.md"
    path.write_text("\n  Ты Алина.  \n", encoding="utf-8")

    assert load_text_file(path, "промпт") == "Ты Алина."


def test_load_text_file_rejects_empty_file(tmp_path):
    path = tmp_path / "prompt.md"
    path.write_text("\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="пуст"):
        load_text_file(path, "промпт")
