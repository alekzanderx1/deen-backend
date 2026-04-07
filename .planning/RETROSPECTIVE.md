# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Fiqh Agentic RAG MVP

**Shipped:** 2026-03-25
**Phases:** 4 | **Plans:** 12 | **Commits:** 78 (2026-03-23 → 2026-03-25)

### What Was Built

- **Ingestion pipeline:** PyMuPDF-based PDF parsing, ruling-boundary chunking (3000 chunks from 2796 Sistani rulings), BM25 sparse + dense embedding, dual Pinecone upsert
- **FAIR-RAG modules:** 6-category classifier, query decomposer, hybrid RRF retriever, evidence filter, SEA (structured evidence assessment), query refiner, answer generator — all unit-tested with mocked LLM
- **Coordinator + sub-graph:** Pure Python FAIR-RAG coordinator (max-3-iteration loop) wrapped in a LangGraph sub-graph invoked by the main ChatAgent, with session isolation via `checkpointer=False`
- **SSE integration:** Fiqh path detection in `pipeline_langgraph.py` with pre-canned status events, token-by-token streaming, and `fiqh_references` SSE event
- **39 requirements satisfied, 5 E2E flows verified, 0 blockers at ship**

### What Worked

- **Phased isolation:** Building modules in isolation (Phase 3) with mocked LLM tests before wiring (Phase 4) caught interface issues early without needing live infra
- **Sub-graph composition:** LangGraph `checkpointer=False` pattern cleanly solved the session isolation requirement without custom state management
- **Dynamic LLM allocation pattern:** Routing gpt-4o-mini for classification/SEA and gpt-4.1 for generation/refinement kept costs low while maintaining quality
- **BM25 JSON serialization:** Persisting BM25 encoder to `data/fiqh_bm25_encoder.json` (not pickle) made it portable across ingestion and query-time environments
- **Fails-open evidence filtering:** Returning all docs when the filter LLM returns an empty list prevented silent context loss

### What Was Inefficient

- **ROADMAP.md progress table went stale:** Phase 2 showed "Not started" and Phase 3 showed "In Progress" at archive time despite all work being complete — the progress table needs updating at each plan completion, not just at phase start
- **Pre-canned SSE status events:** The decision to emit pre-canned `fiqh_refine` events (instead of reading live `FiqhState.status_events`) deferred a real UX accuracy problem to tech debt; the clean solution existed but was skipped for speed
- **Phase 02-01/02-02 SUMMARY.md missing one_liner field:** Two summary files lacked the `one_liner` frontmatter field, causing "One-liner:" placeholders to appear in MILESTONES.md from the CLI tool

### Patterns Established

- **Wrapper node pattern:** `_call_fiqh_subgraph_node` projects `ChatState → FiqhState → ChatState` without sharing keys between schemas — clean interface for sub-graph composition
- **Fails-open for LLM tools:** When LLM output is ambiguous or empty, return all input docs rather than filtering aggressively — better to over-include than silently drop evidence
- **No module-level env var guards for optional features:** Guard inside the function/script, not at import time, to avoid breaking server startup for developers without fiqh indexes configured
- **Mock-first unit tests for pipeline modules:** All FAIR-RAG modules have `unittest.mock.patch` tests that run without LLM or Pinecone — enables fast CI and clear interface contracts

### Key Lessons

1. **Sub-graph state isolation requires explicit design:** LangGraph's MemorySaver checkpointer persists across invocations by default — always set `checkpointer=False` for sub-graphs that must be stateless per request
2. **Chunk count from research papers may not match your PDF:** Expected 1000–1600 chunks per FAIR-RAG paper assumptions; actual PDF produced 3000 chunks (2796 unique rulings). Always verify before committing to index sizing
3. **The "One-liner" frontmatter field in SUMMARY.md is load-bearing:** The milestone CLI depends on it; files missing this field silently produce placeholder text in MILESTONES.md
4. **ROADMAP.md progress table requires active maintenance:** It's not auto-updated by gsd-tools — mark phases complete in the table at the end of each plan execution, not just at phase start

### Cost Observations

- Model mix: Sonnet 4.6 (primary executor across all phases)
- Sessions: ~78 commits over 2 days
- Notable: Dynamic LLM allocation (gpt-4o-mini for 60%+ of inference steps) achieved research-validated 13% cost savings vs all-large allocation; fast iteration over 2 days suggests good session continuity

