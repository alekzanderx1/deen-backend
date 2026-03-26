# Architecture Patterns: Fiqh Agentic RAG (FAIR-RAG Sub-Graph)

**Domain:** Agentic RAG for religious/legal Q&A — specifically FAIR-RAG iterative pipeline
integrated as a LangGraph sub-graph into an existing Islamic education FastAPI backend
**Researched:** 2026-03-23
**Confidence:** HIGH (based on existing codebase analysis + FAIR-RAG / FARSIQA documentation)

---

## Recommended Architecture

The FAIR-RAG system lives as a **LangGraph sub-graph** that the main `ChatAgent` routes into
when the fiqh classifier fires. The main agent's existing `fiqh_classification` → `check_early_exit`
path currently issues a hard rejection. That rejection is replaced by a hand-off to the FAIR-RAG
sub-graph that performs the full iterative retrieval-assessment loop before generating a grounded
answer.

### High-Level System Shape

```
POST /chat/stream/agentic
    │
    ▼
api/chat.py
    │
    ▼
core/pipeline_langgraph.py               ← unchanged orchestrator
    │
    ▼
agents/core/chat_agent.py (main graph)
    │
    [fiqh_classification node]  ← UPGRADED: new FiqhClassifier replaces old binary check
    │
    ├── NOT fiqh → [agent node] (existing hadith/Quran retrieval path, unchanged)
    │
    └── IS fiqh → [fiqh_subgraph node]  ← NEW: wraps FiqhAgent as a compiled sub-graph
                      │
                      ▼
              agents/fiqh/fiqh_agent.py   ← NEW: StateGraph(FiqhState)
                      │
                      [validate_and_route]
                      │
                      ├── OBVIOUS/OUT_OF_SCOPE → [fiqh_early_exit] → END
                      │
                      └── VALID → [decompose_query]
                                      │
                                      ▼
                              ┌─────────────────────────────────┐
                              │       ITERATIVE LOOP (max 3)    │
                              │                                 │
                              │  [retrieve]                     │
                              │   Dense + Sparse → RRF          │
                              │   (fiqh Pinecone indexes)       │
                              │        │                        │
                              │  [filter_evidence]              │
                              │   gpt-4.1 — inclusive filter    │
                              │        │                        │
                              │  [assess_evidence] (SEA)        │
                              │   gpt-4o-mini — checklist audit │
                              │        │                        │
                              │   sufficient?                   │
                              │   ├── YES → exit loop           │
                              │   └── NO  → [refine_queries]    │
                              │              gpt-4.1            │
                              │              └── back to        │
                              │                 [retrieve]      │
                              └─────────────────────────────────┘
                                      │
                              [generate_answer]
                               gpt-4.1, strict grounding,
                               inline citations, disclaimer
                                      │
                                      END

    ▼ (back in pipeline_langgraph.py)
SSE streaming: status, fiqh_status, response_chunk, fiqh_references, done
```

---

## Component Boundaries

### Existing Components (Unchanged or Lightly Modified)

| Component | Responsibility | What Changes |
|-----------|---------------|--------------|
| `api/chat.py` | HTTP route handler, auth, DB persistence | No change — fiqh response persists via same `wrap_streaming_response_for_persistence` path |
| `core/pipeline_langgraph.py` | SSE event translation, streaming orchestration | Add `fiqh_status` and `fiqh_references` SSE event types; add fiqh sub-graph status messages to `NODE_STATUS_MESSAGES` |
| `agents/core/chat_agent.py` | Main LangGraph graph | Replace `check_early_exit` path for fiqh with call to `FiqhAgent.invoke()` or `FiqhAgent.astream()` inside a new `fiqh_subgraph` node |
| `agents/state/chat_state.py` | Per-request state TypedDict | Add `fiqh_result: Optional[FiqhResult]` field for carrying sub-graph output back to pipeline |
| `modules/retrieval/retriever.py` | Pinecone hybrid search | Reused — fiqh retriever calls the same module but with fiqh-specific index names and RRF merge logic |
| `core/vectorstore.py` | Pinecone client init | Reused — fiqh indexes added as new named indexes via existing `_get_vectorstore` / `_get_sparse_vectorstore` helpers |

