# Phase 4: Assembly and Integration - Research

**Researched:** 2026-03-24
**Domain:** LangGraph sub-graph wiring, SSE streaming integration, FastAPI agentic pipeline
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** The FiqhAgent sub-graph is a multi-node compiled LangGraph sub-graph with one node per pipeline stage: `decompose` → `retrieve` → `filter` → `assess` → (conditional: INSUFFICIENT and iteration < 3 → `refine` → back to `retrieve`; SUFFICIENT or iteration ≥ 3 → exit sub-graph).

**D-02:** Loop is implemented with conditional edges + iteration counter in FiqhState. After `assess`, router checks verdict and counter. Max 3 iterations enforced in state, matching Phase 3 logic.

**D-03:** Sub-graph calls Phase 3 module functions directly: `decompose_query`, `retrieve_fiqh_documents`, `filter_evidence`, `assess_evidence`, `refine_query`. Does NOT call `run_fair_rag()` — that function is bypassed in Phase 4 (the sub-graph is the reusable graph equivalent).

**D-04:** Sub-graph does NOT include a generate node. On exit, it stores `fiqh_filtered_docs` (final filtered doc list) and `fiqh_sea_result` in ChatState. Generation happens in the main graph.

**D-05:** A new `generate_fiqh_response` node is added to the main ChatAgent graph (not the sub-graph). It runs after the fiqh sub-graph exits.

**D-06:** This node uses the fiqh-specific system prompt from `modules/fiqh/generator.py` (`SYSTEM_PROMPT` + evidence format). It formats `fiqh_filtered_docs` as a numbered evidence list and streams tokens via `chain.stream()`. One LLM call only — no duplicate invocations.

**D-07:** `pipeline_langgraph.py` detects that the fiqh path was taken (via `fiqh_category` in final state) and streams the response from the node's token output — same pattern as the existing hadith streaming path.

**D-08:** A `generate_answer_stream()` variant may be added to `generator.py` to expose the streaming prompt/chain for reuse by the main graph node.

**D-09:** `_fiqh_classification_node` is fully replaced with the Phase 2 6-category classifier (`modules/fiqh/classifier.py`). The old binary `classify_fiqh_query()` from `modules/classification/classifier.py` is no longer called for fiqh routing.

**D-10:** Routing after classification:
- `VALID_OBVIOUS`, `VALID_SMALL`, `VALID_LARGE`, `VALID_REASONER` → fiqh sub-graph → `generate_fiqh_response` → END
- `OUT_OF_SCOPE_FIQH`, `UNETHICAL` → `check_early_exit` → END
- Non-fiqh (existing non-Islamic path) → `agent` → existing tools path

**D-11:** `is_fiqh` is set to `True` for any `VALID_*` result to preserve backward compatibility with existing state consumers.

**D-12:** Rejection messages for `OUT_OF_SCOPE_FIQH` and `UNETHICAL` are LLM-generated (personalized, gpt-4o-mini), not hardcoded strings. The `check_early_exit` node generates a contextual message referencing the actual query. This replaces the static `EARLY_EXIT_FIQH` constant.

**D-13:** The sub-graph stores the final filtered doc list in `ChatState` as `fiqh_filtered_docs: list[dict]` at sub-graph exit.

**D-14:** After streaming the fiqh answer, `pipeline_langgraph.py` emits a `fiqh_references` SSE event from `fiqh_filtered_docs` — same pattern as `hadith_references` and `quran_references` today. Each reference carries: `book`, `chapter`, `section`, `ruling_number` from chunk metadata.

**D-15:** Add to `ChatState` and `create_initial_state()`:
- `fiqh_filtered_docs: list[dict]` — final filtered doc set from sub-graph
- `fiqh_sea_result: Optional[SEAResult]` — SEA result from final iteration (for generation context)
- Existing `fiqh_category: str` field (Phase 2) drives all routing — no new routing fields needed.

### Claude's Discretion

- FiqhState TypedDict shape for the sub-graph's internal state (iteration counter, accumulated docs, prior queries, current query)
- Exact SSE status message strings for each fiqh pipeline stage (classifying, decomposing, retrieving, filtering, assessing, refining, generating)
- Whether to add `fiqh_subgraph` as a node in `ChatAgent` or compile it as a separate `CompiledGraph` invoked from within a node
- Test structure for end-to-end integration (mock at sub-graph boundary vs. mock individual fiqh modules)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTG-01 | FAIR-RAG pipeline is implemented as a compiled LangGraph sub-graph invoked by the main ChatAgent when a query is classified as fiqh | Sub-graph composition pattern documented in Architecture Patterns section |
| INTG-02 | The existing `fiqh_classification` node routes to the fiqh sub-graph instead of the current early-exit behavior | `_route_after_fiqh_check` expansion from 2 paths to 3 documented; existing routing code read |
| INTG-03 | SSE status events are emitted for each fiqh pipeline stage: classifying, decomposing, retrieving, filtering, assessing, refining, generating | `NODE_STATUS_MESSAGES` / `TOOL_STATUS_MESSAGES` pattern in `pipeline_langgraph.py` lines 19–35 ready to extend |
| INTG-04 | The final answer is streamed token-by-token via the existing SSE `response_chunk` protocol | Existing `chain.stream()` loop in `pipeline_langgraph.py` lines 158–171 is the reuse target |
| INTG-05 | Fiqh citations are emitted as a new SSE event type alongside existing hadith/quran reference events | `sse_event("hadith_references", ...)` pattern at line 197 is the direct model; fiqh metadata keys confirmed in `retriever.py` |
</phase_requirements>