---

## Milestone: v1.1 — Supabase Migration

**Shipped:** 2026-04-07
**Phases:** 3 | **Plans:** 6 | **Commits:** ~30 (2026-04-06 → 2026-04-07)

### What Was Built

- **Database migration:** Supabase Postgres provisioned; genesis Alembic migration created to support fresh-DB provisioning; all 13 tables + pgvector HNSW index verified; app connects via SQLAlchemy with zero code changes
- **Auth migration:** JWKS fetch URL updated from Cognito to `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`; Cognito env vars removed; account deletion replaced with httpx Supabase Admin API call; all routes protected with strict auth + ENV=development bypass
- **Cleanup:** boto3 fully removed from requirements.txt and api/account.py; `.env.example` created with 28 vars grouped by service; README `## Environment Variables` section added with v1.0→v1.1 migration callout

### What Worked

- **Clear phase boundaries:** Keeping auth changes in Phase 6 and boto3 removal in Phase 7 prevented scope creep and made each phase independently verifiable
- **Genesis migration pattern:** Creating `0000_initial_schema.py` as a separate foundational migration (rather than hacking existing migrations) kept the Alembic chain clean and idempotent — `alembic upgrade head` on any fresh DB now just works
- **Research catching subtle issues:** Phase 7 researcher identified the botocore import line that CONTEXT.md missed — both lines got removed cleanly
- **Plan checker catching gaps:** Checker caught 4 missing env vars in .env.example template before execution — saved a re-run

### What Was Inefficient

- **Requirements checkboxes not updated during execution:** DB-01, DB-02, DB-03, AUTH-01, AUTH-02 remained unchecked at milestone close despite the code being complete; checkbox maintenance needs to happen at plan completion, not retroactively
- **Phase 5 was purely manual (infra provisioning):** The GSD execution flow doesn't map cleanly to "go click in a dashboard" tasks — Phase 5 plans were more of a checklist than executable code tasks

### Patterns Established

- **Genesis migration for legacy codebases:** When adopting Alembic on a codebase with pre-existing tables, always create a `0000_initial_schema.py` genesis migration before running against any fresh database
- **Direct port 5432 over pooler:** asyncpg + Supabase transaction pooler (6543) are incompatible — always use direct connection for both sync and async SQLAlchemy engines
- **.env.example as the deployment contract:** A well-structured `.env.example` grouped by service (OpenAI, Pinecone, Supabase, Redis, App) eliminates all "what env vars do I need?" onboarding friction

### Key Lessons

1. **Alembic chain must be validated on a fresh DB before any migration milestone ships** — testing only on existing databases hides genesis-migration gaps
2. **Requirement checkboxes are a tracking artifact, not just a gate** — update them at plan completion so they reflect reality at archive time
3. **Auth middleware migrations are less risky than they look** — changing a JWKS URL is a one-line diff with no schema or protocol impact; the testing surface is the JWKS fetch at startup

### Cost Observations

- Model mix: Sonnet 4.6 (all phases)
- Sessions: ~2 sessions over 2 days
- Notable: Phase 5 (infra provisioning) generated minimal commits — most of the work was manual Supabase dashboard interaction; GSD planning overhead was low relative to v1.0

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 4 | 12 | First milestone; established FAIR-RAG module isolation + sub-graph patterns |
| v1.1 | 3 | 6 | Infrastructure migration; established genesis-migration + direct-connection patterns |

### Cumulative Quality

| Milestone | Tests Added | Modules | Zero-Dep Additions |
|-----------|-------------|---------|-------------------|
| v1.0 | ~55 mock-based unit tests | 8 fiqh modules | modules/fiqh/ (fully isolated from agents layer) |
| v1.1 | 0 new tests (infra migration) | 0 new modules | core/auth.py, api/account.py, .env.example |

### Top Lessons (Verified Across Milestones)

1. Build and test modules in isolation before wiring into the graph — Phase 3 isolation caught interface bugs before Phase 4 integration
2. Pre-canned workarounds for SSE/event propagation accrue UX debt — invest in proper event propagation at design time
3. Always validate Alembic chain on a fresh database before any migration milestone — the genesis-migration gap in v1.1 was only discovered during Phase 5 execution
