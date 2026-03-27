# Repository Guidelines

## Project Structure & Module Organization
This FastAPI backend is organized by responsibility:
- `api/`: HTTP route handlers (`chat`, `reference`, `hikmah`, `primers`, account/admin endpoints).
- `core/`: shared pipeline logic, config, auth, logging, memory/vector utilities, and `pipeline_langgraph.py`.
- `modules/`: AI pipeline stages (classification, embedding, retrieval, reranking, generation, translation).
- `agents/`: agent orchestration (`core/`), tool wrappers (`tools/`), runtime state (`state/`), prompts, and configuration (`config/`).
- `db/`: SQLAlchemy models, Pydantic schemas, repositories/CRUD, routers, and session setup.
- `services/`: business services used by routes and agents.
- `alembic/`: migration scripts.
- `tests/` + `tests/db/`: pytest suites.
- `agent_tests/`: integration/debug scripts.

## Build, Test, and Development Commands
- `python3 -m venv venv && source venv/bin/activate`: create and activate local env.
- `pip install -r requirements.txt`: install dependencies.
- `alembic upgrade head`: apply DB migrations.
- `uvicorn main:app --reload`: run API locally at `http://127.0.0.1:8000`.
- `pytest tests -q`: run primary test suite.
- `pytest tests/db -q`: run DB compatibility checks (requires `DATABASE_URL`).
- `python agent_tests/test_memory_agent.py`: run memory-agent integration script.
- `docker compose build --no-cache && docker compose up -d`: run containerized stack.
- `curl -X POST http://127.0.0.1:8000/chat/stream/agentic ...`: verify the agentic endpoint.

## Coding Style & Naming Conventions
- Follow existing Python style: 4-space indentation, PEP 8 spacing, and concise docstrings for non-trivial logic.
- Add type hints to new/changed functions (required by existing project guidance).
- Naming: `snake_case` for modules/functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Keep route modules thin; move reusable logic into `services/`, `core/`, or `modules/`.

## Testing Guidelines
- Framework: `pytest` with `pytest-asyncio` for async behavior.
- Test files should be named `test_*.py`; group fixtures close to the tests that use them.
- Prefer mock-based unit tests in `tests/`; reserve `tests/db` and `agent_tests` for environment-dependent integration coverage.
- For new agentic behavior, add tests around tool-selection outcomes and early-exit behavior (`non_islamic`, `fiqh`) where possible.

## Commit & Pull Request Guidelines
- Match repo history: short, imperative commit subjects (e.g., `feat: add primer cache invalidation` or `Added DB logging for memory admin`).
- Keep commits focused by concern (API, DB migration, service logic, docs).
- PRs should include: purpose, impacted paths/endpoints (especially `/chat/stream/agentic` or `/chat/agentic` changes), migration notes (`alembic/versions/...`), env var changes, and test evidence (commands + results).

## Security & Configuration Tips
- Never commit secrets; keep `.env` local.
- Validate CORS, Cognito, Redis, Pinecone, and OpenAI settings before running integration tests or deploy commands.