---

## Summary

Phase 4 wires the completed FAIR-RAG modules (Phases 2 and 3) into the live LangGraph agent and SSE streaming pipeline. All module functions are already implemented and tested in isolation. The integration work is surgical: replace the placeholder fiqh early-exit with a real sub-graph, add two new ChatState fields, expand routing in `chat_agent.py`, and extend `pipeline_langgraph.py` to detect the fiqh path and emit a `fiqh_references` event.

The critical architectural choice — resolved by D-03 — is that the sub-graph invokes Phase 3 module functions directly (not `run_fair_rag()`). This gives the sub-graph the iterative retrieve→assess→refine loop as LangGraph nodes with proper state tracking, while keeping each module function independently testable. The LangGraph 1.x sub-graph API (confirmed current) supports both "node wrapping a compiled graph" and "add_node with compiled graph directly" patterns; given that `FiqhState` and `ChatState` do not share keys, the node-wrapper pattern (Pattern 1 in the verified docs) is the correct approach.

The streaming extension in `pipeline_langgraph.py` follows a fully established pattern: the file already handles `hadith_references` and `quran_references` events; `fiqh_references` is a third instance of the same shape. Token streaming reuses `chain.stream()` with the fiqh-specific prompt from `modules/fiqh/generator.py`. The `SYSTEM_PROMPT` and `_prompt` ChatPromptTemplate are already defined in that module — a streaming variant adds only the generator model binding.

**Primary recommendation:** Use Pattern 1 (compile FiqhState sub-graph, invoke from a wrapper node) because ChatState and FiqhState have no shared keys. Write `FiqhState` as a compact TypedDict (query, iteration, accumulated_docs, prior_queries, sea_result, verdict). Emit status SSE events by adding entries to `NODE_STATUS_MESSAGES` keyed on the sub-graph node names, then emitting them from `pipeline_langgraph.py`'s existing node-event loop.

---

## Standard Stack

### Core (all already installed — no new dependencies required)

| Library | Installed Version | Purpose | Phase 4 Usage |
|---------|------------------|---------|---------------|
| `langgraph` | 0.2.64 (project) / 1.1.3 (latest) | Graph orchestration | Compile FiqhState sub-graph; wire as node in main graph |
| `langchain-core` | 0.3.74 | ChatPromptTemplate, messages | Build streaming prompt chain in `generate_fiqh_response` node |
| `langchain-openai` | 0.3.25 | LLM bindings | `get_generator_model()` for streaming generation |
| `fastapi` / `starlette` | 0.115.8 / 0.45.3 | SSE streaming | `StreamingResponse` + `sse_event()` helper already in place |

**Version note:** The project pins `langgraph==0.2.64`. LangGraph 1.x is production-stable on PyPI (1.1.3 as of 2026-03-24). The 0.2.x sub-graph API used here is compatible with the patterns verified from current docs — `StateGraph`, `compile()`, `add_node()` signatures are stable across both. No upgrade is required or planned for this phase.

**Installation:** No new packages needed. All dependencies are present in `requirements.txt`.

---

## Architecture Patterns

### Sub-graph Composition: Pattern 1 (Node Wrapper)

The verified LangGraph documentation describes two sub-graph patterns:

**Pattern 1 — Call compiled sub-graph inside a node function (use this):**
```python
# When parent and subgraph have DIFFERENT state schemas
def call_fiqh_subgraph(state: ChatState) -> dict:
    result = fiqh_subgraph.invoke({
        "query": state["user_query"],
        "iteration": 0,
        "accumulated_docs": [],
        "prior_queries": [],
        "sea_result": None,
        "verdict": "INSUFFICIENT",
    })
    return {
        "fiqh_filtered_docs": result["accumulated_docs"],
        "fiqh_sea_result": result["sea_result"],
    }

# In _build_graph():
workflow.add_node("fiqh_subgraph", call_fiqh_subgraph)
```

**Pattern 2 — add_node(compiled_graph) directly (do NOT use this):**
```python
builder.add_node("node_2", subgraph)  # Only valid when parent/child share state keys
```

