# Deen Backend — Fiqh Agentic RAG

## What This Is

An enhancement to the Deen Islamic education platform's chatbot agent that enables it to answer Twelver Shia fiqh questions grounded in Ayatollah Sistani's published rulings. The system implements a FAIR-RAG (Faithful Agentic Iterative Retrieval-Augmented Generation) pipeline that iteratively retrieves, verifies, and synthesizes evidence from Sistani's "Islamic Laws" (4th edition) before generating any answer — ensuring the chatbot never derives its own conclusions or issues fatwas.

**Shipped:** v1.0 — 4 phases, 12 plans, 39 requirements satisfied (2026-03-25) | v1.1 — 3 phases, 6 plans, AWS-free Supabase migration (2026-04-07) | v1.2 complete — Phases 8–11 (config + deps, LLM swap, embedding migration, dead code cleanup)

## Core Value

Every fiqh answer must be strictly grounded in retrieved evidence from Ayatollah Sistani's published rulings — the system refuses to answer rather than hallucinate or speculate.

## Requirements

### Validated

- ✓ FastAPI backend with SSE streaming chat endpoint (`/chat/stream/agentic`) — existing
- ✓ LangGraph-based agentic pipeline with tool selection — existing
- ✓ Pinecone-based dense + sparse retrieval for hadith/Quran content — existing
- ✓ Redis-backed conversation memory — existing
- ✓ Query classification and routing (non-Islamic, fiqh early exit) — existing
- ✓ Translation and query enhancement tools — existing
- ✓ PostgreSQL persistence with Alembic migrations — existing
- ✓ AWS Cognito JWT authentication — existing (replaced by Supabase Auth in v1.1)
- ✓ Fiqh book data ingestion pipeline (PDF parsing, chunking, embedding, Pinecone upload) — v1.0
- ✓ Dedicated Pinecone indexes for fiqh content (deen-fiqh-dense + deen-fiqh-sparse) — v1.0
- ✓ 6-category fiqh classifier (VALID_OBVIOUS/SMALL/LARGE/REASONER/OUT_OF_SCOPE_FIQH/UNETHICAL, gpt-4o-mini) — v1.0
- ✓ Query decomposition into 1-4 keyword-rich sub-queries with safe fallback — v1.0
- ✓ Hybrid retrieval with RRF merging (dense + sparse, BM25 encoder, dedup, up to 20 docs) — v1.0
- ✓ ChatState extended with `fiqh_category` field (backwards-compatible) — v1.0
- ✓ LLM-based evidence filtering (inclusive, gpt-4.1) — v1.0
- ✓ Structured Evidence Assessment (SEA) — checklist gap analysis with sufficiency verdict, gpt-4o-mini — v1.0
- ✓ Iterative query refinement targeting identified gaps using confirmed facts — v1.0
- ✓ Faithful answer generation with strict evidence-only grounding, inline [n] citations, fatwa disclaimer — v1.0
- ✓ FAIR-RAG coordinator: max-3-iteration retrieve→filter→assess→refine loop with early exit — v1.0
- ✓ FAIR-RAG sub-graph wired as LangGraph sub-graph invoked by main ChatAgent — v1.0
- ✓ SSE streaming of intermediate fiqh pipeline status events — v1.0
- ✓ `fiqh_references` SSE event with book/chapter/section/ruling_number per source — v1.0
- ✓ LLM-generated rejection for OUT_OF_SCOPE_FIQH and UNETHICAL categories — v1.0
- ✓ Session isolation via `checkpointer=False` on fiqh sub-graph — v1.0
- ✓ Non-fiqh path preserved unchanged — v1.0

## Current Milestone: v1.2 Claude Migration

**Goal:** Replace all OpenAI model usage with Anthropic Claude (LLM) and free HuggingFace embeddings across the full pipeline.

