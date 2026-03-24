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

### Active

- [ ] FAIR-RAG iterative loop as a LangGraph sub-graph (decompose → retrieve → filter → assess → refine → repeat, max 3 iterations)
- [ ] LLM-based evidence filtering (inclusive, remove only clearly irrelevant docs)
- [ ] Structured Evidence Assessment (SEA) — checklist-based gap analysis with sufficiency verdict
- [ ] Iterative query refinement targeting identified gaps using confirmed facts
- [ ] Faithful answer generation with strict evidence-only grounding
- [ ] Dynamic LLM allocation (gpt-4o-mini for routing/decomposition/SEA, gpt-4.1 for filtering/refinement/generation)
- [ ] Inline citations [n] linking to source passages with references list
- [ ] Fatwa disclaimer on every ruling response
- [ ] Insufficient evidence handling — partial answers with redirect to official sources
- [ ] SSE streaming of intermediate pipeline status (decomposing, retrieving, assessing, refining)
- [ ] Negative rejection — refuse to answer when evidence is insufficient or question is out of scope

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
| FAIR-RAG as LangGraph sub-graph | Integrates cleanly with existing agent architecture; main agent routes to fiqh sub-graph | — Pending |
| Dynamic LLM allocation | 13% cheaper than static large with better negative rejection (97% vs 94%) per FARSIQA research | — Pending |
| Max 3 iterations | Both FAIR-RAG and FARSIQA papers show iteration 4 gives negligible or negative improvement | — Pending |
| Start with single book only | Bounded corpus makes data quality controllable; expand later | — Pending |
| Improved classifier over existing | Current classifier doesn't route fiqh queries accurately enough | — Pending |

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
*Last updated: 2026-03-24 — Phase 2 complete*