Pattern 1 is correct here because `FiqhState` and `ChatState` have no overlapping keys. The node function is responsible for projecting ChatState → FiqhState input and mapping FiqhState output → ChatState delta.

**Source:** https://docs.langchain.com/oss/python/langgraph/use-subgraphs (verified 2026-03-24)

---

### FiqhState TypedDict (Claude's Discretion — recommended shape)

```python
# agents/state/fiqh_state.py  (new file)
from typing import TypedDict, Optional, List
from modules.fiqh.sea import SEAResult

class FiqhState(TypedDict):
    query: str                         # original fiqh query
    iteration: int                     # current iteration count (0-based, max 3)
    accumulated_docs: List[dict]       # deduplicated docs across iterations
    prior_queries: List[str]           # all queries tried so far (fed to refiner)
    sea_result: Optional[SEAResult]    # latest SEA output (None before first assess)
    verdict: str                       # "SUFFICIENT" | "INSUFFICIENT"
```

The sub-graph nodes write back to these keys. The wrapper node reads `accumulated_docs` and `sea_result` on exit and writes them to `ChatState`.

---

### FiqhAgent Sub-graph: Node and Edge Structure

```
FiqhState
   │
   ▼
decompose_node  ─── retrieve_node
                         │
                    filter_node
                         │
                    assess_node
                     /        \
    (INSUFFICIENT            (SUFFICIENT
     AND iter < 3)            OR iter >= 3)
          │                        │
     refine_node               [EXIT]
          │
      retrieve_node  (loop back)
```

```python
# agents/fiqh/fiqh_graph.py  (new file)
from langgraph.graph import END, StateGraph
from agents.state.fiqh_state import FiqhState

def _route_after_assess(state: FiqhState) -> str:
    if state["verdict"] == "SUFFICIENT" or state["iteration"] >= 3:
        return "exit"
    return "refine"

fiqh_builder = StateGraph(FiqhState)
fiqh_builder.add_node("decompose", _decompose_node)
fiqh_builder.add_node("retrieve", _retrieve_node)
fiqh_builder.add_node("filter", _filter_node)
fiqh_builder.add_node("assess", _assess_node)
fiqh_builder.add_node("refine", _refine_node)

fiqh_builder.set_entry_point("decompose")
fiqh_builder.add_edge("decompose", "retrieve")
fiqh_builder.add_edge("retrieve", "filter")
fiqh_builder.add_edge("filter", "assess")
fiqh_builder.add_conditional_edges(
    "assess",
    _route_after_assess,
    {"exit": END, "refine": "refine"},
)
fiqh_builder.add_edge("refine", "retrieve")

# checkpointer=False: stateless per-invocation (no cross-session leakage, no parallel call issue)
fiqh_subgraph = fiqh_builder.compile(checkpointer=False)
```

**Why `checkpointer=False`:** The sub-graph runs inside a single request; no cross-turn memory is needed at sub-graph level. The parent graph's `MemorySaver` handles cross-turn state. `checkpointer=False` also sidesteps the documented limitation that per-thread subgraphs do not support parallel tool calls. Two concurrent fiqh sessions are isolated because each call to `fiqh_subgraph.invoke()` gets a fresh `FiqhState` dictionary — no shared mutable state exists between invocations.

---

### Expanded Main Graph Routing (D-10)

Current `_route_after_fiqh_check` returns `"exit"` or `"continue"`. Phase 4 expands to three paths:

```python
def _route_after_fiqh_check(
    self, state: ChatState
) -> Literal["fiqh", "exit", "continue"]:
    category = state.get("fiqh_category", "")
    if category in {"VALID_OBVIOUS", "VALID_SMALL", "VALID_LARGE", "VALID_REASONER"}:
        return "fiqh"
    if category in {"OUT_OF_SCOPE_FIQH", "UNETHICAL"}:
        return "exit"
    return "continue"
```

```python
# In _build_graph():
workflow.add_conditional_edges(
    "fiqh_classification",
    self._route_after_fiqh_check,
    {
        "fiqh": "fiqh_subgraph",
        "exit": "check_early_exit",
        "continue": "agent",
    },
)
workflow.add_edge("fiqh_subgraph", "generate_fiqh_response")
workflow.add_edge("generate_fiqh_response", END)
```

---

### Updated `_fiqh_classification_node` (D-09)

```python
def _fiqh_classification_node(self, state: ChatState) -> dict:
    from modules.fiqh.classifier import classify_fiqh_query, VALID_CATEGORIES

    try:
        category = classify_fiqh_query(state["user_query"])
        is_fiqh = category.startswith("VALID_")
        return {
            "fiqh_category": category,
            "is_fiqh": is_fiqh,
            "classification_checked": True,
        }
    except Exception as exc:
        print(f"[FIQH CLASSIFICATION NODE] Error: {exc}")
        return {
            "fiqh_category": "",
            "is_fiqh": False,
            "classification_checked": True,
            "errors": state.get("errors", []) + [f"Fiqh classification error: {str(exc)}"],
        }
```

