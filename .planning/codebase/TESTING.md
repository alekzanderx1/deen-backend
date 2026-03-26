# Testing
_Last updated: 2026-03-22_

## Summary

The project uses `pytest` with `pytest-asyncio` as its primary test suite, organized across three test locations with clearly separated concerns: mock-based unit/integration tests in `tests/`, live-database schema checks in `tests/db/`, and environment-dependent integration scripts in `agent_tests/`. Most production-path logic in `tests/` is fully mocked against external services (OpenAI, Redis, Pinecone), relying on in-memory SQLite and `monkeypatch`/`unittest.mock` for isolation. The `agent_tests/` directory consists of executable scripts that hit real infrastructure and are not part of the standard `pytest` run.

---

## Test Framework & Config

**Runner:** `pytest` 8.4.1

**Async support:** `pytest-asyncio` 0.26.0
- Async tests use `@pytest.mark.asyncio` per-test decoration (no global `asyncio_mode = auto`).
- `test_agentic_streaming_sse.py` applies the marker conditionally via a helper `_maybe_mark_asyncio()` wrapper to allow the file to also run as a plain `python` script.
- Async pipeline tests in `test_agentic_streaming_pipeline.py` use `asyncio.run()` directly inside synchronous `def test_*` functions rather than marking them `async`.

**Additional pytest plugins installed** (from `requirements.txt`):
- `pytest-benchmark==5.1.0`
- `pytest-codspeed==3.2.0`
- `pytest-recording==0.13.4`
- `pytest-socket==0.7.0`

**Configuration files:** None. No `pytest.ini`, `setup.cfg`, or `pyproject.toml` is present. Pytest runs with default settings from the project root.

---

## Directory Structure

```
deen-backend/
├── tests/
│   ├── test_agentic_streaming_pipeline.py   # Unit tests: LangGraph agent & pipeline logic (monkeypatched)
│   ├── test_agentic_streaming_sse.py        # Integration test: SSE event parsing; also a standalone script
│   ├── test_chat_persistence_service.py     # Unit/integration: chat persistence with in-memory SQLite
│   ├── test_embedding_service.py            # Unit tests: EmbeddingService with mocked OpenAI
│   ├── test_hikmah_quiz_service.py          # Unit tests: HikmahQuizService with mocked DB
│   ├── test_primer_service.py               # Unit/integration: PrimerService with mocked DB & LLM
│   └── db/
│       ├── test_baseline_primers_compatibility.py   # Schema check: requires live DATABASE_URL
│       └── test_db_premiers_table.py                # DB exploration script (not a proper test suite)
├── agent_tests/
│   ├── test_memory_agent.py                 # Live integration: MemoryAgent against real DB + LLM
│   ├── test_consolidation.py                # Live integration: memory consolidation pipeline
│   ├── test_consolidation_debug.py          # Debug script
│   ├── test_db_connection.py                # Live integration: DB connectivity check
│   ├── test_hikmah_memory_integration.py    # Live integration: Hikmah + memory interaction
│   ├── test_realistic_memory.py             # Live integration: realistic memory workloads
│   ├── test_threading_hikmah.py             # Live integration: threading behavior
│   ├── test_universal_debug.py              # Debug script
│   └── test_universal_memory.py             # Live integration: universal memory flows
└── db/
    └── test_user_progress_api.py            # API-level integration test using FastAPI TestClient
```

---

## Test Types & Coverage

### Unit Tests (`tests/`)

**`tests/test_agentic_streaming_pipeline.py`**
- Tests `ChatAgent` internal methods: `_apply_tool_call_defaults`, `_record_retrieval_result`, `_should_continue`.
- Tests `core/pipeline_langgraph.py` streaming pipeline behavior: normal completion, early exit, Quran retrieval errors.
- Uses `monkeypatch` to replace `ChatAgent`, `core.memory.make_history`, `core.chat_models.get_generator_model`, and `services.chat_persistence_service.append_turn_to_runtime_history` with inline fake classes.
- All tests are synchronous `def test_*` functions that call `asyncio.run()` for async pipeline invocations.

**`tests/test_embedding_service.py`**
- Covers `services/embedding_service.py`: content hashing, single/batch embedding generation, note/lesson chunk storage, existence checks, similarity search, signal quality calculation, delete operations.
- Uses `pytest` fixtures with `unittest.mock.Mock`, `MagicMock`, and `unittest.mock.patch` to mock the SQLAlchemy `Session` and the `OpenAI` client.
- Grouped into test classes: `TestContentHashing`, `TestEmbeddingGeneration`, `TestNoteEmbeddingStorage`, `TestLessonChunkEmbeddingStorage`, `TestEmbeddingExistenceChecks`, `TestSimilaritySearch`, `TestSignalQualityCalculation`, `TestBatchOperations`, `TestDeleteOperations`.