### New Components

| Component | Location | Responsibility | Communicates With |
|-----------|----------|---------------|-------------------|
| `FiqhClassifier` | `modules/classification/fiqh_classifier.py` | Upgraded classifier — outputs typed category (`VALID_OBVIOUS`, `VALID_SMALL`, `VALID_LARGE`, `OUT_OF_SCOPE_FIQH`, `UNETHICAL`) not a binary bool. Uses `gpt-4o-mini`. | Called from `agents/core/chat_agent.py` `_fiqh_classification_node` |
| `FiqhState` | `agents/fiqh/fiqh_state.py` | TypedDict for all FAIR-RAG state: sub-queries, accumulated evidence, SEA checklist, iteration count, confirmed facts, gaps, sufficiency verdict | Owned by `FiqhAgent` sub-graph |
| `FiqhAgent` | `agents/fiqh/fiqh_agent.py` | Compiled `StateGraph(FiqhState)` — full FAIR-RAG loop as LangGraph nodes | Calls `FiqhRetriever`, `FiqhEvidenceFilter`, `SEAModule`, `QueryRefiner`, `FiqhGenerator` |
| `FiqhRetriever` | `modules/fiqh/retriever.py` | Hybrid Pinecone search (dense + sparse) → RRF merge. Top-3 per retriever → RRF → top-5 per sub-query. | `core/vectorstore.py` (fiqh indexes), `modules/embedding/embedder.py` |
| `FiqhEvidenceFilter` | `modules/fiqh/evidence_filter.py` | gpt-4.1 agent — batch reviews retrieved docs against original user query. Inclusive by design (removes only clearly irrelevant). | Receives doc list + user query; returns filtered doc list |
| `SEAModule` | `modules/fiqh/sea_module.py` | gpt-4o-mini — Structured Evidence Assessment. Deconstructs query into required-findings checklist, checks each against evidence, produces `confirmed_facts`, `gaps`, `sufficient` verdict | Receives accumulated evidence + user query; writes into `FiqhState` |
| `QueryRefiner` | `modules/fiqh/query_refiner.py` | gpt-4.1 — generates 1-4 targeted refinement sub-queries using confirmed facts to add precision. Never repeats prior queries. | Reads `confirmed_facts`, `gaps` from `FiqhState`; writes new `sub_queries` |
| `FiqhGenerator` | `modules/fiqh/generator.py` | gpt-4.1 — faithful answer generation. Strict evidence-only grounding, inline citations `[n]`, mandatory fatwa disclaimer, partial-answer path on exhausted iterations. | Reads accumulated `evidence_docs` + `user_query` from `FiqhState`; writes `final_answer` + `citations` |
| `DataIngestionPipeline` | `scripts/ingest_fiqh.py` | One-time (and re-runnable) pipeline: PDF parse → paragraph-boundary chunking (300-400 tokens) → dense + sparse embeddings → Pinecone upload. Adds chapter/section/topic metadata per chunk. | `documentation/fiqh_related_docs/english-islamic-laws-4th-edition.pdf` → Pinecone fiqh indexes |

---

## Data Flow

### 1. Request Entry and Routing

```
Client POST /chat/stream/agentic  {query: "Is fasting obligatory for a traveler?"}
    │
api/chat.py
    → optional JWT user_id extraction
    → hydrate Redis history from DB (if user authenticated)
    → call core/pipeline_langgraph.py :: chat_pipeline_streaming_agentic()
    │
ChatAgent.astream(streaming_mode=True)
    │
[fiqh_classification node]
    → FiqhClassifier.classify(user_query)    ← gpt-4o-mini
    → returns: {category: "VALID_LARGE", is_fiqh: True}
    → state["fiqh_category"] = "VALID_LARGE"
    → state["is_fiqh"] = True
    │
_route_after_fiqh_check()
    → is_fiqh=True → route to "fiqh_subgraph"
```

