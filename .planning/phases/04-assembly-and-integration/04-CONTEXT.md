# Phase 4: Assembly and Integration - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the complete FAIR-RAG pipeline as a LangGraph sub-graph invoked by the live SSE streaming endpoint. Replaces the current fiqh early-exit with real FAIR-RAG processing. Delivers end-to-end fiqh query handling: classification → sub-graph (decompose → retrieve → filter → assess → refine loop) → streaming answer generation → fiqh references SSE event. Non-fiqh queries continue through the existing agent path untouched.

</domain>

<decisions>
## Implementation Decisions

### Sub-graph Node Structure
- **D-01:** The FiqhAgent sub-graph is a **multi-node compiled LangGraph sub-graph** with one node per pipeline stage: `decompose` → `retrieve` → `filter` → `assess` → (conditional: INSUFFICIENT and iteration < 3 → `refine` → back to `retrieve`; SUFFICIENT or iteration ≥ 3 → exit sub-graph).
- **D-02:** Loop is implemented with **conditional edges + iteration counter** in FiqhState. After `assess`, router checks verdict and counter. Max 3 iterations enforced in state, matching Phase 3 logic.
- **D-03:** Sub-graph calls Phase 3 module functions directly: `decompose_query`, `retrieve_fiqh_documents`, `filter_evidence`, `assess_evidence`, `refine_query`. Does NOT call `run_fair_rag()` — that function is bypassed in Phase 4 (the sub-graph is the reusable graph equivalent).
- **D-04:** Sub-graph does **NOT** include a generate node. On exit, it stores `fiqh_filtered_docs` (final filtered doc list) and `fiqh_sea_result` in ChatState. Generation happens in the main graph.

### Answer Streaming
- **D-05:** A new `generate_fiqh_response` node is added to the **main ChatAgent graph** (not the sub-graph). It runs after the fiqh sub-graph exits.
- **D-06:** This node uses the **fiqh-specific system prompt** from `modules/fiqh/generator.py` (`SYSTEM_PROMPT` + evidence format). It formats `fiqh_filtered_docs` as a numbered evidence list and streams tokens via `chain.stream()`. One LLM call only — no duplicate invocations.
- **D-07:** `pipeline_langgraph.py` detects that the fiqh path was taken (via `fiqh_category` in final state) and streams the response from the node's token output — same pattern as the existing hadith streaming path.
- **D-08:** A `generate_answer_stream()` variant may be added to `generator.py` to expose the streaming prompt/chain for reuse by the main graph node.

### Main Graph Routing
- **D-09:** `_fiqh_classification_node` is **fully replaced** with the Phase 2 6-category classifier (`modules/fiqh/classifier.py`). The old binary `classify_fiqh_query()` from `modules/classification/classifier.py` is no longer called for fiqh routing.
- **D-10:** Routing after classification:
  - `VALID_OBVIOUS`, `VALID_SMALL`, `VALID_LARGE`, `VALID_REASONER` → fiqh sub-graph → `generate_fiqh_response` → END
  - `OUT_OF_SCOPE_FIQH`, `UNETHICAL` → `check_early_exit` → END
  - Non-fiqh (existing non-Islamic path) → `agent` → existing tools path
- **D-11:** `is_fiqh` is set to `True` for any `VALID_*` result to preserve backward compatibility with existing state consumers.
- **D-12:** Rejection messages for `OUT_OF_SCOPE_FIQH` and `UNETHICAL` are **LLM-generated** (personalized, gpt-4o-mini), not hardcoded strings. The `check_early_exit` node generates a contextual message referencing the actual query. This replaces the static `EARLY_EXIT_FIQH` constant.

### fiqh_references SSE Event
- **D-13:** The sub-graph stores the final filtered doc list in `ChatState` as `fiqh_filtered_docs: list[dict]` at sub-graph exit.
- **D-14:** After streaming the fiqh answer, `pipeline_langgraph.py` emits a `fiqh_references` SSE event from `fiqh_filtered_docs` — same pattern as `hadith_references` and `quran_references` today. Each reference carries: `book`, `chapter`, `section`, `ruling_number` from chunk metadata.

### ChatState Additions
- **D-15:** Add to `ChatState` and `create_initial_state()`:
  - `fiqh_filtered_docs: list[dict]` — final filtered doc set from sub-graph
  - `fiqh_sea_result: Optional[SEAResult]` — SEA result from final iteration (for generation context)
  - Existing `fiqh_category: str` field (Phase 2) drives all routing — no new routing fields needed.

