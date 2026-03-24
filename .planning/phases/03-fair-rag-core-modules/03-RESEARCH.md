# Phase 3: FAIR-RAG Core Modules — Research

**Researched:** 2026-03-24
**Domain:** LangChain structured output, iterative RAG pattern, evidence assessment, citation generation
**Confidence:** HIGH

## Summary

Phase 3 builds five Python modules in `modules/fiqh/` that implement the four core FAIR-RAG processing stages (filter, SEA, refiner, generator) plus a coordinator that runs the max-3-iteration loop. All modules follow the structural pattern already established by `modules/fiqh/classifier.py` and `modules/fiqh/decomposer.py`: module-level prompt constants, a single public function, `from __future__ import annotations` at the top, and never-raise behavior with safe fallbacks.

The most technically novel module is `sea.py`. It uses LangChain's `with_structured_output()` API to produce reliably typed `SEAResult` Pydantic objects — this API is confirmed available on `langchain-core 0.3.74` and `langchain-openai` with Pydantic v2 (verified in the project's installed venv). The correct call pattern is `model.with_structured_output(SEAResult).invoke(prompt.format_messages(...))`, which chains directly with the existing `ChatPromptTemplate` style.

The coordinator in `fair_rag.py` is pure Python — no LangGraph — and calls `decompose_query` and `retrieve_fiqh_documents` from Phase 2, then sequences the three new modules. The doc shape `{"chunk_id": str, "metadata": dict, "page_content": str}` is the contract across all modules, established by the retriever in Phase 2. All five tests files follow the `unittest.mock.patch` pattern demonstrated in `tests/test_fiqh_classifier.py` and `tests/test_fiqh_retriever.py`.

**Primary recommendation:** Use `model.with_structured_output(SEAResult).invoke(...)` for SEA; use `model.invoke(prompt.format_messages(...)).content` for filter, refiner, and generator; never raise in any public function.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Module Structure**
- D-01: Phase 3 delivers exactly 5 new files in `modules/fiqh/`: `filter.py`, `sea.py`, `refiner.py`, `generator.py`, `fair_rag.py`
- D-02: Phase 4 wraps `fair_rag.py` in a LangGraph sub-graph. Phase 3 contains NO LangGraph code.
- D-03: All modules follow the same structural pattern as `modules/fiqh/classifier.py` and `modules/fiqh/decomposer.py`: module-level prompt constants, a single public function, never raises (returns safe fallback on error).

**LLM Allocation (AGEN-08)**
- D-04: Evidence filter → `chat_models.get_generator_model()` (LARGE_LLM = gpt-4.1) per EVID-02.
- D-05: SEA → `chat_models.get_classifier_model()` (SMALL_LLM = gpt-4o-mini) per AGEN-08.
- D-06: Query refiner → `chat_models.get_generator_model()` (LARGE_LLM = gpt-4.1) per AGEN-08.
- D-07: Answer generator → `chat_models.get_generator_model()` (LARGE_LLM = gpt-4.1) per AGEN-07.
- D-08: The correct large-LLM function is `get_generator_model()`, NOT `get_agent_model()` — that function does not exist.

**Evidence Filter (EVID-01, EVID-02)**
- D-09: Batch filter: one LLM call with ALL retrieved docs, returns list of `chunk_id` strings to KEEP. Inclusive bias — keep any doc where there is doubt.
- D-10: Public interface: `filter_evidence(query: str, docs: list[dict]) -> list[dict]`
- D-11: On any LLM or parse error, return ALL input docs unchanged (fail open).

**SEA — Structured Evidence Assessment (EVID-03, EVID-04, EVID-05)**
- D-12: Use LangChain `.with_structured_output()` with these Pydantic models:
  ```python
  class Finding(BaseModel):
      description: str
      confirmed: bool
      citation: str
      gap_summary: str

  class SEAResult(BaseModel):
      findings: list[Finding]
      verdict: Literal["SUFFICIENT", "INSUFFICIENT"]
      confirmed_facts: list[str]
      gaps: list[str]
  ```