**Note:** `modules/fiqh/classifier.py::classify_fiqh_query(query: str) -> str` takes only `query` — no `session_id` parameter. The old binary classifier took `(query, session_id)`. This difference is confirmed by reading the Phase 2 source.

---

### ChatState Additions (D-15)

```python
# In agents/state/chat_state.py — add to ChatState TypedDict
fiqh_filtered_docs: List[dict]
"""Final filtered fiqh documents from sub-graph exit"""

fiqh_sea_result: Optional[Any]
"""SEAResult from final sub-graph iteration; None if fiqh path not taken"""
```

```python
# In create_initial_state() — add to return dict
fiqh_filtered_docs=[],
fiqh_sea_result=None,
```

`Optional[Any]` avoids a circular import; the actual type is `SEAResult` from `modules.fiqh.sea`. The planner may choose to import it explicitly if the import chain permits.

---

### `generate_fiqh_response` Node (D-05, D-06, D-08)

This node lives in the main ChatAgent graph. It streams tokens using the fiqh-specific prompt chain. The streaming actually happens in `pipeline_langgraph.py`, not in the node itself — the node stores `final_response` for the non-streaming path; `pipeline_langgraph.py` handles the streaming path analogous to how it handles the existing hadith path (lines 132–172).

**For the non-streaming path** (the node generates the response directly):
```python
def _generate_fiqh_response_node(self, state: ChatState) -> dict:
    from modules.fiqh.generator import _prompt, _format_evidence, _build_references_section
    from modules.fiqh.generator import INSUFFICIENT_WARNING, FATWA_DISCLAIMER
    from core.chat_models import get_generator_model

    docs = state.get("fiqh_filtered_docs", [])
    sea_result = state.get("fiqh_sea_result")
    is_sufficient = getattr(sea_result, "verdict", "INSUFFICIENT") == "SUFFICIENT"

    try:
        model = get_generator_model()
        response = model.invoke(_prompt.format_messages(
            query=state["user_query"],
            evidence=_format_evidence(docs),
        ))
        answer = response.content.strip()
        answer += _build_references_section(answer, docs)
        if not is_sufficient:
            answer += INSUFFICIENT_WARNING
        answer += FATWA_DISCLAIMER
        return {"final_response": answer, "response_generated": True}
    except Exception as exc:
        return {
            "errors": state.get("errors", []) + [f"Fiqh generation error: {str(exc)}"],
            "final_response": "Unable to generate fiqh answer." + FATWA_DISCLAIMER,
        }
```

**For the streaming path** — `pipeline_langgraph.py` detects `fiqh_category in VALID_CATEGORIES` in `final_state`, then runs a separate `chain.stream()` loop using `_prompt` from `generator.py` (D-07):

```python
# In pipeline_langgraph.py response_generator(), after the sub-graph exits:
VALID_FIQH_CATEGORIES = {"VALID_OBVIOUS", "VALID_SMALL", "VALID_LARGE", "VALID_REASONER"}

if final_state.get("fiqh_category") in VALID_FIQH_CATEGORIES:
    from modules.fiqh.generator import _prompt, _format_evidence
    from core.chat_models import get_generator_model

    yield sse_event("status", {"step": "generate_fiqh_response", "message": "Generating fiqh answer..."})
    docs = final_state.get("fiqh_filtered_docs", [])
    model = get_generator_model()
    chain = _prompt | model
    response_tokens = []
    for chunk in chain.stream({"query": user_query, "evidence": _format_evidence(docs)}):
        token = getattr(chunk, "content", str(chunk) if chunk else "")
        if token:
            response_tokens.append(token)
            yield sse_event("response_chunk", {"token": token})
    # ... post-process references, disclaimer, then fiqh_references event
```

This mirrors lines 148–171 of `pipeline_langgraph.py` for the hadith path.

---

### `fiqh_references` SSE Event (D-13, D-14)

The fiqh doc metadata keys from `modules/fiqh/retriever.py` are: `source_book`, `chapter`, `section`, `ruling_number`, `topic_tags`, `text_en`. The SSE event carries just the citation fields:

```python
# In pipeline_langgraph.py, after fiqh answer streams:
def format_fiqh_references_as_json(docs: list) -> list:
    result = []
    for doc in docs:
        md = doc.get("metadata", {}) or {}
        result.append({
            "book": md.get("source_book", "Islamic Laws"),
            "chapter": md.get("chapter", ""),
            "section": md.get("section", ""),
            "ruling_number": md.get("ruling_number", ""),
        })
    return result

fiqh_json = format_fiqh_references_as_json(fiqh_docs)
yield sse_event("fiqh_references", {"references": fiqh_json})
```

