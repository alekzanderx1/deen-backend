# core/memory.py
import os
from core.config import REDIS_URL, KEY_PREFIX, TTL_SECONDS, MAX_MESSAGES
from typing import Callable, Union
import redis
from langchain_community.chat_message_histories import (
    RedisChatMessageHistory,
    ChatMessageHistory as EphemeralHistory,
)

HistoryT = Union[RedisChatMessageHistory, EphemeralHistory]

from langchain_core.runnables.history import RunnableWithMessageHistory

# Check to make sure redis is working fine
def _redis_ok(url: str) -> bool:
    try:
        client = redis.from_url(url)
        client.ping()
        print("USING REDIS, MEMORY PERSISTENCE ENABLED")
        return True
    except Exception as e:
        print(f"[memory] Redis not reachable: {e}")
        return False

USE_REDIS = _redis_ok(REDIS_URL)


def make_history(session_id: str) -> HistoryT:
    """Return a message history bound to this session.
    Uses Redis when available; otherwise falls back to per-process ephemeral memory.
    """
    if USE_REDIS:
        # Key shape: <prefix>:<session_id>
        return RedisChatMessageHistory(
            session_id=f"{KEY_PREFIX}:{session_id}",
            url=REDIS_URL,
            ttl=TTL_SECONDS,
        )
    # Fallback: Ephemeral (non-persistent) history so the app still works without Redis
    print(f"[memory] Using ephemeral in-memory history for session: {session_id}")
    return EphemeralHistory()


def trim_history(history: HistoryT, max_messages: int = MAX_MESSAGES):
    """Hard-cap the number of stored messages to avoid unbounded growth.
    Keeps most recent N messages.
    """
    # `messages` returns a list[BaseMessage] in order
    msgs = history.messages
    if len(msgs) > max_messages:
        # overwrite with the last N messages
        keep = msgs[-max_messages:]
        history.clear()
        history.add_messages(keep)


def with_redis_history(chain) -> Callable[[dict, dict], str]:
    """Wrap a Runnable (prompt | model | parser) with Redis-backed message history."""
    return RunnableWithMessageHistory(
        chain,
        # history factory gets session_id from config
        lambda session_id: make_history(session_id),
        input_messages_key="query",
        history_messages_key="chat_history",
    )