- D-13: Public interface: `assess_evidence(query: str, docs: list[dict]) -> SEAResult`. Default fallback: `SEAResult(findings=[], verdict="INSUFFICIENT", confirmed_facts=[], gaps=[query])`.
- D-14: "Confirmed with logical inferences" means confirmed if evidence explicitly states OR is a direct logical consequence of a stated ruling.

**Query Refiner (EVID-06, EVID-08)**
- D-15: Public interface: `refine_query(original_query: str, sea_result: SEAResult, prior_queries: list[str]) -> list[str]`. Returns 1-4 new sub-queries.
- D-16: Must NOT repeat or rephrase prior queries. Falls back to `[original_query]` on any error.
- D-17: Refinement queries are grounded in `sea_result.confirmed_facts` and target `sea_result.gaps`.

**Answer Generator (AGEN-01 through AGEN-06)**
- D-18: Public interface: `generate_answer(query: str, docs: list[dict], sea_result: SEAResult, is_sufficient: bool) -> str`
- D-19: Citation approach — hybrid: numbered evidence list `[1] text\n[2] text...`, LLM uses `[n]` tokens, system post-processes to build `## Sources` section.
- D-20: Fatwa disclaimer ALWAYS appended: `"Note: This is based on Ayatollah Sistani's published rulings. For a definitive ruling, consult a qualified jurist or Sistani's official office."`
- D-21: Insufficient evidence handling: when `is_sufficient=False`, append `"⚠️ Insufficient Evidence: The retrieved sources do not fully address this question. For a complete ruling, please consult Sistani's official resources at sistani.org or contact his office directly."`

**Coordinator / Iterative Loop (EVID-07)**
- D-22: `fair_rag.py` implements `run_fair_rag(query: str) -> str` orchestrating the full loop.
- D-23: Max 3 iterations enforced by loop counter. Early exit on `SUFFICIENT` verdict.
- D-24: `run_fair_rag(query: str) -> str` is the Phase 4 integration point.

### Claude's Discretion
- Exact prompt templates for filter, SEA, refiner, and generator (content and tone)
- Whether to add a module-level logger to each file (recommended: yes, `logging.getLogger(__name__)`)
- Exact SEA checklist decomposition logic (how many findings to generate from a query)
- Whether to add a `--dry-run` mode to the coordinator

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVID-01 | LLM-based evidence filter removes clearly irrelevant documents while preserving partially relevant ones (inclusive) | `filter_evidence()` in `filter.py` uses single batch LLM call with all docs, inclusive bias, returns all on error |
| EVID-02 | Evidence filtering uses large LLM (gpt-4.1) | `chat_models.get_generator_model()` confirmed in `core/chat_models.py` |
| EVID-03 | SEA deconstructs query into a numbered checklist of required findings | `assess_evidence()` in `sea.py` uses structured output with `Finding` Pydantic model for each checklist item |
| EVID-04 | SEA classifies each finding as confirmed (with logical inferences) or gap | `Finding.confirmed` bool + `Finding.citation` for exact quote; prompt instructs logical inference |
| EVID-05 | SEA produces sufficiency verdict — "Yes" only when ALL required findings confirmed | `SEAResult.verdict: Literal["SUFFICIENT","INSUFFICIENT"]` — SUFFICIENT only when all findings confirmed |
| EVID-06 | When SEA identifies gaps, system generates 1-4 targeted refinement queries using confirmed facts | `refine_query()` in `refiner.py` — receives `sea_result.confirmed_facts` and `sea_result.gaps` |
| EVID-07 | Retrieval-assess-refine loop runs maximum 3 iterations, early exit on sufficiency | `run_fair_rag()` in `fair_rag.py` — iteration counter, early exit on SUFFICIENT |
| EVID-08 | Query refinement uses large LLM and never repeats previous queries | `get_generator_model()` + `prior_queries` list passed to prompt |
| AGEN-01 | Final answer generated exclusively from retrieved evidence | Generator prompt includes only numbered doc list; instructions forbid using outside knowledge |
| AGEN-02 | Every factual claim includes inline citation token [n] | Generator prompt instructs `[n]` inline tokens; post-processing extracts them |
| AGEN-03 | Response includes references list with book/chapter/section/ruling_number | Post-processing in `generate_answer()` builds `## Sources` from chunk metadata |
| AGEN-04 | Every ruling response includes fatwa disclaimer | Disclaimer unconditionally appended in `generate_answer()` |
| AGEN-05 | Insufficient evidence after max iterations → partial answer with warning | `is_sufficient=False` path in generator appends insufficient-evidence warning |
| AGEN-06 | No relevant evidence → clear statement + redirect to official sources | Covered by same `is_sufficient=False` path |
| AGEN-07 | Answer generation uses large LLM (gpt-4.1) | `chat_models.get_generator_model()` confirmed |
| AGEN-08 | Dynamic LLM allocation: small for SEA, large for filter/refinement/generation | SEA → `get_classifier_model()`; others → `get_generator_model()` |
</phase_requirements>