This function can live in `core/utils.py` alongside `format_quran_references_as_json` (existing pattern).

---

### LLM-Generated Rejection Messages (D-12)

The `EARLY_EXIT_FIQH` constant in `agents/prompts/agent_prompts.py` is replaced by LLM-generated output. The `_check_early_exit_node` uses `get_classifier_model()` (gpt-4o-mini) for cost efficiency:

```python
def _check_early_exit_node(self, state: ChatState) -> dict:
    if state.get("is_non_islamic"):
        return {"final_response": EARLY_EXIT_NON_ISLAMIC, "early_exit_message": EARLY_EXIT_NON_ISLAMIC}

    category = state.get("fiqh_category", "")
    if category in {"OUT_OF_SCOPE_FIQH", "UNETHICAL"}:
        # LLM-generated personalized rejection (D-12)
        try:
            from core.chat_models import get_classifier_model
            model = get_classifier_model()
            prompt = _build_rejection_prompt(category, state["user_query"])
            response = model.invoke(prompt)
            msg = response.content.strip()
        except Exception:
            msg = "I'm unable to answer this question. For fiqh rulings, please consult a qualified scholar."
        return {"final_response": msg, "early_exit_message": msg}

    return {"final_response": "Unable to process the query."}
```

---

### SSE Status Message Additions (INTG-03)

Add to `NODE_STATUS_MESSAGES` in `pipeline_langgraph.py`:

```python
NODE_STATUS_MESSAGES = {
    # existing entries...
    "fiqh_classification": "Checking query classification...",  # already present
    "fiqh_subgraph": "Processing fiqh query...",
    "generate_fiqh_response": "Generating fiqh answer...",
    # fiqh sub-graph stage names (emitted directly from pipeline_langgraph.py, not node events):
    # "fiqh_decompose", "fiqh_retrieve", "fiqh_filter", "fiqh_assess", "fiqh_refine"
}
```

Because the sub-graph runs inside a wrapper node (Pattern 1), its internal node events are NOT surfaced to the parent `astream()` loop automatically. Status events for decompose/retrieve/filter/assess/refine must be emitted explicitly. The recommended approach: have each sub-graph node write a status key to `FiqhState`, and have the wrapper node yield status SSE events before and after invoking the sub-graph using a step-by-step invocation OR emit them by running nodes one at a time.

**Simpler approach (recommended):** Emit pre-canned status events from the wrapper node before calling `fiqh_subgraph.invoke()`, and detect the step transitions by checking `FiqhState` fields after completion. Alternatively, use streaming on the sub-graph itself (`fiqh_subgraph.stream(...)`) inside the wrapper node to get per-node events — but this requires yielding SSE from inside a non-async function.

**Most practical approach for this codebase:** Add a `status_events: list[dict]` field to `FiqhState`. Each sub-graph node appends `{"step": "fiqh_retrieve", "message": "Retrieving fiqh documents..."}` to this list. The wrapper node reads `status_events` from the completed sub-graph result and stores them in `ChatState`. `pipeline_langgraph.py` flushes them to SSE after the `fiqh_subgraph` node event fires.

---

### Session Isolation (Success Criterion 5)

Each call to `fiqh_subgraph.invoke({...})` constructs a fresh `FiqhState` dict from the node wrapper's inputs. With `checkpointer=False`, the sub-graph has no persistent state store. `FiqhState` is a plain `TypedDict` (immutable values passed by value through the graph). No class-level or module-level mutable state is involved. Two concurrent fiqh sessions invoking the same compiled `fiqh_subgraph` object are fully isolated because:

1. Each invocation receives an independent input dict
2. `checkpointer=False` means no checkpoint store is written or read
3. LangGraph's node execution model creates a new state copy per run

**Verified:** This isolation property follows directly from how Python dicts work and from the LangGraph documented behavior: "Each call starts fresh" for `checkpointer=None` (per-invocation default).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sub-graph state loop | Custom recursion or while-loop | LangGraph `StateGraph` with conditional edges | State transitions, error handling, and checkpointing all handled; loop termination is declarative |
| SSE fiqh references format | New formatter class | Add `format_fiqh_references_as_json()` to `core/utils.py` alongside existing `format_quran_references_as_json()` | Exact same 4-line pattern; already has error handling |
| Streaming token loop | New generator function | Reuse existing `chain.stream()` loop in `pipeline_langgraph.py` | Pattern already handles token concatenation, `response_end`, and `history_written` flag |
| LLM rejection messages | Hardcoded string bank | Single `model.invoke()` with personalized prompt | One call with gpt-4o-mini; context-aware phrasing |
| Fiqh doc deduplication in sub-graph | Set-based deduplication in wrapper | Implement `seen_chunk_ids: set` inside `_retrieve_node` updating `accumulated_docs` | Sub-graph already has explicit iteration state; dedup is 3 lines |

