# Coding Conventions
_Last updated: 2026-03-22_

## Summary

This is a Python FastAPI backend for an Islamic education platform. Naming follows standard Python community conventions (`snake_case` for functions/variables, `PascalCase` for classes), with type hints used consistently in service and CRUD layers but inconsistently in older modules. Error handling varies by layer: API routes use `HTTPException`, service methods raise `ValueError`/`LookupError`, and low-level modules often silently swallow exceptions and return empty results.

---

## Naming Patterns

**Files and modules:**
- All lowercase with underscores: `chat_persistence_service.py`, `pipeline_langgraph.py`, `hikmah_quiz_service.py`
- Module directories use short lowercase names: `api/`, `agents/`, `core/`, `modules/`, `services/`, `db/`
- One exception: `models/JWTBearer.py` uses PascalCase (class-name-as-filename)

**Classes:**
- `PascalCase` throughout: `ChatAgent`, `HikmahQuizService`, `PrimerService`, `CRUDBase`, `ExtraFormatter`, `JWTBearer`
- SQLAlchemy models follow this: `User`, `ChatSession`, `ChatMessage`, `LessonPageQuizQuestion`

**Functions and methods:**
- `snake_case` for all functions: `generate_response`, `retrieve_shia_documents`, `build_runtime_session_id`
- Private helpers prefixed with underscore: `_extract_user_id`, `_require_user_id`, `_looks_like_sse_stream`, `_extract_agentic_sse_answer_text`, `_make_db_session`, `_build_graph`
- LangGraph tool names are descriptive verb phrases: `enhance_query_tool`, `retrieve_shia_documents_tool`, `check_if_non_islamic_tool`

**Variables:**
- `snake_case`: `user_query`, `session_id`, `target_language`, `runtime_session_id`
- Module-level constants use `UPPER_SNAKE_CASE`: `OPENAI_API_KEY`, `REDIS_URL`, `REFERENCES_MARKER`, `DEFAULT_FORMAT`, `MAX_MESSAGES`

**SQLAlchemy model columns:**
- `snake_case` matching the database column name: `created_at`, `updated_at`, `is_active`, `display_name`

---

## Code Style

**Formatting:**
- No enforced formatter detected (no `.prettierrc`, `.flake8`, `pyproject.toml`, or `ruff.toml` in project root)
- Indentation is 4 spaces consistently
- Line length is not strictly enforced; some lines in `modules/generation/stream_generator.py` exceed 100 chars

**Imports:**
- Standard library imports first, then third-party, then local — this order is followed in well-maintained files (e.g., `services/chat_persistence_service.py`, `agents/core/chat_agent.py`) but not everywhere
- Local path manipulation with `sys.path.insert(0, ...)` appears at the top of test files to allow running them as scripts:
  ```python
  sys.path.insert(0, str(Path(__file__).parent.parent))
  ```
- `from __future__ import annotations` used in `services/chat_persistence_service.py` for forward references

---

## Type Annotations

**Where used:**
- All functions in `services/` layer carry type hints: return types, parameter types
- `db/crud/base.py` uses `Generic[ModelType, ...]` with `TypeVar`
- `agents/` layer: function signatures in `chat_agent.py` and tools are fully typed
- `core/chat_persistence_service.py`: fully annotated including `Optional`, `List`, `Dict`, `Callable`, `AsyncIterator`

**Where missing or inconsistent:**
- `modules/retrieval/retriever.py`: `retrieve_documents(query, no_of_docs=10)` — no type hints
- `modules/embedding/embedder.py`: `getSparseEmbedder()` — no type hints, non-snake-case name
- `modules/generation/generator.py`: `generate_response(query: str, retrieved_docs: list)` — `list` not parameterized
- `modules/reranking/reranker.py`: `rerank_documents(dense_results, sparse_results, no_of_docs)` — no types

**Rule:** Add type hints to all new or changed functions. Annotate parameters and return values using `typing` module types (`List[str]`, `Dict[str, Any]`, `Optional[str]`).

---

## Error Handling Patterns

**API layer (`api/`):**
- Catch all exceptions in route handlers and raise `HTTPException`:
  ```python
  except Exception as e:
      print("UNHANDLED ERROR in /chat/stream/agentic:", e)
      traceback.print_exc()
      raise HTTPException(status_code=500, detail="Internal Server Error")
  ```
- Generic 500 error message intentional — no internal details leaked to client
- Input validation raises `HTTPException(status_code=400, ...)` directly (not from Pydantic)
- `traceback` is imported and used in `api/chat.py`; not all routes use it uniformly

