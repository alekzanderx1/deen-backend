from core.memory import make_history, trim_history

def get_recent_context(session_id: str, max_messages: int = 6) -> str:
    """
    Pulls the last N turns from Redis (or ephemeral fallback) and returns
    them as a compact string for classifier context.
    """
    history = make_history(session_id)
    msgs = history.messages[-max_messages:]  # last N messages

    parts = []
    for m in msgs:
        role = getattr(m, "type", getattr(m, "role", "user"))
        parts.append(f"{role}: {m.content}")
    return "\n".join(parts)