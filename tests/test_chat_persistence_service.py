import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from services import chat_persistence_service


def _make_db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(128) NOT NULL,
                    session_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    last_message_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    CONSTRAINT uq_chat_sessions_user_session UNIQUE (user_id, session_id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_session_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    FOREIGN KEY(chat_session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
                """
            )
        )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return session_local()


def test_derive_chat_title_truncates_to_50_chars():
    query = "a" * 80
    title = chat_persistence_service.derive_chat_title(query)
    assert len(title) == 50
    assert title == "a" * 50


def test_extract_answer_text_removes_references_block():
    raw = "Answer body\n\n\n[REFERENCES]\n\n\n[{\"author\":\"x\"}]"
    cleaned = chat_persistence_service.extract_answer_text(raw)
    assert cleaned == "Answer body"


def test_extract_answer_text_from_agentic_sse_stream():
    raw = (
        'event: status\n'
        'data: {"step":"agent","message":"Agent thinking..."}\n\n'
        'event: response_chunk\n'
        'data: {"token":"Patience"}\n\n'
        'event: response_chunk\n'
        'data: {"token":" in Islam"}\n\n'
        'event: response_chunk\n'
        'data: {"token":" is steadfastness."}\n\n'
        'event: response_end\n'
        'data: {}\n\n'
        'event: hadith_references\n'
        'data: {"references":[{"reference":"x"}]}\n\n'
        'event: done\n'
        'data: {}\n\n'
    )
    cleaned = chat_persistence_service.extract_answer_text(raw)
    assert cleaned == "Patience in Islam is steadfastness."


def test_extract_answer_text_from_agentic_sse_early_exit():
    raw = (
        'event: response_chunk\n'
        'data: {"token":"Please consult a qualified scholar."}\n\n'
        'event: response_end\n'
        'data: {}\n\n'
        'event: done\n'
        'data: {}\n\n'
    )
    cleaned = chat_persistence_service.extract_answer_text(raw)
    assert cleaned == "Please consult a qualified scholar."


def test_extract_answer_text_from_agentic_sse_with_error_only_returns_empty():
    raw = (
        'event: status\n'
        'data: {"step":"agent","message":"Agent thinking..."}\n\n'
        'event: error\n'
        'data: {"message":"No response generated."}\n\n'
        'event: done\n'
        'data: {}\n\n'
    )
    cleaned = chat_persistence_service.extract_answer_text(raw)
    assert cleaned == ""


def test_persist_and_query_saved_chat():
    db = _make_db_session()

    chat_persistence_service.persist_user_message(
        db,
        user_id="user-1",
        session_id="thread-1",
        user_query="What is tawhid?",
    )
    chat_persistence_service.persist_assistant_message(
        db,
        user_id="user-1",
        session_id="thread-1",
        assistant_text="Tawhid means the oneness of Allah.",
    )

    items, total = chat_persistence_service.list_sessions(
        db,
        user_id="user-1",
        limit=20,
        offset=0,
    )
    assert total == 1
    assert len(items) == 1
    assert items[0]["session_id"] == "thread-1"
    assert items[0]["title"] == "What is tawhid?"
    assert items[0]["message_count"] == 2

    detail = chat_persistence_service.get_session_with_messages(
        db,
        user_id="user-1",
        session_id="thread-1",
        limit=100,
        offset=0,
    )
    assert detail is not None
    assert detail["session_id"] == "thread-1"
    assert detail["total_messages"] == 2
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]


async def _collect_streaming_response(response: StreamingResponse) -> str:
    chunks = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8")
        chunks.append(chunk)
    return "".join(chunks)


def test_wrap_streaming_response_for_persistence_saves_only_agentic_answer_text():
    db = _make_db_session()
    chat_persistence_service.persist_user_message(
        db,
        user_id="user-1",
        session_id="thread-2",
        user_query="Tell me about patience",
    )

    async def body():
        yield 'event: status\ndata: {"step":"agent","message":"Agent thinking..."}\n\n'
        yield 'event: response_chunk\ndata: {"token":"Patience"}\n\n'
        yield 'event: response_chunk\ndata: {"token":" is beautiful."}\n\n'
        yield 'event: response_end\ndata: {}\n\n'
        yield 'event: done\ndata: {}\n\n'

    callback_values = []
    response = StreamingResponse(body(), media_type="text/event-stream")
    wrapped = chat_persistence_service.wrap_streaming_response_for_persistence(
        response=response,
        db=db,
        user_id="user-1",
        session_id="thread-2",
        on_assistant_message_saved=callback_values.append,
    )

    streamed = asyncio.run(_collect_streaming_response(wrapped))
    assert 'event: response_chunk' in streamed

    detail = chat_persistence_service.get_session_with_messages(
        db,
        user_id="user-1",
        session_id="thread-2",
        limit=100,
        offset=0,
    )
    assert detail is not None
    assert detail["messages"][-1]["role"] == "assistant"
    assert detail["messages"][-1]["content"] == "Patience is beautiful."
    assert callback_values == ["Patience is beautiful."]


def test_wrap_streaming_response_for_persistence_saves_partial_agentic_answer_on_error():
    db = _make_db_session()
    chat_persistence_service.persist_user_message(
        db,
        user_id="user-1",
        session_id="thread-3",
        user_query="Tell me about patience",
    )

    async def body():
        yield 'event: status\ndata: {"step":"agent","message":"Agent thinking..."}\n\n'
        yield 'event: response_chunk\ndata: {"token":"Partial"}\n\n'
        yield 'event: response_chunk\ndata: {"token":" answer"}\n\n'
        raise RuntimeError("stream interrupted")

    response = StreamingResponse(body(), media_type="text/event-stream")
    wrapped = chat_persistence_service.wrap_streaming_response_for_persistence(
        response=response,
        db=db,
        user_id="user-1",
        session_id="thread-3",
    )

    try:
        asyncio.run(_collect_streaming_response(wrapped))
        assert False, "Expected stream interruption"
    except RuntimeError as exc:
        assert str(exc) == "stream interrupted"

    detail = chat_persistence_service.get_session_with_messages(
        db,
        user_id="user-1",
        session_id="thread-3",
        limit=100,
        offset=0,
    )
    assert detail is not None
    assert detail["messages"][-1]["content"] == "Partial answer"