---

## Common Pitfalls

### Pitfall 1: Wrong Sub-graph Pattern (Pattern 2 When 1 Is Required)
**What goes wrong:** Using `workflow.add_node("fiqh_subgraph", compiled_fiqh_subgraph)` directly when the two state schemas share no keys — LangGraph tries to map keys by name and either silently drops all output or raises a KeyError.
**Why it happens:** Pattern 2 (direct node addition) requires overlapping state keys between parent and child. `ChatState` and `FiqhState` have no shared keys by design.
**How to avoid:** Always use Pattern 1 (wrapper node function) when schemas differ. The wrapper explicitly projects state in and out.
**Warning signs:** Sub-graph completes but `fiqh_filtered_docs` stays empty in `ChatState`.

### Pitfall 2: checkpointer Conflict — Sub-graph Inherits Parent's MemorySaver
**What goes wrong:** Compiling the sub-graph without specifying `checkpointer` means it inherits the parent graph's `MemorySaver`. Under concurrent load, two sessions writing to the same sub-graph namespace will overwrite each other's checkpoint.
**Why it happens:** Default LangGraph behavior for nested graphs is to inherit the parent checkpointer.
**How to avoid:** Explicitly pass `checkpointer=False` when compiling the fiqh sub-graph. This makes each invocation stateless and inherently concurrent-safe.
**Warning signs:** One session's retrieved docs appear in another session's response; session B gets answers clearly about session A's query.

### Pitfall 3: Fiqh Classifier Signature Change
**What goes wrong:** Calling `classify_fiqh_query(state["user_query"], state["runtime_session_id"])` in the new `_fiqh_classification_node`. The old binary classifier took two args; Phase 2's `modules/fiqh/classifier.py::classify_fiqh_query(query: str)` takes only one.
**Why it happens:** The CONTEXT.md and Phase 2 source both confirm the new signature, but the existing `_fiqh_classification_node` code calls the old two-argument form. Copy-paste from existing code propagates the bug.
**How to avoid:** Import from `modules.fiqh.classifier`, not `modules.classification.classifier`. Confirmed in Phase 2 source: `def classify_fiqh_query(query: str) -> str`.
**Warning signs:** `TypeError: classify_fiqh_query() takes 1 positional argument but 2 were given`.

### Pitfall 4: Streaming Path Never Detects Fiqh Category
**What goes wrong:** `pipeline_langgraph.py` checks `final_state.get("early_exit_message")` first. If `check_early_exit` sets `early_exit_message` for a valid fiqh query (routing bug), the pipeline serves the early-exit path and never streams the fiqh answer.
**Why it happens:** Current `_check_early_exit_node` sets `final_response = EARLY_EXIT_FIQH` for any `is_fiqh=True` state. After Phase 4, valid fiqh queries (`VALID_*`) must never reach `check_early_exit`. Only `OUT_OF_SCOPE_FIQH` / `UNETHICAL` should.
**How to avoid:** Verify routing: after `fiqh_classification`, `VALID_*` categories go to `fiqh_subgraph`, not `check_early_exit`. Add assertion in tests that valid fiqh queries produce `early_exit_message=None`.
**Warning signs:** Valid fiqh query returns the static early-exit string rather than a FAIR-RAG answer.

### Pitfall 5: `fiqh_filtered_docs` Not Populated When Sub-graph Errors
**What goes wrong:** If any sub-graph node raises unexpectedly (e.g., Pinecone timeout), the wrapper node catches the exception and returns an empty `fiqh_filtered_docs`. The `generate_fiqh_response` node then generates with no evidence, producing a disclaimer-only response without raising a visible error.
**Why it happens:** All Phase 3 module functions are documented as "never raises" — they return empty/fallback values. But a complete sub-graph failure (OOM, import error) bypasses those fallbacks.
**How to avoid:** The wrapper node should catch `Exception`, append to `state["errors"]`, and return `{"fiqh_filtered_docs": [], "fiqh_sea_result": None}`. The generation node then checks `len(fiqh_filtered_docs) == 0` and can return a "no evidence" message rather than calling the LLM pointlessly.
**Warning signs:** Empty `fiqh_filtered_docs` in state but no `errors` entry explaining why.

### Pitfall 6: Token Streaming Blocks Event Loop
**What goes wrong:** `chain.stream()` is a synchronous iterator called inside `async def response_generator()`. Each call to `next()` on the sync iterator blocks the event loop briefly.
**Why it happens:** This is pre-existing behavior (lines 158–171 of `pipeline_langgraph.py`) and is documented in `CLAUDE.md` under "Async vs Sync Patterns". Fiqh generation using the same pattern inherits the same characteristic.
**How to avoid:** This is an accepted tradeoff in the existing codebase. Do not attempt to "fix" it as part of Phase 4 — it is out of scope per CLAUDE.md conventions. Match the existing pattern exactly.
**Warning signs:** N/A — this is expected behavior, not a bug.

