# Deen Backend — Fiqh Agentic RAG

## What This Is

An enhancement to the Deen Islamic education platform's chatbot agent that enables it to answer Twelver Shia fiqh questions grounded in Ayatollah Sistani's published rulings. The system implements a FAIR-RAG (Faithful Agentic Iterative Retrieval-Augmented Generation) pipeline that iteratively retrieves, verifies, and synthesizes evidence from Sistani's "Islamic Laws" (4th edition) before generating any answer — ensuring the chatbot never derives its own conclusions or issues fatwas.

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

### Validated

- ✓ Fiqh book data ingestion pipeline (PDF parsing, chunking, embedding, Pinecone upload) — Validated in Phase 1: Data Foundation
- ✓ Dedicated Pinecone index(es) for fiqh content (dense + sparse) — Validated in Phase 1: Data Foundation

### Validated

- ✓ Improved fiqh query classifier (6-category: VALID_OBVIOUS/SMALL/LARGE/REASONER/OUT_OF_SCOPE_FIQH/UNETHICAL) using gpt-4o-mini — Validated in Phase 2: Routing and Retrieval
- ✓ Query decomposition into 1-4 keyword-rich sub-queries with JSON fence stripping and safe fallback — Validated in Phase 2: Routing and Retrieval
- ✓ Hybrid retrieval with RRF merging (dense + sparse) from fiqh Pinecone indexes, BM25 encoder, deduplication, up to 20 docs — Validated in Phase 2: Routing and Retrieval
- ✓ ChatState extended with `fiqh_category` field (backwards-compatible alongside `is_fiqh`) — Validated in Phase 2: Routing and Retrieval

### Validated

- ✓ LLM-based evidence filtering (inclusive, remove only clearly irrelevant docs) — Validated in Phase 3: FAIR-RAG Core Modules
- ✓ Structured Evidence Assessment (SEA) — checklist-based gap analysis with sufficiency verdict — Validated in Phase 3: FAIR-RAG Core Modules
- ✓ Iterative query refinement targeting identified gaps using confirmed facts — Validated in Phase 3: FAIR-RAG Core Modules
- ✓ Faithful answer generation with strict evidence-only grounding — Validated in Phase 3: FAIR-RAG Core Modules
- ✓ Dynamic LLM allocation (gpt-4o-mini for SEA, gpt-4.1 for filtering/refinement/generation) — Validated in Phase 3: FAIR-RAG Core Modules
- ✓ Inline citations [n] linking to source passages with references list — Validated in Phase 3: FAIR-RAG Core Modules
- ✓ Fatwa disclaimer on every ruling response — Validated in Phase 3: FAIR-RAG Core Modules
- ✓ Insufficient evidence handling — partial answers with redirect to official sources — Validated in Phase 3: FAIR-RAG Core Modules
- ✓ FAIR-RAG coordinator: max-3-iteration retrieve→filter→assess→refine loop, doc accumulation, early exit — Validated in Phase 3: FAIR-RAG Core Modules

### Validated

- ✓ FAIR-RAG iterative sub-graph wired as a LangGraph sub-graph invoked by the main ChatAgent — Validated in Phase 4: Assembly and Integration
- ✓ SSE streaming of intermediate fiqh pipeline status (classifying, decomposing, retrieving, filtering, assessing, refining, generating) — Validated in Phase 4: Assembly and Integration
- ✓ `fiqh_references` SSE event emitted after streaming with book/chapter/section/ruling_number per source — Validated in Phase 4: Assembly and Integration
- ✓ Negative rejection — OUT_OF_SCOPE_FIQH and UNETHICAL categories exit early with LLM-generated personalized rejection messages — Validated in Phase 4: Assembly and Integration
- ✓ Session isolation — `checkpointer=False` on compiled sub-graph guarantees fresh FiqhState per invocation — Validated in Phase 4: Assembly and Integration
- ✓ Non-fiqh path preserved unchanged — existing hadith/Quran pipeline unaffected — Validated in Phase 4: Assembly and Integration

### Active

### Out of Scope

- Other maraji (scholars) beyond Sistani — single-scholar focus for now
- Sistani.org Q&A data scraping — starting with the book only
- Model fine-tuning or training — agentic pipeline architecture only
- Frontend changes — backend API only
- Arabic/Persian language support for the fiqh pipeline — English first
- Reasoner model routing (e.g., o1 for complex inheritance) — defer to future iteration

## Context

- The existing chatbot already has a LangGraph agent with classification → tool selection → generation flow
- The current fiqh classification exists but doesn't perform well at routing queries to the correct category
- The FAIR-RAG approach (from academic research) treats evidence gathering as an iterative, self-auditing process — the key innovation is the Structured Evidence Assessment (SEA) module that explicitly checks what's confirmed vs what's missing
- Ayatollah Sistani's "Islamic Laws" (4th edition) is a ~112-page PDF covering tahara, salah, sawm, hajj, khums, transactions, family law, etc.
- The FARSIQA paper achieved 97% negative rejection accuracy with this approach — critical for religious content where wrong answers are worse than no answers
- Chunking strategy from research: ~300-400 tokens, paragraph-boundary aware, with metadata (chapter, section, topic tags)
- The system must never issue fatwas — always disclaimer and redirect to qualified authority

## Constraints

- **Tech Stack**: Must integrate with existing FastAPI + LangGraph + Pinecone + Redis stack
- **LLM Provider**: OpenAI models — gpt-4.1 (large) and gpt-4o-mini (small) for dynamic allocation
- **Retrieval**: Pinecone for both dense and sparse indices (separate from existing hadith/Quran indices)
- **Iterations**: Max 3 retrieval iterations per query (research shows diminishing returns beyond 3)
- **Religious Sensitivity**: Never issue fatwas, always include disclaimers, refuse rather than speculate
- **Streaming**: Must emit SSE status events compatible with existing frontend protocol

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Separate Pinecone index for fiqh | Keep fiqh corpus isolated from hadith/Quran for precision | deen-fiqh-dense + deen-fiqh-sparse, 3000 chunks in ns1 |
| FAIR-RAG as LangGraph sub-graph | Integrates cleanly with existing agent architecture; main agent routes to fiqh sub-graph | Implemented in Phase 4: `agents/fiqh/fiqh_graph.py` compiled with `checkpointer=False` |
| Dynamic LLM allocation | 13% cheaper than static large with better negative rejection (97% vs 94%) per FARSIQA research | Implemented in Phase 3: gpt-4o-mini for SEA/decompose/filter, gpt-4.1 for generation/refinement |
| Max 3 iterations | Both FAIR-RAG and FARSIQA papers show iteration 4 gives negligible or negative improvement | Implemented in Phase 3/4: iteration counter in FiqhState, `_route_after_assess` exits at iteration >= 3 |
| Start with single book only | Bounded corpus makes data quality controllable; expand later | Implemented in Phase 1: Sistani "Islamic Laws" 4th ed., ~3000 chunks in Pinecone ns1 |
| Improved classifier over existing | Current classifier doesn't route fiqh queries accurately enough | Implemented in Phase 2/4: 6-category classifier (VALID_OBVIOUS/SMALL/LARGE/REASONER/OUT_OF_SCOPE_FIQH/UNETHICAL) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-25 — Phase 4 complete — all milestone phases complete*
