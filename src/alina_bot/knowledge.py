"""Локальная база знаний: разбиение на разделы и поиск релевантного контекста."""

from __future__ import annotations

import re
from pathlib import Path

from .config import ConfigurationError

MAX_CONTEXT_CHARS = 12000
MAX_SELECTED_CHUNKS = 5

_STOP_WORDS = frozenset(
    {
        "а",
        "без",
        "быть",
        "в",
        "вы",
        "где",
        "для",
        "если",
        "есть",
        "же",
        "и",
        "из",
        "или",
        "к",
        "как",
        "какой",
        "когда",
        "кто",
        "ли",
        "мне",
        "можно",
        "на",
        "не",
        "но",
        "о",
        "об",
        "от",
        "по",
        "под",
        "пожалуйста",
        "что",
        "чтобы",
        "это",
        "я",
    }
)

_TOKEN_RE = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)
_HEADING_SPLIT_RE = re.compile(r"(?m)(?=^#{1,6}\s+)")

_ALIASES = {
    "ии": ("ии", "ai", "нейросет", "интеллект"),
    "ai": ("ai", "ии", "нейросет", "интеллект"),
    "нейросет": ("нейросет", "нейросеть", "ии", "ai", "интеллект"),
    "вайб": ("вайб", "vibe", "claude", "агент"),
    "аналит": ("аналит", "аналитик", "данн"),
    "автомат": ("автомат", "интегра", "n8n", "albato"),
    "zerocod": ("zerocod", "zerocoder", "зерокодер"),
    "цена": ("цена", "стоимост", "оплат", "рассроч", "скидк"),
    "контакт": ("контакт", "телефон", "почт", "адрес", "email"),
    "форма": ("форма", "заяв", "связ", "продаж"),
    "обуч": ("обуч", "курс", "программ", "формат"),
}


def _normalise_token(token: str) -> str:
    return token.casefold().replace("ё", "е")


def _tokens(value: str) -> set[str]:
    return {
        _normalise_token(token)
        for token in _TOKEN_RE.findall(value)
        if len(token) >= 2 and _normalise_token(token) not in _STOP_WORDS
    }


def _expanded_tokens(value: str) -> set[str]:
    tokens = _tokens(value)
    expanded = set(tokens)
    for token in list(tokens):
        for alias in _ALIASES.get(token, ()):
            expanded.add(_normalise_token(alias))
    for prefix, aliases in _ALIASES.items():
        if any(token.startswith(prefix) or prefix.startswith(token) for token in tokens):
            for alias in aliases:
                expanded.add(_normalise_token(alias))
    return expanded


def _tokens_match(first: str, second: str) -> bool:
    if first == second:
        return True
    prefix_length = min(4, len(first), len(second))
    return prefix_length >= 4 and first[:prefix_length] == second[:prefix_length]


class KnowledgeBase:
    """Markdown-база знаний, разбитая на разделы по заголовкам."""

    def __init__(self, text: str):
        self.text = text.strip()
        chunks = [chunk.strip() for chunk in _HEADING_SPLIT_RE.split(self.text)]
        self.chunks = [chunk for chunk in chunks if chunk]

    @classmethod
    def from_file(cls, path: Path) -> KnowledgeBase:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ConfigurationError(
                f"Не удалось прочитать базу знаний из {path.name}"
            ) from exc
        if not text.strip():
            raise ConfigurationError("База знаний пуста")
        return cls(text)

    def context_for(self, query: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
        """Вернуть обзорный раздел и до четырёх разделов, релевантных запросу."""
        if not self.chunks:
            return ""

        query_tokens = _expanded_tokens(query)
        scored: list[tuple[int, int]] = []
        for index, chunk in enumerate(self.chunks):
            chunk_tokens = _tokens(chunk)
            score = sum(
                1
                for query_token in query_tokens
                if any(
                    _tokens_match(query_token, chunk_token)
                    for chunk_token in chunk_tokens
                )
            )
            if score:
                scored.append((score, index))

        selected = [0]
        if scored:
            for _, index in sorted(scored, key=lambda item: (-item[0], item[1])):
                if index not in selected:
                    selected.append(index)
                if len(selected) >= MAX_SELECTED_CHUNKS:
                    break

        context = "\n\n".join(self.chunks[index] for index in selected)
        return context[:max_chars].strip()


def load_text_file(path: Path, description: str) -> str:
    """Прочитать непустой UTF-8 текстовый файл или выбросить ConfigurationError."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ConfigurationError(
            f"Не удалось прочитать {description} из {path.name}"
        ) from exc
    if not text.strip():
        raise ConfigurationError(f"Файл {description} пуст")
    return text.strip()


def build_system_prompt(
    template: str,
    knowledge_context: str,
    lead_form_url: str,
) -> str:
    """Собрать системное сообщение из промпта, ссылки на форму и базы знаний."""
    parts = [template.strip()]
    if lead_form_url:
        parts.append(
            f"Ссылка на форму отдела продаж, переданная приложением:\n{lead_form_url}"
        )
    context = knowledge_context.strip() or "Подтверждённых сведений в базе знаний нет."
    parts.append(f"НАЧАЛО БАЗЫ ЗНАНИЙ\n{context}\nКОНЕЦ БАЗЫ ЗНАНИЙ")
    return "\n\n".join(parts)