---

## Code Examples

### Pattern 1 Sub-graph Invocation (Verified from Official Docs)

```python
# Source: https://docs.langchain.com/oss/python/langgraph/use-subgraphs
# Pattern 1: call compiled subgraph inside a node function (different schemas)
def call_subgraph(state: State):
    subgraph_output = subgraph.invoke({"bar": state["foo"]})
    return {"foo": subgraph_output["bar"]}

builder = StateGraph(State)
builder.add_node("node_1", call_subgraph)
```

### Stateless Sub-graph Compilation

```python
# Source: https://docs.langchain.com/oss/python/langgraph/use-subgraphs
subgraph = builder.compile(checkpointer=False)
# Runs like a plain function call — no checkpointing overhead, no cross-invocation state
```

### Streaming with Subgraphs (informational — not used in this phase)

```python
# Source: https://docs.langchain.com/oss/python/langgraph/streaming
# If sub-graph were added directly as a node (Pattern 2), streaming with subgraphs=True
# surfaces internal node events via the ns field:
for chunk in graph.stream(input, subgraphs=True, stream_mode="updates", version="v2"):
    print(chunk["ns"])    # () for parent, ("node_name:<task_id>",) for subgraph
    print(chunk["data"])
# NOT used here because Phase 4 uses Pattern 1 (wrapper node), so sub-graph
# events are NOT automatically surfaced. Status events must be injected manually.
```

### Existing SSE Reference Event Pattern (lines 195–201 of pipeline_langgraph.py)

```python
# Source: core/pipeline_langgraph.py lines 195–201
if hadith_docs:
    hadith_json = utils.format_references_as_json(hadith_docs)
    yield sse_event("hadith_references", {"references": hadith_json})

if quran_docs:
    quran_json = utils.format_quran_references_as_json(quran_docs)
    yield sse_event("quran_references", {"references": quran_json})
```

The `fiqh_references` event follows this exact pattern.

### Existing Token Streaming Pattern (lines 146–172 of pipeline_langgraph.py)

```python
# Source: core/pipeline_langgraph.py lines 148–171
yield sse_event("status", {"step": "generate_response", "message": "Generating response..."})
references = utils.compact_format_references(all_docs)
chat_model = chat_models.get_generator_model()
prompt = prompt_templates.generator_prompt_template
chain = prompt | chat_model
# ...
for chunk in chain.stream({...}):
    token = getattr(chunk, "content", str(chunk) if chunk is not None else "")
    if token:
        response_tokens.append(token)
        yield sse_event("response_chunk", {"token": token})
assistant_text = "".join(response_tokens).strip()
yield sse_event("response_end", {})
```

The fiqh path replaces `prompt_templates.generator_prompt_template` with `_prompt` from `modules/fiqh/generator.py` and `references` with `_format_evidence(fiqh_docs)`.

---

## Files to Modify and Create

### Files to Modify (surgical edits)

| File | What Changes |
|------|-------------|
| `agents/state/chat_state.py` | Add `fiqh_filtered_docs: List[dict]` and `fiqh_sea_result: Optional[Any]` to `ChatState`; update `create_initial_state()` defaults |
| `agents/core/chat_agent.py` | Replace `_fiqh_classification_node` body; expand `_route_after_fiqh_check` to 3 paths; add `generate_fiqh_response` node; update `_check_early_exit_node` to LLM-generated rejections; update `_build_graph()` edges |
| `core/pipeline_langgraph.py` | Add fiqh path detection after `astream` loop; add fiqh token streaming; add `fiqh_references` SSE event; add fiqh stage to `NODE_STATUS_MESSAGES` |
| `core/utils.py` | Add `format_fiqh_references_as_json()` function |
| `agents/prompts/agent_prompts.py` | `EARLY_EXIT_FIQH` constant is superseded (kept for import safety; node no longer uses it for valid fiqh) |

### Files to Create (new)

| File | Purpose |
|------|---------|
| `agents/state/fiqh_state.py` | `FiqhState` TypedDict definition |
| `agents/fiqh/fiqh_graph.py` | Compiled `fiqh_subgraph` with node functions and conditional edge router |
| `tests/test_fiqh_integration.py` | Integration tests: routing, state isolation, SSE event sequence |

---

## Environment Availability

Step 2.6: SKIPPED — Phase 4 is a pure code integration. No new external dependencies are introduced. All tools, services, and runtimes (Pinecone, OpenAI, Redis, PostgreSQL) were provisioned in Phases 1–3 and remain unchanged.

---

## Validation Architecture

`workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`. Validation Architecture section is omitted per config.