---

## Standard Stack

### Core (verified in installed venv)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain | 0.3.27 | `ChatPromptTemplate`, chain construction | Already used by all fiqh modules |
| langchain-core | 0.3.74 | `with_structured_output()`, base abstractions | Confirmed to have `with_structured_output` on chat model classes |
| langchain-openai | 0.3.25 | OpenAI model binding | Confirmed `ChatOpenAI.with_structured_output` available |
| pydantic | 2.10.6 | `BaseModel`, `Literal`, typed schema definitions | `list[str]` syntax works; `model_json_schema()` correct |
| langchain.chat_models | 0.3.27 | `init_chat_model()` | Existing pattern in `core/chat_models.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (stdlib) | 3.11 | Extract `[n]` citation tokens from generated text | `re.findall(r'\[(\d+)\]', text)` in generator post-processing |
| logging (stdlib) | 3.11 | Module-level logger | `logging.getLogger(__name__)` in each module |
| traceback (stdlib) | 3.11 | Structured error logging | Only where detailed traceback needed (retriever pattern) |

**No new package installations required.** All dependencies are satisfied by the existing `requirements.txt`.

---

## Architecture Patterns

### Recommended Module Structure

```
modules/fiqh/
├── __init__.py          # existing
├── classifier.py        # existing — structural pattern to mirror
├── decomposer.py        # existing — structural pattern to mirror
├── retriever.py         # existing — doc shape source of truth
├── filter.py            # NEW: LLM-based evidence filter
├── sea.py               # NEW: Structured Evidence Assessment
├── refiner.py           # NEW: Query refinement
├── generator.py         # NEW: Answer generation with citations
└── fair_rag.py          # NEW: Coordinator / iterative loop

tests/
├── test_fiqh_filter.py
├── test_fiqh_sea.py
├── test_fiqh_refiner.py
├── test_fiqh_generator.py
└── test_fair_rag.py
```

### Pattern 1: Module Structure (mirrors classifier.py / decomposer.py)

**What:** Module-level prompt constant, single public function, catch-all fallback.
**When to use:** All 5 new modules.

```python
# Source: modules/fiqh/classifier.py (existing)
from __future__ import annotations
import logging
from langchain.prompts import ChatPromptTemplate
from core import chat_models

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """..."""

_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{query}"),
])

def public_function(query: str, ...) -> ReturnType:
    """Never raises — returns safe fallback on any error."""
    try:
        model = chat_models.get_generator_model()   # or get_classifier_model()
        response = model.invoke(_prompt.format_messages(query=query, ...))
        # ... parse response ...
        return result
    except Exception:
        return SAFE_FALLBACK
```

### Pattern 2: Structured Output (SEA module only)

**What:** Use `model.with_structured_output(SEAResult)` to get reliably typed Pydantic output from the LLM.
**When to use:** `sea.py` only — the other modules parse text directly.

```python
# Source: verified in langchain-core 0.3.74 / langchain-openai 0.3.25
def assess_evidence(query: str, docs: list[dict]) -> SEAResult:
    try:
        model = chat_models.get_classifier_model()
        structured_model = model.with_structured_output(SEAResult)
        result = structured_model.invoke(_prompt.format_messages(
            query=query,
            evidence=_format_evidence(docs),
        ))
        return result
    except Exception:
        return SEAResult(findings=[], verdict="INSUFFICIENT",
                         confirmed_facts=[], gaps=[query])
