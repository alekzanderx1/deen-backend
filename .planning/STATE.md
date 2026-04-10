---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Claude Migration
status: verifying
stopped_at: Completed 09-02-PLAN.md
last_updated: "2026-04-10T14:19:00.000Z"
last_activity: 2026-04-10
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-09 after v1.2 milestone start)

**Core value:** Every fiqh answer must be strictly grounded in retrieved evidence from Ayatollah Sistani's published rulings — the system refuses to answer rather than hallucinate or speculate.
**Current focus:** Phase 09 — LLM swap (09-01 complete, 09-02 complete)

## Current Position

Phase: 9
Plan: 02 complete — Phase 09 all plans done
Status: In progress
Last activity: 2026-04-10

Progress: [░░░░░░░░░░] 0%  (0/4 phases complete)

## v1.2 Phase Overview

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 8. Config + Dependencies | App boots with Claude + Voyage AI credentials; packages swapped | CONF-01..07 | Not started |
| 9. LLM Swap | All LLM calls use ChatAnthropic; streaming fiqh response works end-to-end | LLM-01..07 | Not started |
| 10. Embedding Migration | pgvector columns resized to 1024; voyage-4 backfill complete; alembic clean | EMBED-01..05 | Not started |
| 11. Dead Code Cleanup | Zero openai references remain; test suite passes | CLEAN-03..04 | Not started |

## Performance Metrics

**Velocity (v1.2):**

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
| Phase 08 P02 | 1 | 2 tasks | 2 files |
| Phase 08-config-dependencies P01 | 1 | 1 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.2 scope]: LLM swap is gpt-4.1 → claude-sonnet-4-6 and gpt-4o-mini → claude-haiku-4-5-20251001
- [v1.2 scope]: Pinecone retrieval embeddings (HuggingFace all-mpnet-base-v2) are NOT changed — only pgvector embeddings migrate to Voyage AI
- [v1.2 scope]: Voyage AI voyage-4 produces 1024-dim vectors vs OpenAI text-embedding-3-small 1536-dim; DB migration required
- [LLM-05]: Claude returns preamble text before JSON — fiqh classifier response parsing must strip it before category extraction
- [LLM-06]: Claude may emit empty AIMessage content in tool-call sequences — must filter before passing history to LLM
- [LLM-04]: Claude requires explicit max_tokens; ModelConfig gets max_tokens=4096 default and temperature validator le=1.0 (Claude max is 1.0, not 2.0)
- [Phase 08]: anthropic pinned at 0.87.0 per D-05 (not 0.92.0 currently in venv) to ensure reproducible installs
- [Phase 08]: tiktoken==0.9.0 retained despite OpenAI removal — used directly by scripts/ingest_fiqh.py
- [Phase 08-config-dependencies]: ANTHROPIC_API_KEY and VOYAGE_API_KEY replace OPENAI_API_KEY as required startup guards in core/config.py
- [Phase 08-config-dependencies]: LARGE_LLM defaults to claude-sonnet-4-6; SMALL_LLM to claude-haiku-4-5-20251001; EMBEDDING_MODEL to voyage-4 (1024 dims)

- [Phase 09-01]: OPENAI_API_KEY shim = "" (not os.getenv) — legacy modules must not use it for real API calls; Phase 11 removes imports
- [Phase 09-01]: get_classifier_model() uses LARGE_LLM not SMALL_LLM — D-07 SMALL_LLM correction for classifier deferred to Phase 11
- [Phase 09-01]: ChatAnthropic constructor uses api_key kwarg (not anthropic_api_key); max_tokens set at construction per D-02
- [Phase 09-01]: ModelConfig max_tokens changed from Optional[int]=None to int=4096; Optional removed from typing imports

- [Phase 09-02]: FiqhCategory Literal enforces valid category at schema level — VALID_CATEGORIES set check inside classify_fiqh_query removed; set retained for external consumers
- [Phase 09-02]: D-08 AIMessage filter uses getattr(msg, "tool_calls", None) for broad message type safety; filters empty AIMessages with no tool_calls before each llm.invoke()
- [Phase 09-02]: hikmah script lazy-imports ChatAnthropic inside init_llm() branches (consistent with factory function pattern); top-level init_chat_model import removed

### Pending Todos

None yet.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-04-10T14:19:00.000Z
Stopped at: Completed 09-02-PLAN.md
Resume file: None
Next action: Execute Phase 10 — Embedding Migration
