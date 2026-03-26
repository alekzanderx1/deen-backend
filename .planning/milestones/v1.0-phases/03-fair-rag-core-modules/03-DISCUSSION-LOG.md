# Phase 3: FAIR-RAG Core Modules - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 03-fair-rag-core-modules
**Mode:** Auto (--auto flag active, no user interaction)
**Areas discussed:** Module structure, SEA output format, Evidence filter approach, Citation implementation

---

## Module Structure and Iterative Loop Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Loop in Phase 3 (pure Python coordinator) | Implements EVID-07 as `fair_rag.py` standalone function; Phase 4 wraps in LangGraph | ✓ |
| Loop deferred to Phase 4 | Phase 3 only builds isolated modules; loop added during LangGraph assembly | |

**Auto-selected:** Loop in Phase 3 — EVID-07 is mapped to Phase 3 in REQUIREMENTS.md; pure Python coordinator keeps modules testable before LangGraph.
**Notes:** `fair_rag.py` exposes `run_fair_rag(query: str) -> str` as the Phase 4 integration point.

---

## SEA Structured Output Format

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic + `.with_structured_output()` | Reliable JSON via LangChain structured output; `SEAResult` + `Finding` Pydantic models | ✓ |
| JSON mode + manual parse | LLM JSON mode, parse with `json.loads()`; less type-safe | |
| Plain text + regex | Parse LLM freeform text; least reliable | |

**Auto-selected:** Pydantic + `.with_structured_output()` — most reliable for downstream consumption; avoids JSON parse fragility.
**Notes:** `SEAResult(findings, verdict, confirmed_facts, gaps)` schema defined in D-12.

---

## Evidence Filter Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Batch filter (one LLM call) | All docs sent in one prompt; LLM returns list of chunk_ids to keep; cost-efficient | ✓ |
| Per-doc filter (one call per doc) | More granular but 20x more expensive; not justified for inclusive filter | |
| Score-based threshold | LLM returns relevance scores; keep above threshold; adds complexity | |

**Auto-selected:** Batch filter — cost-efficient, aligns with inclusive approach (EVID-01), fail-open on error.

---

## Citation Implementation

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid: LLM cites [n], system builds references | LLM embeds [n] tokens; system post-processes to build structured references list | ✓ |
| Pure LLM | LLM generates both inline citations and references list; less reliable | |
| Pure system | System injects citations post-generation; LLM unaware of citation numbering | |

**Auto-selected:** Hybrid — LLM handles creative citation placement; system ensures references list is accurate and structured.

---

## Claude's Discretion

- Exact prompt templates for filter, SEA, refiner, and generator
- Module-level logger per file
- SEA checklist decomposition depth
- Coordinator dry-run mode

## Deferred Ideas

None raised during auto-discussion.