### 2. FAIR-RAG Sub-Graph Execution

```
[fiqh_subgraph node] in ChatAgent
    → create FiqhState from ChatState fields
    → FiqhAgent.astream(fiqh_state)           ← compiled sub-graph
    │
[validate_and_route node]
    → already classified VALID_LARGE; confirm not OBVIOUS/OUT_OF_SCOPE
    → set fiqh_state["llm_size"] = "large"
    │
[decompose_query node]
    → gpt-4o-mini
    → input:  user_query
    → output: sub_queries = [
        "Sistani ruling fasting traveler",
        "Conditions fasting obligatory traveler Islam",
        "Traveler prayer salah fasting exception",
        "Sawm qasr traveler Shia fiqh"
      ]
    → fiqh_state["sub_queries"] = sub_queries
    → fiqh_state["iteration"] = 1
    │
    ┌── ITERATION LOOP ──────────────────────────────────────────────────┐
    │                                                                    │
    │  [retrieve node]                                                   │
    │    → for each sub_query in fiqh_state["sub_queries"]:             │
    │        dense_results = FiqhRetriever.dense_search(sub_q, top_k=3) │
    │        sparse_results = FiqhRetriever.sparse_search(sub_q, top_k=3│
    │        merged = RRF_merge(dense_results, sparse_results, k=60)    │
    │        top_5 = merged[:5]                                          │
    │    → fiqh_state["candidate_docs"] += deduplicated top_5 per query │
    │                                                                    │
    │  [filter_evidence node]                                            │
    │    → gpt-4.1                                                       │
    │    → input:  candidate_docs (batch) + original user_query         │
    │    → output: filtered_docs (only clearly irrelevant removed)       │
    │    → fiqh_state["accumulated_evidence"] += filtered_docs          │
    │                                                                    │
    │  [assess_evidence node] (SEA)                                      │
    │    → gpt-4o-mini                                                   │
    │    → input:  user_query + accumulated_evidence                    │
    │    → Step 1: deconstruct query → required_findings checklist      │
    │    → Step 2: check each finding against evidence                  │
    │      confirmed_facts: ["Traveler must shorten prayers (qasr)..."] │
    │      gaps: ["No evidence found on 10-day stay fasting rule"]      │
    │    → Step 3: sufficient verdict                                    │
    │    → writes: fiqh_state["confirmed_facts"],                       │
    │              fiqh_state["gaps"],                                   │
    │              fiqh_state["sufficient"]                              │
    │                                                                    │
    │  _route_after_sea():                                               │
    │    sufficient=True → exit loop → [generate_answer]                │
    │    sufficient=False AND iteration < 3 →                           │
    │                                                                    │
    │  [refine_queries node]                                             │
    │    → gpt-4.1                                                       │
    │    → input: confirmed_facts + gaps + prior sub_queries            │
    │    → output: new targeted sub_queries (1-4), no repeats           │
    │    → fiqh_state["sub_queries"] = new_sub_queries                  │
    │    → fiqh_state["iteration"] += 1                                 │
    │    → loop back to [retrieve node]                                 │
    │                                                                    │
    │  sufficient=False AND iteration == 3 → force exit to generate    │
    └────────────────────────────────────────────────────────────────────┘
    │
    [generate_answer node]
    → gpt-4.1
    → input: user_query + accumulated_evidence (all iterations)
    → if sufficient: full grounded answer with inline citations [n]
    → if not sufficient: partial answer + "insufficient evidence" warning
    → ALWAYS append fatwa disclaimer
    → writes: fiqh_state["final_answer"], fiqh_state["citations"]
    │
    END (FiqhAgent sub-graph)
    │
[fiqh_subgraph node] (back in ChatAgent)
    → copy fiqh_state["final_answer"] → chat_state["early_exit_message"]
    → copy fiqh_state["citations"] → chat_state["fiqh_citations"]
    → route to check_early_exit → END
```

### 3. SSE Streaming Back to Client

