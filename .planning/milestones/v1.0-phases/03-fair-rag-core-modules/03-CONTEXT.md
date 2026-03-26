# Phase 3: FAIR-RAG Core Modules - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the four FAIR-RAG processing modules — evidence filter, SEA (Structured Evidence Assessment), query refiner, and answer generator — plus a coordinator function that implements the max-3-iteration loop. All code lives in `modules/fiqh/`. Modules are unit-tested in isolation against synthetic evidence sets. No LangGraph integration yet — that is Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Module Structure
- **D-01:** Phase 3 delivers exactly 5 new files in `modules/fiqh/`:
  - `modules/fiqh/filter.py` — LLM-based evidence filter (batch, inclusive)
  - `modules/fiqh/sea.py` — Structured Evidence Assessment (SEA) with Pydantic output
  - `modules/fiqh/refiner.py` — query refinement generating 1-4 new sub-queries
  - `modules/fiqh/generator.py` — answer generation with inline [n] citations and disclaimer
  - `modules/fiqh/fair_rag.py` — coordinator implementing the max-3-iteration retrieve→filter→assess→refine loop as pure Python (EVID-07)
- **D-02:** Phase 4 wraps `fair_rag.py` in a LangGraph sub-graph. Phase 3 contains NO LangGraph code.
- **D-03:** All modules follow the same structural pattern as `modules/fiqh/classifier.py` and `modules/fiqh/decomposer.py`: module-level prompt constants, a single public function, never raises (returns safe fallback on error).

### LLM Allocation (AGEN-08)
- **D-04:** Evidence filter → `chat_models.get_generator_model()` (LARGE_LLM = gpt-4.1) per EVID-02.
- **D-05:** SEA → `chat_models.get_classifier_model()` (SMALL_LLM = gpt-4o-mini) per AGEN-08 ("small tasks include SEA").
- **D-06:** Query refiner → `chat_models.get_generator_model()` (LARGE_LLM = gpt-4.1) per AGEN-08 ("heavy tasks include refinement").
- **D-07:** Answer generator → `chat_models.get_generator_model()` (LARGE_LLM = gpt-4.1) per AGEN-07.
- **D-08:** The correct large-LLM function is `get_generator_model()`, NOT `get_agent_model()` — that function does not exist in `core/chat_models.py`. Do not call `get_agent_model()`.

### Evidence Filter (EVID-01, EVID-02)
- **D-09:** Batch filter: one LLM call with ALL retrieved docs, returns list of `chunk_id` strings to KEEP. Inclusive bias — keep any doc where there is doubt about irrelevance ("when in doubt, keep").
- **D-10:** Public interface: `filter_evidence(query: str, docs: list[dict]) -> list[dict]`. Input/output both use the `{"chunk_id": str, "metadata": dict, "page_content": str}` shape from Phase 2 D-17.
- **D-11:** On any LLM or parse error, return ALL input docs unchanged (fail open, not fail closed — per inclusive design).

### SEA — Structured Evidence Assessment (EVID-03, EVID-04, EVID-05)
- **D-12:** Use LangChain `.with_structured_output()` with Pydantic models for reliable JSON:
  ```python
  class Finding(BaseModel):
      description: str           # what the query requires
      confirmed: bool            # True if found in evidence
      citation: str              # exact quote or "" if not confirmed
      gap_summary: str           # what's missing, or "" if confirmed

  class SEAResult(BaseModel):
      findings: list[Finding]
      verdict: Literal["SUFFICIENT", "INSUFFICIENT"]
      confirmed_facts: list[str]  # bullet list of confirmed facts (for refiner)
      gaps: list[str]             # bullet list of gaps (for refiner query)
  ```
- **D-13:** Public interface: `assess_evidence(query: str, docs: list[dict]) -> SEAResult`. Returns a default `SEAResult(findings=[], verdict="INSUFFICIENT", confirmed_facts=[], gaps=[query])` on any error.
- **D-14:** "Confirmed with logical inferences" (EVID-04) means: confirmed if evidence explicitly states OR if it is a direct logical consequence of a stated ruling. The SEA prompt should instruct this. Claude's discretion on the exact wording.

### Query Refiner (EVID-06, EVID-08)
- **D-15:** Public interface: `refine_query(original_query: str, sea_result: SEAResult, prior_queries: list[str]) -> list[str]`. Returns 1-4 new sub-queries.
- **D-16:** Refiner must NOT repeat or rephrase prior queries (pass `prior_queries` list in the prompt). Falls back to `[original_query]` on any error.
- **D-17:** Refinement queries are grounded in confirmed facts from `sea_result.confirmed_facts` and target `sea_result.gaps`. The prompt explicitly includes both.

