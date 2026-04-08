---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Supabase Migration
status: verifying
stopped_at: Completed 07-cleanup-P01-PLAN.md
last_updated: "2026-04-07T15:11:00.541Z"
last_activity: 2026-04-07
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 6
  completed_plans: 6
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-06 after v1.1 milestone start)

**Core value:** Every fiqh answer must be strictly grounded in retrieved evidence from Ayatollah Sistani's published rulings — the system refuses to answer rather than hallucinate or speculate.
**Current focus:** Phase 07 — cleanup

## Current Position

Phase: 07 (cleanup) — EXECUTING
Plan: 1 of 1
Status: Phase complete — ready for verification
Last activity: 2026-04-08 - Completed quick task 260407-w1l: Migrate hikmah tree and memory agent tables to Supabase DB

## v1.1 Phase Overview

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 5. Database Migration | Supabase Postgres provisioned, all tables present, DB env vars updated | DB-01, DB-02, DB-03 | Not started |
| 6. Auth Migration | Supabase Auth JWTs verified, Cognito fully replaced | AUTH-01, AUTH-02, AUTH-03, AUTH-04 | Not started |
| 7. Cleanup | boto3 removed, env var changes documented | CLEAN-01, CLEAN-02 | Not started |

## Performance Metrics

**Velocity (v1.1):**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

**v1.0 velocity reference (for comparison):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 01-data-foundation P01 | 2 | 3 tasks | 4 files |
| Phase 01-data-foundation P02 | 6 | 1 tasks | 4 files |
| Phase 01-data-foundation P03 | 2 | 1 tasks | 1 files |
| Phase 02-routing-and-retrieval P01 | 1 | 2 tasks | 3 files |
| Phase 02-routing-and-retrieval P02 | 1 | 2 tasks | 3 files |
| Phase 02-routing-and-retrieval P03 | 5 | 2 tasks | 2 files |
| Phase 03-fair-rag-core-modules P01 | 3 | 2 tasks | 4 files |
| Phase 03-fair-rag-core-modules P02 | 2 | 2 tasks | 4 files |
| Phase 03-fair-rag-core-modules P03 | 3 | 1 tasks | 2 files |
| Phase 04-assembly-and-integration P01 | 3 | 3 tasks | 4 files |
| Phase 04-assembly-and-integration P02 | 4 | 2 tasks | 3 files |
| Phase 04-assembly-and-integration P03 | 4 | 2 tasks | 2 files |
| Phase 06-auth-migration PP01 | 1 | 1 tasks | 1 files |
| Phase 06-auth-migration PP03 | 5 | 1 tasks | 2 files |
| Phase 07-cleanup P01 | 3min | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Separate Pinecone index for fiqh — keeps fiqh corpus isolated from hadith/Quran for precision
- FAIR-RAG as LangGraph sub-graph — integrates cleanly with existing agent; main agent routes to fiqh sub-graph
- Dynamic LLM allocation — gpt-4o-mini for routing/decomposition/SEA; gpt-4.1 for filtering/refinement/generation
- Max 3 iterations — both FAIR-RAG and FARSIQA papers show diminishing returns beyond iteration 3
- Improved classifier over existing — current binary classifier does not route fiqh queries accurately
- [Phase 01-data-foundation]: No module-level ValueError guard for fiqh index env vars — guard lives in ingestion script to avoid breaking server startup for developers without fiqh indexes configured
- [Phase 01-02]: Deduplicate ruling numbers via seen_ruling_numbers set — PDF contains 83 inline cross-references matching RULING_PATTERN; only first occurrence of each ruling number is processed
- [Phase 01-02]: Chunk count expectation corrected from 1000-1600 to ~3000: 2796 rulings each produce their own chunk; research merger assumption was incorrect
- [Phase 01-02]: Zero overlap in secondary chunk splitting: each ruling is atomic; overlap between adjacent rulings has no retrieval benefit
- [Phase 01-data-foundation]: No module-level env var guard for fiqh indexes: guard lives inside _run_ingestion() to avoid blocking server startup for developers without fiqh indexes configured
- [Phase 01-data-foundation]: BM25 encoder persisted to data/fiqh_bm25_encoder.json using JSON serialization for portability and Phase 2 query-time reload
- [Phase 01-data-foundation]: Dense embedding sub-batch size 32 (conservative within 32-64 safe range) to prevent OOM with all-mpnet-base-v2
- [Phase 02-routing-and-retrieval]: Inline SYSTEM_PROMPT in fiqh/classifier.py: new standalone classifier, not a port of existing one; no session_id parameter needed
- [Phase 02-routing-and-retrieval]: fiqh_category: str added after is_fiqh in ChatState TypedDict with default '' in create_initial_state() for backward-compatible FAIR-RAG routing
- [Phase 02-routing-and-retrieval]: decompose_query uses get_classifier_model() (gpt-4o-mini) per QPRO-03: cost efficiency for decomposition step
- [Phase 02-routing-and-retrieval]: Fallback returns [query] not [] on any parse/exception: caller always gets at least one retrieval query
- [Phase 02-routing-and-retrieval]: Use _get_sparse_vectorstore() for both dense and sparse fiqh index access: raw Pinecone index returns match.id (chunk_id) needed for RRF deduplication
- [Phase 02-routing-and-retrieval]: sparse_vector= kwarg for sparse index query (not vector=): mixing causes 400 error on sparse-type Pinecone indexes
- [Phase 02-routing-and-retrieval]: BM25_ENCODER_PATH resolved via Path(__file__).resolve(): cwd-independent path for fiqh_bm25_encoder.json regardless of server/test/ingestion context
- [Phase 03-fair-rag-core-modules]: filter_evidence uses get_generator_model() (gpt-4.1): large model for nuanced relevance filtering per EVID-02
- [Phase 03-fair-rag-core-modules]: assess_evidence uses get_classifier_model() (gpt-4o-mini) with with_structured_output(SEAResult): cheaper structured classification per AGEN-08
- [Phase 03-fair-rag-core-modules]: filter_evidence fails open on empty LLM list: empty list = over-aggressive filtering, treat as error, return all docs
- [Phase 03-fair-rag-core-modules]: refine_query uses get_generator_model() (gpt-4.1): refinement needs nuanced cross-referencing per EVID-08
- [Phase 03-fair-rag-core-modules]: generate_answer uses get_generator_model() (gpt-4.1): answer synthesis is highest-stakes step per AGEN-07
- [Phase 03-fair-rag-core-modules]: re.findall citation extraction: LLM embeds [n] inline tokens; post-processor extracts them to build ## Sources — faithful to actual LLM output
- [Phase 03-fair-rag-core-modules]: run_fair_rag uses range(1, 4): enforces max 3 iterations per D-23 and EVID-07
- [Phase 03-fair-rag-core-modules]: refine_query skipped on iteration 3: avoids wasted LLM call when no next retrieval will occur
- [Phase 03-fair-rag-core-modules]: No LangGraph imports in fair_rag.py: pure Python module per D-02; Phase 4 wraps into graph node
- [Phase 04-assembly-and-integration]: FiqhState.sea_result typed as Optional[object] to prevent circular import from agents -> modules packages
- [Phase 04-assembly-and-integration]: agents/state package created fresh in worktree from shawn-dev Phase 2 baseline: worktree was on older commit missing the state package
- [Phase 04-assembly-and-integration]: checkpointer=False on fiqh_subgraph: stateless per-invocation; prevents cross-session state leakage
- [Phase 04-assembly-and-integration]: Wrapper node pattern: _call_fiqh_subgraph_node projects ChatState to fresh FiqhState and maps results back
- [Phase 04-assembly-and-integration]: 3-path routing from fiqh_classification: VALID_* to fiqh_subgraph, OUT_OF_SCOPE/UNETHICAL to check_early_exit with LLM rejection, else to agent
- [Phase 04-assembly-and-integration]: Pre-canned fiqh stage SSE status events: sub-graph runs as black box; pipeline emits pre-canned messages rather than reading FiqhState.status_events
- [Phase 04-assembly-and-integration]: VALID_FIQH_CATEGORIES constant at module level in pipeline_langgraph.py: mirrors chat_agent routing set for consistent fiqh path detection
- [Phase 06-auth-migration]: Supabase vars placed adjacent to Redis/LLM vars in core/config.py; ValueError guard added as standalone block below existing OPENAI/PINECONE guard; COGNITO vars fully deleted per D-03
- [Phase 06-auth-migration]: boto3 import retained in api/account.py through Phase 6 per D-03a — physical removal is Phase 7 CLEAN-01
- [Phase 06-auth-migration]: httpx.delete() used synchronously in account deletion per D-04 — consistent with existing sync-inside-async pattern
- [Phase 06-auth-migration]: 404 from Supabase Admin API treated as success-equivalent per D-05 — user already deleted, log warning and return 204
- [Phase 07-cleanup]: boto3 removal was pre-committed (44e712e) before plan execution; Task 1 verified only
- [Phase 07-cleanup]: .env.example uses comment header migration callout (COGNITO vars removed as of v1.1) matching README Upgrading from v1.0 callout