```
core/pipeline_langgraph.py :: response_generator() (async generator)
    │
    → async for event in agent.astream():
        node_name = "fiqh_subgraph" → emit status: "Researching Fiqh ruling..."
        node_name = "fiqh_decompose" → emit fiqh_status: "Decomposing query..."
        node_name = "fiqh_retrieve"  → emit fiqh_status: "Retrieving Fiqh sources (iteration N)..."
        node_name = "fiqh_sea"       → emit fiqh_status: "Assessing evidence sufficiency..."
        node_name = "fiqh_refine"    → emit fiqh_status: "Refining search queries..."
    │
    → final_state["early_exit_message"] is set (by fiqh path)
    → yields response_chunk tokens (final_answer, streamed)
    → yields response_end
    → yields fiqh_references: [{text, source_book, chapter, section, citation_num}]
    → yields done
```

### SSE Event Protocol (Augmented for Fiqh)

| Event Type | Payload | When Emitted |
|-----------|---------|-------------|
| `status` | `{step, message}` | Per main graph node (existing) |
| `fiqh_status` | `{step, message, iteration}` | Per FAIR-RAG loop stage — NEW |
| `response_chunk` | `{token}` | Per LLM token of final answer |
| `response_end` | `{}` | After last token |
| `fiqh_references` | `[{text, source_book, chapter, section, citation_num}]` | After response_end — NEW |
| `hadith_references` | `[...]` | Existing (not emitted on fiqh path) |
| `quran_references` | `[...]` | Existing (not emitted on fiqh path) |
| `error` | `{message}` | On any unhandled exception |
| `done` | `{}` | Terminal event |

---

## State Management

### FiqhState TypedDict (New)

Lives inside the FAIR-RAG sub-graph for the duration of one fiqh query. Does NOT persist to Redis or PostgreSQL independently — the final answer text flows back into `ChatState` and follows the existing Redis + Postgres persistence path.

```python
class FiqhState(TypedDict):
    # Input
    user_query: str
    fiqh_category: str            # VALID_SMALL | VALID_LARGE | VALID_OBVIOUS

    # Decomposition
    sub_queries: List[str]        # Current iteration's sub-queries (1-4)
    all_prior_queries: List[str]  # All sub-queries ever used (for dedup)

    # Retrieval
    candidate_docs: List[FiqhDoc] # Raw retrieved docs this iteration
    accumulated_evidence: List[FiqhDoc]  # All filtered docs across iterations

    # SEA Output
    required_findings: List[str]  # Checklist derived from user_query
    confirmed_facts: List[str]    # Facts confirmed by evidence
    gaps: List[str]               # Missing findings (actionable search targets)
    sufficient: bool              # SEA verdict

    # Loop control
    iteration: int                # Current iteration (1-3)
    max_iterations: int           # Hard cap (3)

    # Output
    final_answer: Optional[str]
    citations: List[FiqhCitation] # [{citation_num, text_snippet, source_book, chapter}]
    is_partial_answer: bool       # True if evidence was insufficient at loop exit
    errors: List[str]
```

### ChatState Extension (Minimal)

Add to existing `ChatState`:

```python
fiqh_category: Optional[str]     # Typed classification result from upgraded classifier
fiqh_citations: List[Dict]       # Carried from FiqhState for SSE emission
```

The existing `early_exit_message` field carries the final fiqh answer text, and the existing
`chat_persistence_service.append_turn_to_runtime_history()` call persists it to Redis + Postgres
without modification.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Folding FAIR-RAG into the Existing Agent Tool Loop
**What:** Adding decompose/SEA/refine as new `@tool` decorators alongside the existing retrieval tools, letting the main LLM agent "decide" when to call them.
**Why bad:** The existing agent uses free-form tool-calling LLM decisions. FAIR-RAG requires a structured, deterministic loop — SEA must always follow retrieval, refinement must always follow a "gaps found" verdict. An LLM agent won't reliably enforce this sequence.
**Instead:** Compile FAIR-RAG as a separate `StateGraph(FiqhState)` with explicit edges and routing functions. The main `ChatAgent` calls it as a black-box node, not as a tool.

