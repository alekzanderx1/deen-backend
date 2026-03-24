---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to execute
stopped_at: Completed 01-data-foundation-01-02-PLAN.md
last_updated: "2026-03-24T01:48:57.845Z"
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 3
  completed_plans: 2
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-23)

**Core value:** Every fiqh answer must be strictly grounded in retrieved evidence from Ayatollah Sistani's published rulings — the system refuses to answer rather than hallucinate or speculate.
**Current focus:** Phase 01 — data-foundation

## Current Position

Phase: 01 (data-foundation) — EXECUTING
Plan: 3 of 3

## Performance Metrics

**Velocity:**

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
| Phase 01-data-foundation P01 | 2 | 3 tasks | 4 files |
| Phase 01-data-foundation P02 | 6 | 1 tasks | 4 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

- **TF-IDF vectorizer persistence**: Unclear whether the existing pipeline persists the fitted vectorizer to disk. Must audit `modules/embedding/embedder.py` before finalizing ingestion script design — if persistence pattern does not exist, it must be built.
- **LangGraph 0.2.64 sub-graph API**: Sub-graph composition (`.invoke()` vs `.astream()` for nested graphs) should be verified against release notes before Phase 4 implementation begins.
- **pymupdf4llm version**: Version 0.0.17 was current at knowledge cutoff; verify latest on PyPI before pinning.
- **Sistani PDF ruling-number format**: Chunking regex anchoring logic assumes numbered rulings (e.g., "Issue 712:"); confirm actual 4th edition format before writing the parser.

## Session Continuity

Last session: 2026-03-24T01:48:57.835Z
Stopped at: Completed 01-data-foundation-01-02-PLAN.md
Resume file: None