```

**Important:** `with_structured_output` signature is `(schema, method=None, include_raw=False, strict=None, **kwargs)`. No special flags needed for gpt-4o-mini with Pydantic v2 models.

### Pattern 3: Citation Extraction (generator.py)

**What:** LLM cites inline with `[n]` tokens; system extracts and builds references section.
**When to use:** `generate_answer()` in `generator.py`.

```python
# Source: verified with re module
import re

def _build_references_section(text: str, docs: list[dict]) -> str:
    """Extract [n] tokens from text, build ## Sources section from doc metadata."""
    citation_nums = sorted(set(int(n) for n in re.findall(r'\[(\d+)\]', text)))
    if not citation_nums:
        return ""
    lines = ["", "## Sources"]
    for n in citation_nums:
        idx = n - 1  # [1] maps to docs[0]
        if 0 <= idx < len(docs):
            md = docs[idx].get("metadata", {})
            book = md.get("source_book", "Islamic Laws")
            chapter = md.get("chapter", "")
            section = md.get("section", "")
            ruling = md.get("ruling_number", "")
            lines.append(f"[{n}] {book}, {chapter}, {section}, Ruling {ruling}")
    return "\n".join(lines)
```

### Pattern 4: Evidence Formatting (shared utility, inline in each module)

**What:** Convert `list[dict]` doc shape to numbered text block for LLM prompt.
**When to use:** filter.py, sea.py, refiner.py (for confirmed facts context), generator.py.

```python
def _format_evidence(docs: list[dict]) -> str:
    """Format docs as numbered evidence list for LLM prompt."""
    lines = []
    for i, doc in enumerate(docs, 1):
        lines.append(f"[{i}] {doc.get('page_content', '')}")
    return "\n".join(lines)
```

### Pattern 5: Test Structure (mirrors test_fiqh_classifier.py)

**What:** `unittest.mock.patch` on `chat_models.get_*_model`, `MagicMock` for responses.
**When to use:** All 5 test files.

```python
# Source: tests/test_fiqh_classifier.py (existing)
def _mock_llm_response(text: str) -> MagicMock:
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = text
    mock_model.invoke.return_value = mock_response
    return mock_model

# For SEA (with_structured_output):
def _mock_sea_model(return_value: SEAResult) -> MagicMock:
    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_model.with_structured_output.return_value = mock_structured
    mock_structured.invoke.return_value = return_value
    return mock_model
```

**Patch path convention (verified by existing tests):**
- `"modules.fiqh.filter.chat_models.get_generator_model"`
- `"modules.fiqh.sea.chat_models.get_classifier_model"`
- `"modules.fiqh.refiner.chat_models.get_generator_model"`
- `"modules.fiqh.generator.chat_models.get_generator_model"`

### Pattern 6: Coordinator Loop (fair_rag.py)

**What:** Pure Python loop calling Phase 2 functions + new modules; max 3 iterations.
**When to use:** `fair_rag.py` only.

```python
def run_fair_rag(query: str) -> str:
    """Orchestrates the FAIR-RAG iterative retrieve-filter-assess-refine loop."""
    try:
        all_docs: list[dict] = []
        prior_queries: list[str] = [query]
        sea_result: SEAResult | None = None
        current_query = query

        for iteration in range(1, 4):  # max 3 iterations (1, 2, 3)
            new_docs = retrieve_fiqh_documents(current_query)
            # Merge new docs into accumulator, deduplicate by chunk_id
            seen_ids = {d["chunk_id"] for d in all_docs}
            for doc in new_docs:
                if doc["chunk_id"] not in seen_ids:
                    all_docs.append(doc)
                    seen_ids.add(doc["chunk_id"])

            filtered_docs = filter_evidence(query, all_docs)
            sea_result = assess_evidence(query, filtered_docs)

            if sea_result.verdict == "SUFFICIENT" or iteration >= 3:
                break

            refinement_queries = refine_query(query, sea_result, prior_queries)
            prior_queries.extend(refinement_queries)
            # Join refinements for next retrieval pass
            current_query = " ".join(refinement_queries)

        is_sufficient = sea_result is not None and sea_result.verdict == "SUFFICIENT"
        return generate_answer(
            query=query,
            docs=filtered_docs if filtered_docs else all_docs,
            sea_result=sea_result or SEAResult(findings=[], verdict="INSUFFICIENT",
                                               confirmed_facts=[], gaps=[query]),
            is_sufficient=is_sufficient,
        )
    except Exception as e:
        logger.error("[FAIR_RAG] run_fair_rag error: %s", e)
        return ("I was unable to retrieve relevant rulings for this question. "
                "Please consult Sistani's official resources at sistani.org.")
