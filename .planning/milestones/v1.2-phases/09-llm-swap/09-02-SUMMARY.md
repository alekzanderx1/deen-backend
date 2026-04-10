---
phase: 09-llm-swap
plan: 02
subsystem: api
tags: [anthropic, langchain-anthropic, chat-agent, classifier, pydantic, structured-output]

# Dependency graph
requires:
  - phase: 09-01
    provides: ChatAnthropic factory functions in core/chat_models.py; ANTHROPIC_API_KEY in core/config.py; ModelConfig with max_tokens=4096 default

provides:
  - ChatAgent._create_llm_with_tools() uses ChatAnthropic with ANTHROPIC_API_KEY (no init_chat_model, no openai_api_key)
  - ChatAgent._agent_node() filters spurious empty AIMessages before invoking LLM (D-08)
  - FiqhCategory Pydantic model + classify_fiqh_query() using with_structured_output (preamble-safe)
  - hikmah generation script init_llm() uses ChatAnthropic for all three branches (default, sonnet, opus)
affects: [core/pipeline_langgraph, agents/fiqh/fiqh_graph, modules/fiqh/sea]

# Tech tracking
tech-stack:
  added: []
  patterns: [with_structured_output(PydanticModel) for reliable Claude JSON extraction, D-08 AIMessage filter for tool-calling sequences]

key-files:
  created: []
  modified:
    - agents/core/chat_agent.py
    - modules/fiqh/classifier.py
    - tests/test_fiqh_classifier.py
    - scripts/hikmah_generation/generate_hikmah_tree.py

key-decisions:
  - "D-08 filter uses getattr(msg, 'tool_calls', None) not msg.tool_calls — safe for all message types"
  - "FiqhCategory Literal enforces valid category at schema level — no post-parse VALID_CATEGORIES set check needed"
  - "classifier.py VALID_CATEGORIES set retained for external consumers (e.g., test_never_raises assertion)"
  - "hikmah script removes top-level init_chat_model import entirely — no other usage in file"

patterns-established:
  - "with_structured_output(PydanticModel) pattern: matches sea.py; mock uses mock_model.with_structured_output.return_value = mock_structured"
  - "D-08 filter pattern: filter messages list before llm.invoke() to remove AIMessage(content='', tool_calls=None)"

requirements-completed: [LLM-02, LLM-05, LLM-06, LLM-07]

# Metrics
duration: 3min
completed: 2026-04-10
---

# Phase 09 Plan 02: Agent Graph + Classifier + Hikmah Script Summary

**ChatAnthropic wired end-to-end in ChatAgent and hikmah script; fiqh classifier made preamble-safe via with_structured_output(FiqhCategory); D-08 AIMessage filter added to prevent Claude tool-call sequence crashes**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-10T14:15:56Z
- **Completed:** 2026-04-10T14:19:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Replaced `init_chat_model` + `OPENAI_API_KEY` with `ChatAnthropic` + `ANTHROPIC_API_KEY` in `ChatAgent._create_llm_with_tools()`
- Added D-08 AIMessage filter in `_agent_node()`: removes empty `AIMessage` entries with no `tool_calls` from history before each LLM invocation, preventing Claude API errors in multi-turn tool-calling sequences
- Rewrote `classify_fiqh_query()` to use `model.with_structured_output(FiqhCategory)`, eliminating the fragile `.content.strip().upper()` parser that broke on Claude preamble text
- Updated `generate_hikmah_tree.py` `init_llm()`: both "default" and "else" branches now use `ChatAnthropic(api_key=ANTHROPIC_API_KEY)` — removed `OPENAI_API_KEY` reference and top-level `init_chat_model` import

## Task Commits

Each task was committed atomically:

1. **Task 1: swap chat_agent.py to ChatAnthropic and add D-08 AIMessage filter** - `9c2ba22` (feat)
2. **Task 2: switch classifier.py to with_structured_output; update test mock** - `9a0a227` (feat)
3. **Task 3: update hikmah script init_llm() to use ChatAnthropic** - `be2f9ed` (feat)

## Files Created/Modified

- `agents/core/chat_agent.py` - Replaced init_chat_model + OPENAI_API_KEY with ChatAnthropic + ANTHROPIC_API_KEY; added D-08 AIMessage filter in _agent_node; added AIMessage import
- `modules/fiqh/classifier.py` - Added FiqhCategory Pydantic model with Literal category field; rewrote classify_fiqh_query() to use with_structured_output; removed brittle .strip().upper() parser
- `tests/test_fiqh_classifier.py` - Replaced _mock_llm_response with _mock_classifier_model (matching sea.py mock pattern); removed case-insensitive/whitespace test cases; imports FiqhCategory; all 23 tests pass
- `scripts/hikmah_generation/generate_hikmah_tree.py` - Both init_llm() branches now use ChatAnthropic(api_key=ANTHROPIC_API_KEY, max_tokens=4096); removed init_chat_model import; menu text updated to "(Anthropic)"

## Decisions Made

- `FiqhCategory.category` uses `Literal[...]` type — Pydantic enforces valid category at schema level, so the post-parse `VALID_CATEGORIES` set check inside `classify_fiqh_query()` is no longer needed
- `VALID_CATEGORIES` set kept as module-level constant for external consumers (used in `test_never_raises` and potentially by future callers)
- D-08 filter uses `getattr(msg, "tool_calls", None)` rather than `msg.tool_calls` for broad message type safety
- `hikmah` script lazy-imports `ChatAnthropic` inside `init_llm()` branches (consistent with factory function pattern from Plan 01)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Tests require env vars (`ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `PINECONE_API_KEY`) to be set at collection time due to `core/config.py` raising at import. Tests were run with `ANTHROPIC_API_KEY=sk-ant-fake VOYAGE_API_KEY=fake PINECONE_API_KEY=fake` prefix — all 23 passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full agentic pipeline now uses ChatAnthropic end-to-end: `core/chat_models.py` (Plan 01) + `agents/core/chat_agent.py` (this plan) + `modules/fiqh/classifier.py` (this plan)
- `core/pipeline_langgraph.py` (the streaming pipeline) was not modified in this plan — still uses `get_generator_model()` from `core/chat_models.py` which already returns ChatAnthropic (Plan 01 coverage)
- Legacy modules (`modules/classification`, `modules/enhancement`, `modules/generation`) still import `OPENAI_API_KEY` shim — Phase 11 cleanup scope
- Phase 10 (Embedding Migration): pgvector column resize and Voyage AI backfill

---
*Phase: 09-llm-swap*
*Completed: 2026-04-10*