**`tests/test_hikmah_quiz_service.py`**
- Covers `services/hikmah_quiz_service.py`: learner-facing question fetching, admin CRUD (create, list, replace, patch, delete), quiz submission processing, and memory trigger behavior.
- Uses `unittest.mock.Mock` and `types.SimpleNamespace` for lightweight DB object construction. A `_build_query()` helper returns a chained mock query.
- Uses `monkeypatch` for `asyncio.run` interception and method patching on the service instance.
- No pytest fixtures — all setup is inline per function.

**`tests/test_primer_service.py`**
- Covers `services/primer_service.py`: note tag filtering, signal quality scoring, LLM response parsing, user signal fetching (tag-based and embedding-based), similarity quality assessment, and cache behavior.
- Uses `pytest` fixtures for `mock_db`, `mock_embedding_service`, `primer_service`, `sample_lesson`, `sample_user_profile`, `sample_user_signals`.
- Mocks `EmbeddingService` via `patch` at construction time; mocks `lesson_crud`, `small_llm`, and cache methods via `patch.object` and `patch`.
- Async generation flow tests use `@pytest.mark.asyncio` inside a `TestGenerationFlow` class.

**`tests/test_chat_persistence_service.py`**
- Covers `services/chat_persistence_service.py`: title derivation, SSE stream parsing, message persistence, session listing, streaming response wrapping (success and error paths).
- Uses a real in-memory SQLite database (created via `sqlite+pysqlite:///:memory:`) with manually executed DDL — no mocking of the DB layer.
- Tests SSE stream parsing by constructing raw SSE strings inline.

### SSE Integration Test (`tests/test_agentic_streaming_sse.py`)

- Exercises the full `core/pipeline_langgraph.py` agentic streaming pipeline end-to-end, including SSE event parsing and markdown reconstruction.
- Requires all environment variables (OpenAI, Redis, Pinecone) to be present — **not suitable for CI without those secrets**.
- Can be run two ways:
  - `pytest tests/test_agentic_streaming_sse.py -v -s` (via pytest with `tmp_path` fixture)
  - `python tests/test_agentic_streaming_sse.py` (standalone, writes to a temp file; supports `AGENTIC_TEST_QUERY`, `AGENTIC_TEST_SESSION`, `AGENTIC_TEST_OUTPUT` env overrides)

### DB Schema Tests (`tests/db/`)

- `test_baseline_primers_compatibility.py`: Connects to the real Postgres database (`DATABASE_URL` with `sslmode=require`) and asserts that `lessons` table has the correct new columns (`baseline_primer_bullets`, `baseline_primer_glossary`, `baseline_primer_updated_at`) with correct nullability.
- `test_db_premiers_table.py`: An exploratory DB inspection script. Runs DDL queries at module load time (not inside test functions). Functions as documentation / schema exploration rather than a proper assertion-based test.

### Live Integration Scripts (`agent_tests/`)

- All files are standalone Python scripts using `asyncio.run()` and `if __name__ == "__main__"`. They are **not pytest-compatible** and are not included in `pytest tests -q`.
- Require live DB, Redis, and OpenAI credentials.
- Run manually: `python agent_tests/test_memory_agent.py`
- Cover: `MemoryAgent.analyze_chat_interaction`, memory consolidation logic, Hikmah memory integration, threading behavior under concurrent requests, DB connectivity.

### API Integration Test (`db/test_user_progress_api.py`)