```

### Anti-Patterns to Avoid

- **Raise in public functions:** All public functions must catch all exceptions and return safe fallbacks — never raise.
- **Calling `get_agent_model()`:** That function does not exist in `core/chat_models.py`. Use `get_generator_model()` for LARGE_LLM.
- **LangGraph imports in Phase 3:** No LangGraph code. Phase 4 wraps `run_fair_rag`.
- **List construction for evidence `[n]` mapping:** When building the references section, map `[n]` to `docs[n-1]` where `docs` is the ordered list passed to the generator prompt — not the full `all_docs` accumulator. Misalignment causes wrong citations.
- **Using `chain = prompt | model` pipe operator for structured output:** Use the explicit `.invoke()` pattern to match existing module style and simplify mocking.
- **Mutable default arguments in function signatures:** Use `None` as default for `prior_queries`, initialize to `[]` inside function.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output | Custom JSON parser with regex | `model.with_structured_output(SEAResult)` | Handles LLM inconsistencies, retries, schema validation |
| LLM model initialization | Direct `ChatOpenAI(...)` calls | `chat_models.get_generator_model()` / `get_classifier_model()` | Centralizes API key, model ID, config; consistent with project |
| Evidence formatting | Custom serialization | `_format_evidence(docs)` helper inline in each module | Simple numbered list; docs already have `page_content` |
| Citation extraction | Markdown parser | `re.findall(r'\[(\d+)\]', text)` | `[n]` tokens are trivial to extract with regex |

**Key insight:** The LLM model wrappers and prompt template API handle all the complexity around structured output, retries, and serialization. The modules are thin orchestration layers — the value is in the prompts and the loop logic, not the infrastructure.

---

## Common Pitfalls

### Pitfall 1: with_structured_output and gpt-4o-mini Tool Calling
**What goes wrong:** `gpt-4o-mini` with `with_structured_output` uses function/tool calling under the hood. If the LLM declines to use the tool (e.g., content policy, context length), it raises an exception rather than returning a partial result.
**Why it happens:** `with_structured_output` requires the LLM to invoke a structured schema function call — it cannot fall back to plain text.
**How to avoid:** The catch-all `except Exception` in `assess_evidence()` handles this. The fallback `SEAResult(findings=[], verdict="INSUFFICIENT", confirmed_facts=[], gaps=[query])` ensures the loop continues. Do NOT let exceptions propagate.
**Warning signs:** Tests pass but integration fails with `OutputParserException` or tool call errors — add logging in the except block.

### Pitfall 2: Evidence List Index Misalignment in Citations
**What goes wrong:** The generator is given a numbered list `[1]...[2]...` of docs. If filtered_docs is used for the prompt but `all_docs` is used for the references section post-processing, citation `[1]` maps to the wrong document.
**Why it happens:** The `docs` parameter to `generate_answer` is the list used for both numbering in the prompt AND building the references section.
**How to avoid:** `generate_answer` builds its own numbered list from the `docs` parameter and post-processes the same `docs` list. Never pass a different list to the references builder than was used to build the numbered prompt.

### Pitfall 3: Filter Returns Empty List
**What goes wrong:** If the filter LLM is overly aggressive and returns an empty chunk_id list, `filter_evidence` returns `[]`. The SEA then sees no evidence and returns INSUFFICIENT, causing unnecessary iterations.
**Why it happens:** Prompt not clearly communicating inclusive bias.
**How to avoid:** The filter prompt must explicitly instruct "when in doubt, keep". Additionally, if the parsed chunk_id list is empty, `filter_evidence` should fall back to returning all input docs (same as error behavior per D-11).

### Pitfall 4: prior_queries Grows Unbounded Across Iterations
**What goes wrong:** If `refine_query` returns 4 new queries each iteration, `prior_queries` grows to 13 items by iteration 3. This makes the prompt very large.
**Why it happens:** No cap on prior_queries list size passed to refiner.
**How to avoid:** With max 3 iterations and 1-4 queries per iteration, worst case is 1 + 4 + 4 = 9 queries. This is manageable. The refiner prompt should include them as a compact list. If prompt length becomes a concern in practice, truncate to the last 8.

### Pitfall 5: Test Isolation — with_structured_output Mock Chaining
**What goes wrong:** Patching `chat_models.get_classifier_model` returns a mock, but `mock.with_structured_output(SEAResult)` returns a new `MagicMock` that has a different `.invoke()` method than expected. Tests pass but the mock return value is a `MagicMock`, not a `SEAResult`.
**Why it happens:** `MagicMock.with_structured_output()` returns a new auto-spec mock, not the configured return value.
**How to avoid:** Use the `_mock_sea_model` helper pattern:
```python
mock_model = MagicMock()
mock_structured = MagicMock()
mock_model.with_structured_output.return_value = mock_structured
mock_structured.invoke.return_value = SEAResult(...)
```
This must be set up explicitly — do NOT rely on MagicMock's auto-return.

### Pitfall 6: Coordinator Accumulating Docs Across Iterations
**What goes wrong:** If `run_fair_rag` passes only the latest iteration's docs to SEA (not all accumulated docs), SEA cannot see evidence from earlier iterations.
**Why it happens:** Natural to just pass the latest retrieval result.
**How to avoid:** Accumulate all unique docs across iterations (deduplicate by `chunk_id`). Pass the full accumulated + filtered set to SEA each iteration.

---

## Code Examples

Verified patterns from existing codebase:

### Filter Evidence — LLM Response Parsing
```python
# Source: modules/fiqh/decomposer.py pattern (existing)
# Filter returns JSON list of chunk_ids to keep
import json