**Target features:**
- LLM swap: gpt-4.1 → claude-sonnet-4-6, gpt-4o-mini → claude-haiku-4-5 ✓ Phase 9 complete
- Embedding swap: text-embedding-3-small → all-mpnet-base-v2 (HuggingFace, free, already installed) ✓ Phase 10 complete
- Config: ANTHROPIC_API_KEY wired; OPENAI_API_KEY dependency removed ✓ Phase 8 complete
- DB migration: pgvector columns resized 1536 → 768 dims (all-mpnet-base-v2 produces 768-dim) ✓ Phase 10 complete
- Dependencies: langchain-anthropic added; voyageai removed ✓ Phase 11 complete
- Dead code: OpenAI client imports, OPENAI_API_KEY shim, and stale test mocks cleaned up ✓ Phase 11 complete

**Decision (Phase 9):** Voyage AI dropped in favour of HuggingFace `all-mpnet-base-v2` for pgvector embeddings — already installed, free, no API key required. Phase 10 plan to be updated accordingly.

## Shipped: v1.1 Supabase Migration ✅

**Shipped:** 2026-04-07 — 3 phases, 6 plans

### Validated in v1.1

- ✓ Database connection switched from AWS RDS to Supabase Postgres — v1.1
- ✓ All 13 SQLAlchemy tables + alembic_version created via genesis migration + 7 original migrations — v1.1
- ✓ DB_* vars + ASYNC_DATABASE_URL pointing at Supabase direct connection (port 5432) — v1.1
- ✓ JWTBearer middleware verifies Supabase Auth JWTs (ES256, JWKS from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`) — v1.1
- ✓ Cognito env vars (COGNITO_REGION, COGNITO_POOL_ID) removed; SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY added — v1.1
- ✓ Account deletion uses Supabase Admin API (httpx DELETE) instead of boto3 AdminDeleteUser — v1.1
- ✓ All routes protected with strict auth; ENV=development bypass for local testing — v1.1
- ✓ boto3 removed from requirements.txt and api/account.py — v1.1
- ✓ .env.example created with all 28 env vars; README updated with full env var docs — v1.1

### Out of Scope

- Other maraji (scholars) beyond Sistani — single-scholar focus; cross-marja conflation risk
- Sistani.org Q&A data scraping — book corpus is bounded and sufficient; deferred to v2
- Model fine-tuning or training — agentic pipeline architecture only
- Frontend changes — backend API only; frontend consumes existing SSE protocol
- Arabic/Persian language support for the fiqh pipeline — English-first; translation tool handles queries
- Reasoner model routing (e.g., o1 for complex inheritance) — defer to future iteration

## Context

**Shipped v1.1 (2026-04-07):**
- 3 phases, 6 plans — AWS fully removed, Supabase Postgres + Auth in place
- Key fix: genesis Alembic migration created to support fresh-DB provisioning (pre-alembic tables were missing from chain)
- Operator onboarding: .env.example (28 vars) + README env section — no git-history archaeology needed

**Shipped v1.0 (2026-03-25):**
- 4 phases, 12 plans, 39 requirements satisfied
- ~49K LOC added across 257 files (Python 3.11)
- 3000 chunks from Sistani's "Islamic Laws" 4th ed. in Pinecone (ns1)
- 6 tech debt items accumulated (all low severity, no blockers) — see `.planning/milestones/v1.0-MILESTONE-AUDIT.md`

**Architecture shipped:**
- `modules/fiqh/` — classifier, decomposer, retriever, filter, sea, refiner, generator, fair_rag
- `agents/fiqh/fiqh_graph.py` — compiled LangGraph sub-graph with checkpointer=False
- `agents/state/` — FiqhState TypedDict, ChatState fiqh fields
- `core/pipeline_langgraph.py` — fiqh SSE path (status events, token streaming, fiqh_references)
- `scripts/ingest_fiqh.py` — full ingestion pipeline

**Notable from v1.0:**
- FARSIQA-inspired approach: 97% negative rejection accuracy target met
- Dynamic LLM allocation (gpt-4o-mini for routing/SEA, gpt-4.1 for generation) saves ~13% vs static large
- Max 3 iterations enforced throughout — iteration 4 showed diminishing/negative returns in research

## Constraints

- **Tech Stack**: Must integrate with existing FastAPI + LangGraph + Pinecone + Redis stack
- **LLM Provider**: OpenAI models — gpt-4.1 (large) and gpt-4o-mini (small) for dynamic allocation
- **Retrieval**: Pinecone for both dense and sparse indices (separate from existing hadith/Quran indices)
- **Iterations**: Max 3 retrieval iterations per query (research shows diminishing returns beyond 3)
- **Religious Sensitivity**: Never issue fatwas, always include disclaimers, refuse rather than speculate
- **Streaming**: Must emit SSE events compatible with existing frontend protocol

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Separate Pinecone index for fiqh | Keep fiqh corpus isolated from hadith/Quran for precision | ✓ deen-fiqh-dense + deen-fiqh-sparse, 3000 chunks in ns1 |
| FAIR-RAG as LangGraph sub-graph | Integrates cleanly with existing agent; main agent routes to sub-graph | ✓ `agents/fiqh/fiqh_graph.py` compiled with `checkpointer=False` |
| Dynamic LLM allocation | 13% cheaper, 97% vs 94% negative rejection per FARSIQA | ✓ gpt-4o-mini for SEA/decompose/filter, gpt-4.1 for generation/refinement |
| Max 3 iterations | Both FAIR-RAG and FARSIQA show iteration 4 gives negligible/negative improvement | ✓ FiqhState iteration counter, `_route_after_assess` exits at iteration >= 3 |
| Single book corpus only | Bounded corpus makes data quality controllable; expand later | ✓ Sistani "Islamic Laws" 4th ed., 3000 chunks |
| 6-category classifier over binary | Current binary classifier did not route fiqh queries accurately | ✓ VALID_OBVIOUS/SMALL/LARGE/REASONER/OUT_OF_SCOPE_FIQH/UNETHICAL in Phase 2/4 |
| Pre-canned SSE stage events | Fiqh sub-graph runs as black box; FiqhState.status_events not propagated back | ⚠ UX inaccuracy: `fiqh_refine` always emits regardless of actual iterations |
| No module-level fiqh env var guard | Guard in ingestion script only — avoids breaking server startup for devs without fiqh indexes | ✓ Works correctly in all environments |
| Genesis Alembic migration (0000_initial_schema.py) | Pre-alembic RDS tables had no migration; fresh DB would fail at step 2 of chain | ✓ All 8 migrations run cleanly on fresh Supabase DB; down_revision chain fixed |
| Direct connection port 5432 (not pooler 6543) | asyncpg incompatible with transaction pooler | ✓ Both DATABASE_URL and ASYNC_DATABASE_URL use port 5432 |
| supabase-py SDK not added | App uses SQLAlchemy directly; SDK wraps PostgREST/storage/realtime which are unused | ✓ Zero new dependencies for DB layer |
| Auth replacement is middleware-only | Frontend handles Supabase Auth SDK; backend validates JWTs only | ✓ JWKS fetched at startup from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` |
| boto3 retained through Phase 6 (removed in Phase 7) | Explicit phase boundary kept scope clean — auth and cleanup are separate concerns | ✓ Clean separation; no lingering partial state |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:** update Validated, Active, Out of Scope, and Key Decisions.

**After each milestone** (via `/gsd:complete-milestone`): full review of all sections.

---
*Last updated: 2026-04-10 — Phase 9 complete: all LLM calls use ChatAnthropic (claude-sonnet-4-6 / claude-haiku-4-5); LLM-01–07 satisfied; Voyage AI dropped in favour of HuggingFace all-mpnet-base-v2 for Phase 10*