- Located outside `tests/` in the `db/` directory. Uses FastAPI's `TestClient` wrapping `main:app`.
- Requires a live database connection (hits real DB via the app's session).
- Run with: `pytest db/test_user_progress_api.py`

---

## Running Tests

```bash
# Primary test suite (no live DB or external services required)
pytest tests -q

# DB compatibility tests (requires DATABASE_URL env var pointing to live Postgres)
pytest tests/db -q

# SSE streaming integration test (requires all external service env vars)
pytest tests/test_agentic_streaming_sse.py -v -s

# Memory agent integration (standalone script, not pytest)
python agent_tests/test_memory_agent.py

# API integration test (requires live DB)
pytest db/test_user_progress_api.py
```

---

## Patterns & Fixtures

### Fixture Pattern (pytest-style, `test_embedding_service.py`, `test_primer_service.py`)

```python
@pytest.fixture
def mock_db():
    db = Mock(spec=Session)
    db.query = Mock(return_value=Mock())
    db.add = Mock()
    db.commit = Mock()
    return db

@pytest.fixture
def mock_openai_client():
    with patch('services.embedding_service.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_embedding_data = Mock()
        mock_embedding_data.embedding = [0.1] * 1536
        mock_openai.return_value = mock_client
        mock_client.embeddings.create.return_value.data = [mock_embedding_data]
        yield mock_client

@pytest.fixture
def embedding_service(mock_db, mock_openai_client):
    with patch('services.embedding_service.OpenAI') as mock_openai:
        mock_openai.return_value = mock_openai_client
        service = EmbeddingService(mock_db)
        service.client = mock_openai_client
        return service
```

### Monkeypatch Pattern (pipeline tests, `test_agentic_streaming_pipeline.py`)

Used to replace entire modules/classes with fake implementations:

```python
def test_streaming_pipeline_uses_runtime_history_and_appends_once(monkeypatch):
    class FakeAgent:
        def __init__(self, config): self.config = config
        async def astream(self, **kwargs):
            yield {"agent": {"messages": [], "runtime_session_id": "runtime-key", ...}}

    monkeypatch.setattr(pipeline_langgraph, "ChatAgent", FakeAgent)
    monkeypatch.setattr("core.memory.make_history", fake_make_history)
    monkeypatch.setattr("core.chat_models.get_generator_model", lambda: RunnableLambda(fake_model_fn))
    monkeypatch.setattr("services.chat_persistence_service.append_turn_to_runtime_history", ...)

    output = asyncio.run(_run())
    assert 'event: response_chunk' in output
```

### In-Memory SQLite Pattern (`test_chat_persistence_service.py`)

```python
def _make_db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE chat_sessions (...)"))
        conn.execute(text("CREATE TABLE chat_messages (...)"))
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return session_local()
```

### Mock Query Builder Pattern (`test_hikmah_quiz_service.py`)

```python
def _build_query(result=None, first_result=None):
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.all.return_value = result if result is not None else []
    query.first.return_value = first_result
    query.delete.return_value = 1
    return query

# Usage:
db.query.side_effect = [
    _build_query(result=[question]),
    _build_query(result=[choice_a, choice_b]),
]
```

### Async Test Pattern

Tests calling async code are run via `asyncio.run()` inside synchronous test functions (the prevalent pattern), not by marking the test as `async`:

```python
def test_streaming_pipeline_early_exit_appends_once(monkeypatch):
    # ... setup ...
    async def _run():
        response = await pipeline_langgraph.chat_pipeline_streaming_agentic(...)
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk)
        return "".join(chunks)

    output = asyncio.run(_run())
    assert "Please consult a qualified scholar." in output
```

`@pytest.mark.asyncio` is used only in `test_primer_service.py` (`TestGenerationFlow`) and conditionally in `test_agentic_streaming_sse.py`.

### What Gets Mocked

- `ChatAgent` and its LLM (`_create_llm_with_tools`) — always replaced with a `_FakeLLM` or `FakeAgent`
- `core.memory.make_history` — replaced with a fake returning in-memory message lists
- `core.chat_models.get_generator_model` — replaced with a `RunnableLambda`
- `services.chat_persistence_service.append_turn_to_runtime_history` — replaced with a list appender
- `OpenAI` client — patched at import path (`services.embedding_service.OpenAI`)
- SQLAlchemy `Session` — `Mock(spec=Session)` or real in-memory SQLite
- `modules.retrieval.retriever.retrieve_quran_documents` — patched to raise errors for error-path tests

### What Is NOT Mocked

- SQLite in-memory DB in `test_chat_persistence_service.py` — real SQL DDL and ORM operations run against it
- `services/chat_persistence_service.py` internal functions (title derivation, SSE parsing) — tested directly without mocking

---

## Gaps & Missing Coverage

**No test coverage for:**

- `api/` route handlers — no HTTP-level tests for the primary endpoints (`/chat/stream/agentic`, `/chat/agentic`, `/references`, `/hikmah/elaborate`, `/primers`, `/admin/memory`). The only API test (`db/test_user_progress_api.py`) is for a secondary CRUD endpoint and requires a live DB.
- `core/auth.py` — JWT/Cognito validation logic is entirely untested.
- `core/vectorstore.py` — Pinecone initialization is untested.
- `modules/` pipeline stages — classification, embedding generation, retrieval, reranking, and generation modules have no unit tests.
- `agents/core/memory_agent.py` — only covered by live integration scripts in `agent_tests/`, not by mock-based tests.
- `services/consolidation_service.py` and `services/memory_service.py` — covered only by live `agent_tests/` scripts.
- LangGraph graph structure and node wiring in `core/pipeline_langgraph.py` — pipeline behavior is tested via fake agents, but the actual graph topology (node connections, edges, conditional routing) is not directly tested.
- Translation/enhancement module in `modules/` — no tests found.
- `db/` routers and repositories — CRUD endpoints beyond user-progress are untested.

**Structural concerns:**

- `tests/db/test_db_premiers_table.py` executes SQL at module import time (not inside test functions), which causes it to fail immediately if `DATABASE_URL` is not set, even when it is not the target of a test run. It should be refactored to use `pytest.skip` or require the env var only inside test functions.
- No `conftest.py` exists anywhere, so shared fixtures (mock DB sessions, OpenAI mocks) are duplicated across `test_embedding_service.py` and `test_primer_service.py`.
- No coverage reporting is configured (no `--cov` setup or `.coveragerc`), so coverage levels are unknown.
- `pytest-socket`, `pytest-recording`, and `pytest-benchmark` are installed but no tests use them, suggesting planned but unimplemented network isolation and performance benchmarking.
