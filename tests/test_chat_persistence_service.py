import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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