### Anti-Pattern 2: Sharing the Fiqh and Hadith Pinecone Indexes
**What:** Storing fiqh book chunks in the same Pinecone index as hadith/Quran documents.
**Why bad:** Mixed-corpus retrieval introduces irrelevant hadith noise into fiqh evidence. Fiqh queries need a clean, isolated index that returns Sistani-book passages only. Cross-contamination degrades the filtering and SEA steps.
**Instead:** Dedicate two new Pinecone indexes (`FIQH_DENSE_INDEX_NAME`, `FIQH_SPARSE_INDEX_NAME`) for fiqh content only. Reference them via the existing `core/vectorstore.py` helpers.

### Anti-Pattern 3: Streaming LLM Tokens Inside the Sub-Graph
**What:** Running `chain.stream()` inside a LangGraph node to yield tokens from within the sub-graph.
**Why bad:** LangGraph nodes return state, they don't yield to the pipeline's async generator. Streaming must happen at the orchestration layer (`pipeline_langgraph.py`), not inside graph nodes.
**Instead:** The `[generate_answer]` node calls `llm.invoke()` (non-streaming) to produce `FiqhState["final_answer"]`. The `chat_pipeline_streaming_agentic()` orchestrator then reads `final_answer` from the returned state and streams it token-by-token via `chain.stream()` exactly as it does today for the non-fiqh path.

### Anti-Pattern 4: Over-Filtering Evidence
**What:** Aggressive evidence filter that removes any document without an explicit Sistani ruling.
**Why bad:** FARSIQA reports filtering F1 of 55-76% — the filter is imperfect. Over-filtering removes marginally-relevant context that the SEA module would have correctly assessed. This shifts errors from the SEA stage (which can trigger another retrieval loop) to the filter stage (which is a one-way gate).
**Instead:** Filter only clearly irrelevant documents (wrong scholar, completely different topic). When in doubt, keep. The SEA module is the correctness gate, not the filter.

### Anti-Pattern 5: Re-Using the Same Binary `is_fiqh` Check
**What:** Keeping the current `classify_fiqh_query()` that returns a boolean and immediately exits.
**Why bad:** The existing classifier only routes to a hard exit. The new system needs typed categories (`VALID_SMALL`, `VALID_LARGE`, `OUT_OF_SCOPE_FIQH`, etc.) to (a) drive dynamic LLM allocation and (b) distinguish questions to route to the FAIR-RAG loop from those to hard-reject.
**Instead:** Replace `classify_fiqh_query()` with `FiqhClassifier.classify()` that returns a typed `FiqhCategory` enum. The main graph routing function reads category to decide between FAIR-RAG entry vs hard rejection vs obvious-answer shortcut.

---

## Build Order (Dependencies Between Components)

The components have a hard dependency chain. Build in this order:

### Layer 0: Data Foundation (must come first, everything else depends on it)
1. **`scripts/ingest_fiqh.py`** — PDF parsing, chunking (300-400 tokens, paragraph-boundary), dense + sparse embedding, Pinecone upload. Requires: the two new Pinecone index names in `.env`.
2. **Pinecone fiqh indexes** — Create `FIQH_DENSE_INDEX_NAME` and `FIQH_SPARSE_INDEX_NAME` in Pinecone dashboard. Add env vars.

No downstream component can be meaningfully tested without a populated fiqh corpus.

### Layer 1: Retrieval Module (depends on Layer 0)
3. **`modules/fiqh/retriever.py`** (`FiqhRetriever`) — Dense + sparse search + RRF merge. Depends on: Pinecone indexes (Layer 0), `core/vectorstore.py` (existing), `modules/embedding/embedder.py` (existing).

### Layer 2: FAIR-RAG Modules (can be built in parallel once Layer 1 is done)
4. **`modules/fiqh/evidence_filter.py`** (`FiqhEvidenceFilter`) — Depends on: OpenAI gpt-4.1. No retrieval dependency; can be unit-tested with synthetic doc lists.
5. **`modules/fiqh/sea_module.py`** (`SEAModule`) — Depends on: OpenAI gpt-4o-mini. No retrieval dependency; can be unit-tested with canned evidence sets.
6. **`modules/fiqh/query_refiner.py`** (`QueryRefiner`) — Depends on: OpenAI gpt-4.1. No retrieval dependency.
7. **`modules/fiqh/generator.py`** (`FiqhGenerator`) — Depends on: OpenAI gpt-4.1. No retrieval dependency.

