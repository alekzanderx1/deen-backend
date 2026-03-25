# Deen Backend — Fiqh Agentic RAG

## What This Is

An enhancement to the Deen Islamic education platform's chatbot agent that enables it to answer Twelver Shia fiqh questions grounded in Ayatollah Sistani's published rulings. The system implements a FAIR-RAG (Faithful Agentic Iterative Retrieval-Augmented Generation) pipeline that iteratively retrieves, verifies, and synthesizes evidence from Sistani's "Islamic Laws" (4th edition) before generating any answer — ensuring the chatbot never derives its own conclusions or issues fatwas.

**Shipped:** v1.0 — 4 phases, 12 plans, 39 requirements satisfied (2026-03-25)

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
- ✓ AWS Cognito JWT authentication — existing
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

### Active

*(Next milestone requirements go here — run `/gsd:new-milestone` to define)*

### Out of Scope

- Other maraji (scholars) beyond Sistani — single-scholar focus; cross-marja conflation risk
- Sistani.org Q&A data scraping — book corpus is bounded and sufficient; deferred to v2
- Model fine-tuning or training — agentic pipeline architecture only
- Frontend changes — backend API only; frontend consumes existing SSE protocol
- Arabic/Persian language support for the fiqh pipeline — English-first; translation tool handles queries
- Reasoner model routing (e.g., o1 for complex inheritance) — defer to future iteration

## Context

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

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:** update Validated, Active, Out of Scope, and Key Decisions.

**After each milestone** (via `/gsd:complete-milestone`): full review of all sections.

---
*Last updated: 2026-03-25 after v1.0 milestone — all 39 requirements validated and shipped*