**Service layer (`services/`):**
- Raise domain-appropriate errors: `ValueError` for invalid inputs, `LookupError` for not-found resources
- Example from `services/hikmah_quiz_service.py`: `raise LookupError(f"LessonContent {lesson_content_id} not found")`
- Example: `raise ValueError("Exactly one choice must be marked as correct")`
- Wrap DB operations in `try/except` and log errors before re-raising or returning fallback

**Module/tool layer (`modules/`, `agents/tools/`):**
- Tools return error payloads instead of raising — callers check for `"error"` key in result:
  ```python
  except Exception as e:
      print(f"[retrieve_shia_documents_tool] Error: {e}")
      return {"documents": [], "count": 0, "source": "shia", "error": str(e), ...}
  ```
- This keeps the LangGraph graph running even when individual tools fail

**Global middleware (`main.py`):**
- A catch-all HTTP middleware logs the traceback and returns a generic JSON 500:
  ```python
  @app.middleware("http")
  async def catch_exceptions_mw(request: Request, call_next):
      try:
          return await call_next(request)
      except Exception as e:
          tb = traceback.format_exc()
          print("===== SERVER EXCEPTION =====", tb)
          return JSONResponse(status_code=500, content={"detail": "internal_error", "error": str(e)})
  ```

---

## Logging Conventions

**Setup:**
- Centralized in `core/logging_config.py` via `setup_logging()` and `get_memory_logger()`
- Format: `%(asctime)s [%(levelname)s] %(name)s - %(message)s` with colorized level names
- Extra dict keys on log records appended as `key=value` pairs by `ExtraFormatter`
- Noisy libraries silenced: `sqlalchemy.engine`, `sqlalchemy.pool`, `httpx` set to `WARNING`

**Logger acquisition — preferred pattern:**
```python
import logging
logger = logging.getLogger(__name__)
```
Used in: `services/hikmah_quiz_service.py`, `services/account_service.py`, `services/embedding_service.py`, `services/primer_service.py`

**`print()` usage (not preferred):**
- Used in `api/chat.py`, `agents/tools/retrieval_tools.py`, `modules/generation/generator.py`, and scattered throughout older code
- `print()` calls with `[CONTEXT]`-style prefixes appear in tools: `print(f"[retrieve_shia_documents_tool] Error: {e}")`
- Rule: Prefer `logger.*` over `print()` in new code

---

## Module Design and Pydantic Schemas

**Pydantic models used for:**
- API request/response schemas in `models/schemas.py`: `ChatRequest`, `ElaborationRequest`, `PersonalizedPrimerResponse`, `QuizQuestionCreateRequest`
- DB schemas in `db/schemas/`: `lessons.py`, `users.py`, `user_progress.py`, `personalized_primers.py`
- `model_validator(mode="after")` used for cross-field validation in `QuizQuestionCreateRequest`

**SQLAlchemy models:**
- Inherit from `Base` imported from `db/session.py`
- `__tablename__` always defined as a plain string
- Timestamps use `TIMESTAMP(timezone=True)` with `server_default=func.now()`

**Repository pattern:**
- `db/crud/base.py` provides generic `CRUDBase[ModelType, CreateSchema, UpdateSchema]`
- Specialized CRUD classes in `db/crud/` extend it: `db/crud/lessons.py`, `db/crud/users.py`, etc.

**Service class pattern:**
```python
class HikmahQuizService:
    def __init__(self, db: Session):
        self.db = db
```
Services accept a SQLAlchemy `Session` injected at construction.

---

## Common Patterns

**FastAPI router setup:**
```python
chat_router = APIRouter(prefix="/chat", tags=["chat"])
```
All routers use `prefix` and `tags`.

**Dependency injection:**
```python
db: Session = Depends(get_db)
credentials: Optional[JWTAuthorizationCredentials] = Depends(optional_auth)
```
`get_db` from `db/session.py` yields a session per request.

**SSE streaming:**
- Streaming responses use `fastapi.responses.StreamingResponse` with `media_type="text/event-stream"`
- SSE format: `event: <name>\ndata: <json>\n\n`
- Events emitted: `status`, `response_chunk`, `response_end`, `hadith_references`, `quran_references`, `done`, `error`

**LangGraph tool decoration:**
```python
from langchain_core.tools import tool

@tool
def retrieve_shia_documents_tool(query: str, num_documents: int = 5) -> Dict[str, any]:
    """Docstring used by LLM as tool description."""
```
Tool docstrings are consumed by the LLM — keep them detailed and accurate.

**`sys.path.insert` in tests:**
All test files in `tests/` and `agent_tests/` manually insert the project root onto `sys.path` to allow direct script execution without package installation.