---

## Open Questions

1. **Sub-graph status events granularity**
   - What we know: Pattern 1 (wrapper node) does not automatically surface sub-graph node events to the parent `astream()` loop. Status events for decompose/retrieve/filter/assess/refine must be injected manually.
   - What's unclear: The cleanest mechanism — `status_events` list in `FiqhState` vs. running `fiqh_subgraph.stream()` inside the wrapper vs. using `subgraphs=True` only if we switch to Pattern 2.
   - Recommendation: Use a `status_events: list[dict]` field in `FiqhState`. Each node appends its status. The wrapper node writes them to `ChatState` as `fiqh_status_events`. `pipeline_langgraph.py` emits them when processing the `fiqh_subgraph` node event. This is the most explicit and testable approach.

2. **`generate_fiqh_response` node vs. pipeline-only streaming**
   - What we know: D-05/D-06 call for a node in the main graph. D-07 says the streaming happens in `pipeline_langgraph.py`. The non-streaming path (`/chat/agentic`) needs the node to actually produce `final_response`.
   - What's unclear: Whether the node should call `generate_answer()` (non-streaming) and `pipeline_langgraph.py` then duplicates the streaming call — risking double invocation.
   - Recommendation: The node is responsible for the non-streaming path only (calls `generate_answer()`). `pipeline_langgraph.py` in streaming mode detects `fiqh_category in VALID_CATEGORIES` and uses `chain.stream()` directly — exactly as it does today for the hadith path where `final_response` is never populated under `streaming_mode=True`. No double invocation occurs because `streaming_mode=True` causes `generate_fiqh_response` node to be skipped (same mechanism as `generate_response` node for the existing path).

   **Confirmed mechanism:** `_should_continue` already returns `"end"` (skipping `generate_response`) when `streaming_mode=True`. The same flag will skip `generate_fiqh_response` if the router is wired identically. The planner must verify whether `generate_fiqh_response` needs its own `streaming_mode` check or if the edge structure naturally bypasses it.

3. **`fiqh_sea_result` type annotation in ChatState**
   - What we know: `SEAResult` is a Pydantic `BaseModel` from `modules/fiqh/sea.py`. Importing it in `agents/state/chat_state.py` creates a dependency from `agents/` into `modules/`.
   - What's unclear: Whether this cross-layer import violates any existing convention (none found in CLAUDE.md, but `agents/` currently does not import from `modules/fiqh/` directly — only via `agents/tools/`).
   - Recommendation: Use `Optional[Any]` with a docstring noting the actual type. Avoids the import; the node functions that read/write it will have the typed import locally. Alternatively, `Optional[dict]` if SEAResult is serialized to dict before storing.

---

## Sources

### Primary (HIGH confidence)
- https://docs.langchain.com/oss/python/langgraph/use-subgraphs — Sub-graph patterns, Pattern 1 vs Pattern 2, `checkpointer=False` semantics, state isolation (fetched 2026-03-24)
- https://docs.langchain.com/oss/python/langgraph/streaming — `subgraphs=True`, `version="v2"`, namespace fields for sub-graph events (fetched 2026-03-24)
- `core/pipeline_langgraph.py` (project source) — SSE event emission pattern, token streaming loop, reference event pattern
- `agents/core/chat_agent.py` (project source) — Existing graph structure, routing functions, node signatures
- `agents/state/chat_state.py` (project source) — Existing state fields, `create_initial_state()` factory
- `modules/fiqh/classifier.py` (project source) — `classify_fiqh_query(query: str)` signature confirmed (single arg)
- `modules/fiqh/generator.py` (project source) — `_prompt`, `_format_evidence`, `SYSTEM_PROMPT`, `generate_answer()` confirmed
- `modules/fiqh/retriever.py` (project source) — Metadata keys: `source_book`, `chapter`, `section`, `ruling_number`
- `modules/fiqh/sea.py` (project source) — `SEAResult` model with `verdict`, `confirmed_facts`, `gaps` fields

### Secondary (MEDIUM confidence)
- https://pypi.org/pypi/langgraph/json — LangGraph 1.1.3 is the current stable release (fetched 2026-03-24)
- WebSearch results — sub-graph state isolation, thread safety, concurrent session patterns

---

## Metadata

**Confidence breakdown:**
- Sub-graph API patterns: HIGH — verified against official LangChain docs fetched 2026-03-24
- Routing and state changes: HIGH — derived directly from reading existing source files
- SSE extension: HIGH — existing pipeline pattern is well-understood and already handles 2 reference event types
- Status event injection for Pattern 1: MEDIUM — no official example of manual status injection from wrapper node; approach is pragmatic but planner should validate
- Session isolation: HIGH — `checkpointer=False` + immutable TypedDict semantics are clearly documented

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable domain — LangGraph core API, existing project patterns)