response = model.invoke(_prompt.format_messages(query=query, evidence=formatted_evidence))
content = response.content.strip()
if content.startswith("```"):
    parts = content.split("```")
    content = parts[1] if len(parts) > 1 else content
    if content.startswith("json"):
        content = content[4:]
    content = content.strip()
chunk_ids_to_keep = json.loads(content)
```

### SEA Structured Output with Fallback
```python
# Source: verified with langchain-core 0.3.74 in project venv
def assess_evidence(query: str, docs: list[dict]) -> SEAResult:
    try:
        model = chat_models.get_classifier_model()
        structured_model = model.with_structured_output(SEAResult)
        result = structured_model.invoke(
            _prompt.format_messages(query=query, evidence=_format_evidence(docs))
        )
        return result
    except Exception:
        return SEAResult(findings=[], verdict="INSUFFICIENT",
                         confirmed_facts=[], gaps=[query])
```

### Refiner — Prior Query List in Prompt
```python
# Refiner prompt must include prior_queries as a formatted block
formatted_prior = "\n".join(f"- {q}" for q in prior_queries)
response = model.invoke(_prompt.format_messages(
    original_query=original_query,
    confirmed_facts="\n".join(f"- {f}" for f in sea_result.confirmed_facts),
    gaps="\n".join(f"- {g}" for g in sea_result.gaps),
    prior_queries=formatted_prior,
))
```

### Citation Regex Extraction
```python
# Source: verified in Python 3.11 re module
import re

citation_nums = sorted(set(int(n) for n in re.findall(r'\[(\d+)\]', generated_text)))
# citation_nums: [1, 2, 3] — 1-based indices into docs list
```

### Test Patch Path for New Modules
```python
# Source: tests/test_fiqh_classifier.py pattern (existing)
with patch("modules.fiqh.filter.chat_models.get_generator_model",
           return_value=_mock_llm_response('["chunk_1", "chunk_2"]')):
    result = filter_evidence("test query", test_docs)

with patch("modules.fiqh.sea.chat_models.get_classifier_model",
           return_value=_mock_sea_model(sea_result)):
    result = assess_evidence("test query", test_docs)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-pass RAG (retrieve once, generate) | Iterative RAG with SEA (FAIR-RAG pattern) | 2023-2024 in literature | Dramatically reduces hallucinations on multi-step fiqh questions |