### Layer 3: FiqhState and FiqhAgent Sub-Graph (depends on Layers 1 + 2)
8. **`agents/fiqh/fiqh_state.py`** (`FiqhState`) — Pure TypedDict, no dependencies.
9. **`agents/fiqh/fiqh_agent.py`** (`FiqhAgent`) — Assembles the full `StateGraph(FiqhState)`. Depends on Layers 1 + 2.

### Layer 4: Upgraded Classifier (can be developed in parallel with Layers 1-3)
10. **`modules/classification/fiqh_classifier.py`** (`FiqhClassifier`) — Replaces binary `classify_fiqh_query`. Depends on: OpenAI gpt-4o-mini. No retrieval dependency.

### Layer 5: Main Agent Integration (depends on Layers 3 + 4)
11. **`agents/core/chat_agent.py` modifications** — Add `fiqh_subgraph` node; wire `_route_after_fiqh_check` to route `is_fiqh=True` to `fiqh_subgraph` instead of `check_early_exit`. Extend `ChatState` with `fiqh_category` and `fiqh_citations`.

### Layer 6: SSE Streaming Integration (depends on Layer 5)
12. **`core/pipeline_langgraph.py` modifications** — Add `fiqh_status` event type, extend `NODE_STATUS_MESSAGES` dict for FAIR-RAG nodes, add `fiqh_references` SSE event after `response_end`.

### Layer 7: End-to-End Validation
13. **`tests/test_fiqh_pipeline.py`** — Integration tests: scope routing accuracy, SEA sufficiency verdicts, negative rejection rate, citation format. Agent tests: full fiqh query through to SSE events.

---

## Scalability Considerations

| Concern | At Current Scale | At Scale |
|---------|-----------------|----------|
| Pinecone latency per sub-query | ~100-300ms per query × 4 sub-queries × 3 iterations = up to 3.6s retrieval time | Use batch retrieval per iteration; parallelize sub-query lookups within one iteration call |
| LLM cost per fiqh request | gpt-4o-mini for routing/decompose/SEA + gpt-4.1 for filter/refine/generate ≈ $0.0025/query (FARSIQA dynamic config) | Dynamic LLM allocation already handles this; cache obvious-answer responses at query level |
| Iteration count | Max 3 — SEA exits early for simple queries (often after 1 iteration) | Hard cap enforced in `FiqhState["max_iterations"]`; simple lookup queries rarely exceed 1 loop |
| Memory/state size | `FiqhState` lives only for one request; `accumulated_evidence` grows by ~15 docs max (5 docs × 3 iterations, deduplicated) | No persistent state growth; no Redis or DB changes needed per-request |
| Latency budget | Expected 15-25s end-to-end for 3-iteration case (FARSIQA: 22.1s for dynamic config) | Cache decompositions for repeated common questions; stream FAIR-RAG `fiqh_status` events so user sees progress immediately |

---

## Sources

- Existing codebase: `agents/core/chat_agent.py`, `agents/state/chat_state.py`, `core/pipeline_langgraph.py`, `.planning/codebase/ARCHITECTURE.md` — HIGH confidence (direct code analysis)
- `documentation/fiqh_related_docs/FAIR_RAG_Fiqh_Implementation_Guide.md` — HIGH confidence (authoritative project documentation derived from FAIR-RAG and FARSIQA papers)
- FARSIQA paper (referenced in above doc): dynamic LLM allocation results (Table 6), iteration count results (Table 5), failure mode taxonomy — HIGH confidence for architectural decisions
- FAIR-RAG paper (referenced in above doc): RRF merge configuration, SEA three-step process, iteration degradation at 4+ loops — HIGH confidence
