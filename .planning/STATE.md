# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-23)

**Core value:** Every fiqh answer must be strictly grounded in retrieved evidence from Ayatollah Sistani's published rulings — the system refuses to answer rather than hallucinate or speculate.
**Current focus:** Phase 1 — Data Foundation

## Current Position

Phase: 1 of 4 (Data Foundation)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-03-23 — Roadmap created, ready to begin Phase 1 planning

Progress: [░░░░░░░░░░] 0%

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

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Separate Pinecone index for fiqh — keeps fiqh corpus isolated from hadith/Quran for precision
- FAIR-RAG as LangGraph sub-graph — integrates cleanly with existing agent; main agent routes to fiqh sub-graph
- Dynamic LLM allocation — gpt-4o-mini for routing/decomposition/SEA; gpt-4.1 for filtering/refinement/generation
- Max 3 iterations — both FAIR-RAG and FARSIQA papers show diminishing returns beyond iteration 3
- Improved classifier over existing — current binary classifier does not route fiqh queries accurately

### Pending Todos

None yet.

### Blockers/Concerns

- **TF-IDF vectorizer persistence**: Unclear whether the existing pipeline persists the fitted vectorizer to disk. Must audit `modules/embedding/embedder.py` before finalizing ingestion script design — if persistence pattern does not exist, it must be built.
- **LangGraph 0.2.64 sub-graph API**: Sub-graph composition (`.invoke()` vs `.astream()` for nested graphs) should be verified against release notes before Phase 4 implementation begins.
- **pymupdf4llm version**: Version 0.0.17 was current at knowledge cutoff; verify latest on PyPI before pinning.
- **Sistani PDF ruling-number format**: Chunking regex anchoring logic assumes numbered rulings (e.g., "Issue 712:"); confirm actual 4th edition format before writing the parser.

## Session Continuity

Last session: 2026-03-23
Stopped at: Roadmap created — ROADMAP.md, STATE.md, and REQUIREMENTS.md traceability written
Resume file: None