### Answer Generator (AGEN-01 through AGEN-06)
- **D-18:** Public interface: `generate_answer(query: str, docs: list[dict], sea_result: SEAResult, is_sufficient: bool) -> str`. Returns a string response.
- **D-19:** Citation approach — hybrid:
  1. Generator prompt includes numbered evidence list: `[1] <text>\n[2] <text>...`
  2. LLM instructed to cite inline with `[n]` tokens
  3. System post-processes response to extract `[n]` references and builds references section from chunk metadata
  4. References section appended to response: `## Sources\n[1] Islamic Laws, Chapter X, Section Y, Ruling 712`
- **D-20:** Fatwa disclaimer is ALWAYS appended on any ruling response: `"Note: This is based on Ayatollah Sistani's published rulings. For a definitive ruling, consult a qualified jurist or Sistani's official office."` (per AGEN-04). The generator function always appends it.
- **D-21:** Insufficient evidence handling (AGEN-05, AGEN-06): when `is_sufficient=False`, the generator produces a partial answer with `"⚠️ Insufficient Evidence: The retrieved sources do not fully address this question. For a complete ruling, please consult Sistani's official resources at sistani.org or contact his office directly."` — never hallucinate.

### Coordinator / Iterative Loop (EVID-07)
- **D-22:** `fair_rag.py` implements `run_fair_rag(query: str) -> str` which orchestrates:
  1. Decompose query (call `decompose_query` from Phase 2)
  2. Retrieve docs (call `retrieve_fiqh_documents` from Phase 2)
  3. Filter evidence (call `filter_evidence`)
  4. Assess evidence (call `assess_evidence` → `SEAResult`)
  5. If `SUFFICIENT` or `iteration >= 3`: generate answer (call `generate_answer`)
  6. Else: refine query (call `refine_query`), retrieve again, loop to step 3
- **D-23:** Max 3 iterations enforced by loop counter. Early exit on `SUFFICIENT` verdict.
- **D-24:** The public interface `run_fair_rag(query: str) -> str` is what Phase 4 will call from LangGraph.

### Claude's Discretion
- Exact prompt templates for filter, SEA, refiner, and generator (content and tone)
- Whether to add a module-level logger to each file (recommended: yes, `logging.getLogger(__name__)`)
- Exact SEA checklist decomposition logic (how many findings to generate from a query)
- Whether to add a `--dry-run` mode to the coordinator

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Evidence Assessment (EVID-01 to EVID-08) — all acceptance criteria for filter, SEA, refiner, and loop
- `.planning/REQUIREMENTS.md` §Answer Generation (AGEN-01 to AGEN-08) — citation, disclaimer, insufficient evidence requirements

### Phase 2 Artifacts (read before implementing — these are the inputs to Phase 3)
- `modules/fiqh/decomposer.py` — `decompose_query(query) -> list[str]` called by coordinator
- `modules/fiqh/retriever.py` — `retrieve_fiqh_documents(query) -> list[dict]` called by coordinator; doc shape is `{"chunk_id": str, "metadata": dict, "page_content": str}`
- `modules/fiqh/classifier.py` — structural pattern to mirror in new modules

### Core utilities
- `core/chat_models.py` — `get_generator_model()` (LARGE_LLM) and `get_classifier_model()` (SMALL_LLM); do NOT call `get_agent_model()` (does not exist)
- `modules/generation/generator.py` — existing non-fiqh generator; read for style reference only, do NOT reuse

### Test patterns
- `tests/test_fiqh_classifier.py` — mocked LLM test pattern to follow
- `tests/test_fiqh_retriever.py` — mocked Pinecone test pattern to follow

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/chat_models.get_generator_model()`: Returns gpt-4.1; use for filter, refiner, generator
- `core/chat_models.get_classifier_model()`: Returns gpt-4o-mini; use for SEA
- `modules/fiqh/decomposer.py`: `decompose_query(query)` already handles query breakdown
- `modules/fiqh/retriever.py`: `retrieve_fiqh_documents(query)` already handles hybrid retrieval

### Established Patterns
- Module-level `_prompt = ChatPromptTemplate.from_messages(...)` — defined at module level, invoked at function call time (matches classifier.py and decomposer.py)
- Never raise in public functions — return safe fallback on any exception
- Use `from __future__ import annotations` at top of each module
- Test files use `sys.path.insert(0, str(Path(__file__).parent.parent))` and `unittest.mock.patch`

### Integration Points
- `modules/fiqh/fair_rag.py` is the Phase 4 integration point — Phase 4 imports and calls `run_fair_rag(query)`
- `agents/state/chat_state.py` will gain a `fair_rag_result` field in Phase 4 (not Phase 3)

</code_context>

<specifics>
## Specific Ideas

- SEA checklist approach mirrors the FARSIQA paper's evidence assessment methodology — sufficiency verdict "Yes" only when ALL findings confirmed
- The 97% negative rejection accuracy target (CLAS-05) is partially met by the SEA layer: when no evidence supports a finding, the answer explicitly states this rather than generating a ruling
- Citations are `[n]` not `(source)` or footnotes — consistent with academic-style inline citation for traceability

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-fair-rag-core-modules*
*Context gathered: 2026-03-24*