| String-based JSON parsing | `with_structured_output()` with Pydantic | LangChain 0.2+ | Eliminates custom JSON parsers, retries handled by library |
| Hard-coded model names in modules | `chat_models.get_generator_model()` / `get_classifier_model()` | Project convention (Phase 2) | Model swaps require changing one file |

**Deprecated/outdated:**
- `LLMChain` (LangChain 0.1 pattern): Do not use. Current pattern is `model.invoke(prompt.format_messages(...))`.
- `SequentialChain`: Do not use. Use explicit Python function calls as in classifier/decomposer.
- `PydanticOutputParser`: Superseded by `with_structured_output()` for structured output.

---

## Open Questions

1. **SEA findings count heuristic**
   - What we know: SEA must decompose the query into a numbered checklist of "required findings"
   - What's unclear: Should the prompt request a fixed number of findings (e.g., 3-5) or let the LLM determine? More findings = more granular gap detection but more tokens.
   - Recommendation: Let the LLM determine (1-5 findings), but instruct it to be granular enough to detect specific gaps. This is left to Claude's discretion per the CONTEXT.md.

2. **Coordinator: accumulated docs vs. fresh retrieval each iteration**
   - What we know: The loop refines queries based on gaps. Refinement queries target different sub-topics.
   - What's unclear: Should `filter_evidence` receive only the latest iteration's docs, or all accumulated docs?
   - Recommendation: Accumulate all unique docs across iterations (deduplicate by `chunk_id`) before filtering each iteration. This gives SEA the most context.

3. **Generator prompt strictness for AGEN-01**
   - What we know: AGEN-01 requires no parametric LLM knowledge — only retrieved evidence.
   - What's unclear: How strictly to enforce this — the LLM can always "leak" parametric knowledge.
   - Recommendation: Strong prompt instruction: "Answer ONLY from the numbered evidence below. Do not use any knowledge not present in the evidence. If the evidence does not support a claim, state this explicitly."

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies identified — Phase 3 is code-only, all required packages already in venv, no new tools needed)

---

## Validation Architecture

> `workflow.nyquist_validation` is `false` in `.planning/config.json` — this section is skipped per configuration.

---

## Sources

### Primary (HIGH confidence)
- `/Users/shawn.n/Desktop/Deen/deen-backend/modules/fiqh/classifier.py` — structural pattern (module-level prompt, single public function, never-raise)
- `/Users/shawn.n/Desktop/Deen/deen-backend/modules/fiqh/decomposer.py` — fallback pattern, JSON parsing with markdown fence handling
- `/Users/shawn.n/Desktop/Deen/deen-backend/modules/fiqh/retriever.py` — doc shape `{"chunk_id", "metadata", "page_content"}`, logger pattern
- `/Users/shawn.n/Desktop/Deen/deen-backend/core/chat_models.py` — confirmed function names: `get_generator_model()`, `get_classifier_model()`, `get_enhancer_model()`, `get_translator_model()` (no `get_agent_model`)
- `/Users/shawn.n/Desktop/Deen/deen-backend/tests/test_fiqh_classifier.py` — mock helper pattern, patch path convention
- `/Users/shawn.n/Desktop/Deen/deen-backend/tests/test_fiqh_retriever.py` — multi-mock patch pattern

### Secondary (MEDIUM confidence)
- `langchain-core 0.3.74` in-venv verification: `with_structured_output` confirmed on `ChatOpenAI` (signature: `schema, method, include_raw, strict, kwargs`)
- Pydantic 2.10.6 in-venv verification: `list[str]` new-style syntax works, `Literal` works, `model_json_schema()` generates valid JSON Schema
- Python 3.11 re module: `re.findall(r'\[(\d+)\]', text)` confirmed for citation extraction

### Tertiary (LOW confidence)
- FARSIQA paper reference (CONTEXT.md): SEA checklist approach mirrors paper's evidence assessment methodology — not directly verified against paper, accepted from project context

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in installed venv
- Architecture: HIGH — all patterns verified against existing codebase files
- Pitfalls: MEDIUM — derived from code analysis + LangChain API behavior; integration edge cases always possible
- Test patterns: HIGH — verified against running test suite (31 existing tests pass)

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (LangChain 0.3.x is stable; Pydantic v2 is stable)