### Claude's Discretion
- FiqhState TypedDict shape for the sub-graph's internal state (iteration counter, accumulated docs, prior queries, current query)
- Exact SSE status message strings for each fiqh pipeline stage (classifying, decomposing, retrieving, filtering, assessing, refining, generating)
- Whether to add `fiqh_subgraph` as a node in `ChatAgent` or compile it as a separate `CompiledGraph` invoked from within a node
- Test structure for end-to-end integration (mock at sub-graph boundary vs. mock individual fiqh modules)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Integration (INTG-01 to INTG-05) — all acceptance criteria for this phase

### Main graph and pipeline (files to modify)
- `agents/core/chat_agent.py` — main graph: replace `_fiqh_classification_node`, add fiqh routing, add `generate_fiqh_response` node, wire sub-graph
- `agents/state/chat_state.py` — add `fiqh_filtered_docs` and `fiqh_sea_result` fields
- `core/pipeline_langgraph.py` — SSE streaming layer: detect fiqh path, emit `fiqh_references` event, stream fiqh answer tokens

### Phase 3 module functions (called directly by sub-graph nodes)
- `modules/fiqh/decomposer.py` — `decompose_query(query) -> list[str]`
- `modules/fiqh/retriever.py` — `retrieve_fiqh_documents(query) -> list[dict]`
- `modules/fiqh/filter.py` — `filter_evidence(query, docs) -> list[dict]`
- `modules/fiqh/sea.py` — `assess_evidence(query, docs) -> SEAResult`, `SEAResult` Pydantic model
- `modules/fiqh/refiner.py` — `refine_query(original_query, sea_result, prior_queries) -> list[str]`
- `modules/fiqh/generator.py` — `SYSTEM_PROMPT`, evidence formatting; add streaming variant here

### Phase 2 classifier (replaces binary classifier in main graph)
- `modules/fiqh/classifier.py` — 6-category classifier; read interface before wiring into `_fiqh_classification_node`

### Existing patterns to follow
- `core/pipeline_langgraph.py` lines 132–202 — existing streaming + reference event emission pattern
- `agents/prompts/agent_prompts.py` — `EARLY_EXIT_FIQH` constant being replaced by LLM-generated messages

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `agents/state/chat_state.py` → `create_initial_state()`: Add new fiqh fields here; all consumers call this factory
- `core/pipeline_langgraph.py` → `sse_event()`: Reuse for new `fiqh_references` event type
- `modules/fiqh/generator.py` → `SYSTEM_PROMPT`, `_format_evidence()`, `_prompt`: Reuse directly in `generate_fiqh_response` node; add streaming variant alongside existing `generate_answer()`
- `core/chat_models.get_generator_model()`: Use for the `generate_fiqh_response` node's streaming chain

### Established Patterns
- SSE reference event pattern: `yield sse_event("hadith_references", {"references": hadith_json})` — emit `fiqh_references` the same way after answer streams
- LangGraph sub-graph: compile with `StateGraph(FiqhState).compile()` and invoke from a parent node or wire as a subgraph node
- Tool error pattern: never raise from nodes — append to `errors`, set `should_end` if fatal
- `NODE_STATUS_MESSAGES` dict in `pipeline_langgraph.py`: add fiqh stage messages here

### Integration Points
- `ChatAgent._fiqh_classification_node()` — replace classifier call; set `fiqh_category` and `is_fiqh`
- `ChatAgent._route_after_fiqh_check()` — expand routing from 2 paths to 3 (valid fiqh / rejection / non-fiqh)
- `ChatAgent._check_early_exit_node()` — update to call LLM for personalized rejection messages
- `ChatAgent._build_graph()` — add fiqh sub-graph node and `generate_fiqh_response` node; wire conditional edges

</code_context>

<specifics>
## Specific Ideas

- The `generate_fiqh_response` node must use the fiqh-specific system prompt (not the generic generator prompt) — the user explicitly called this out to avoid a generic prompt being used for fiqh answers
- One LLM call for generation — no double invocation. Sub-graph exits with docs in state; main graph does the single streaming generation pass
- Rejection messages (OUT_OF_SCOPE_FIQH, UNETHICAL) must be LLM-generated and personalized to the query — not hardcoded

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-assembly-and-integration*
*Context gathered: 2026-03-24*