### v1.1 Decisions

- No data migration: fresh start on Supabase; existing RDS data is abandoned
- Direct connection (port 5432) for both sync and async DB: transaction pooler (6543) incompatible with asyncpg
- supabase-py SDK not added: app uses SQLAlchemy directly; SDK wraps PostgREST/storage/realtime which are unused
- Auth replacement is middleware-only: frontend handles Supabase Auth SDK; backend validates JWTs only
- Phase 5 (DB) and Phase 6 (Auth) are logically sequential for end-to-end testing; Auth code changes can be written before DB is provisioned

### Pending Todos

None yet.

### Blockers/Concerns

None. v1.0 shipped clean. v1.1 requirements and roadmap defined.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260407-d24 | protect all API routes with strict auth and add ENV=development bypass | 2026-04-07 | 417f2f3 | [260407-d24-protect-all-api-routes-with-strict-auth-](./quick/260407-d24-protect-all-api-routes-with-strict-auth-/) |
| 260407-w1l | Migrate hikmah tree and memory agent tables to Supabase DB | 2026-04-08 | 2ba818a | [260407-w1l-migrate-hikmah-tree-and-memory-agent-tab](./quick/260407-w1l-migrate-hikmah-tree-and-memory-agent-tab/) |

## Session Continuity

Last session: 2026-04-07T14:38:25.020Z
Stopped at: Completed 07-cleanup-P01-PLAN.md
Resume file: None
Next action: `/gsd:plan-phase 5`
