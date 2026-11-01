"""История диалогов в оперативной памяти: TTL, лимиты и вытеснение."""

from __future__ import annotations

import time
from collections import OrderedDict, deque
from dataclasses import dataclass

from .config import (
    DEFAULT_HISTORY_MESSAGES,
    DEFAULT_HISTORY_TTL_SECONDS,
)

MAX_IN_MEMORY_USERS = 1000


@dataclass
class UserState:
    messages: deque[dict[str, str]]
    last_seen: float


class ConversationStore:
    """Хранилище последних сообщений пользователей без записи на диск."""

    def __init__(
        self,
        max_messages: int = DEFAULT_HISTORY_MESSAGES,
        ttl_seconds: int = DEFAULT_HISTORY_TTL_SECONDS,
        max_users: int = MAX_IN_MEMORY_USERS,
    ):
        self._max_messages = max_messages
        self._ttl_seconds = ttl_seconds
        self._max_users = max_users
        self._states: OrderedDict[int, UserState] = OrderedDict()

    def _prune(self, now: float) -> None:
        expired = [
            user_id
            for user_id, state in self._states.items()
            if now - state.last_seen > self._ttl_seconds
        ]
        for user_id in expired:
            self._states.pop(user_id, None)
        while len(self._states) > self._max_users:
            self._states.popitem(last=False)

    def _get_state(self, user_id: int) -> UserState:
        now = time.monotonic()
        self._prune(now)
        state = self._states.get(user_id)
        if state is None:
            state = UserState(messages=deque(maxlen=self._max_messages), last_seen=now)
            self._states[user_id] = state
        else:
            state.last_seen = now
            self._states.move_to_end(user_id)
        return state

    def get_history(self, user_id: int) -> list[dict[str, str]]:
        return list(self._get_state(user_id).messages)

    def append(self, user_id: int, role: str, content: str) -> None:
        if content:
            self._get_state(user_id).messages.append({"role": role, "content": content})

    def clear(self, user_id: int) -> None:
        self._states.pop(user_id, None)
