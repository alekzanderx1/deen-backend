# Phase 9: LLM Swap - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace all OpenAI LLM wiring with `ChatAnthropic` across the full pipeline: `core/chat_models.py` factory functions, `agents/core/chat_agent.py`, `agents/config/agent_config.py`, `modules/fiqh/classifier.py`, and `scripts/hikmah_generation/generate_hikmah_tree.py`. Fix Claude-specific compatibility issues: preamble-safe category parsing, empty AIMessage filtering, and max_tokens defaults. No embedding changes (Phase 10), no dead code removal (Phase 11) — LLM wiring only.

</domain>

<decisions>
## Implementation Decisions

### Classifier Preamble Parsing (LLM-05)

- **D-01:** Use `with_structured_output` for `classify_fiqh_query()` — same pattern as `sea.py`. Define a `FiqhCategory` Pydantic model with `category: Literal["VALID_OBVIOUS", "VALID_SMALL", "VALID_LARGE", "VALID_REASONER", "OUT_OF_SCOPE_FIQH", "UNETHICAL"]`. Call `model.with_structured_output(FiqhCategory)` and return `result.category`. Current free-text `.strip().upper()` parser is removed. Error fallback remains `OUT_OF_SCOPE_FIQH`.

### max_tokens for Factory Functions (LLM-01 + LLM-04)

- **D-02:** All `chat_models.py` factory functions set explicit `max_tokens` on the `ChatAnthropic(...)` instantiation. Per-function values:
  - `get_generator_model()` → `max_tokens=4096` (long fiqh answers, general responses)
  - `get_classifier_model()` → `max_tokens=2048` (SEA structured output with multi-finding Pydantic, classifier response)
  - `get_enhancer_model()` → `max_tokens=512` (short query rewrites)
  - `get_translator_model()` → `max_tokens=1024` (translated text, usually sentence-level)
- **D-03:** `ModelConfig` in `agent_config.py` still gets `max_tokens=4096` default per LLM-04 — covers the `_create_llm_with_tools` path in `chat_agent.py`.

### ChatAnthropic Instantiation (LLM-01, LLM-02)

- **D-04:** All factory functions use `ChatAnthropic(model=..., api_key=ANTHROPIC_API_KEY, max_tokens=...)` directly — not `init_chat_model(..., openai_api_key=)`. Import from `langchain_anthropic`. `OPENAI_API_KEY` import removed from `chat_models.py` and `chat_agent.py`.

### ModelConfig Updates (LLM-03, LLM-04)

- **D-05:** `ModelConfig.agent_model` fallback updated from `"gpt-4o"` to `"claude-sonnet-4-6"` per LLM-03.
- **D-06:** `ModelConfig.temperature` validator updated from `le=2.0` to `le=1.0` (Claude max is 1.0). `ModelConfig.max_tokens` default updated to `4096` from `None`.

### Classifier Model Assignment

- **D-07:** `get_classifier_model()` continues to return `LARGE_LLM` (claude-sonnet-4-6) for now. The SMALL_LLM correction is deferred — safer to leave unchanged during migration. This can be addressed in Phase 11 or a follow-up.

### Empty AIMessage Filtering (LLM-06)

- **D-08:** `_agent_node` in `chat_agent.py` filters `AIMessage` entries from history where `content == ""` AND `tool_calls` is empty/absent before passing messages to the LLM. Messages with `content == ""` but active `tool_calls` are preserved (standard Claude tool-use format).

### Hikmah Script (LLM-07)

- **D-09:** `scripts/hikmah_generation/generate_hikmah_tree.py` switches from `init_chat_model(..., openai_api_key=OPENAI_API_KEY)` to `ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY)` (or reads `ANTHROPIC_API_KEY` from env directly via `dotenv`). The script already loads `.env` at the top — `ANTHROPIC_API_KEY` will be available.

### Claude's Discretion

- Exact import style for `ChatAnthropic` (top-level import vs. lazy import inside function) — follow existing pattern in the file.
- Whether `get_translator_model()` keeps the `.bind(temperature=0)` chain call — preserve existing behavior, just swap the underlying model.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Files Being Modified
- `core/chat_models.py` — All 4 factory functions; primary target for LLM-01
- `agents/core/chat_agent.py` — `_create_llm_with_tools()` (LLM-02), `_agent_node()` (LLM-06)
- `agents/config/agent_config.py` — `ModelConfig` fallback + validators (LLM-03, LLM-04)
- `modules/fiqh/classifier.py` — `classify_fiqh_query()` preamble parsing (LLM-05)
- `scripts/hikmah_generation/generate_hikmah_tree.py` — LLM instantiation (LLM-07)

### Reference Implementations
- `modules/fiqh/sea.py` — `with_structured_output(SEAResult)` pattern; D-01 follows this exactly
- `.planning/phases/08-config-dependencies/08-CONTEXT.md` — Prior phase decisions (API key guard pattern)

### Phase Requirements
- `.planning/REQUIREMENTS.md` §LLM Migration (LLM-01..07) — Acceptance criteria for all 7 requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `modules/fiqh/sea.py` `assess_evidence()` — exact pattern for `with_structured_output` + Pydantic model; D-01 mirrors this
- `core/config.py` — `ANTHROPIC_API_KEY` already imported and validated; ready to use in `chat_models.py`

### Established Patterns
- `ChatAnthropic` available from `langchain_anthropic` (added in Phase 8, CONF-05)
- `init_chat_model` with `openai_api_key=` is the current pattern across all 4 factory functions — all 4 need replacement
- `get_translator_model()` uses `.bind(temperature=0)` — keep this behavior, just swap the base model
- `_create_llm_with_tools()` in `chat_agent.py` passes `max_tokens=self.config.model.max_tokens` — will pick up the new 4096 default from ModelConfig automatically once D-06 is applied

### Integration Points
- `modules/fiqh/classifier.py` imports `chat_models.get_classifier_model()` — after D-01, the function signature is unchanged; only the internal LLM call and parsing change
- `modules/fiqh/sea.py` imports `chat_models.get_classifier_model()` — same; `with_structured_output` is called on the returned model, which `ChatAnthropic` supports
- `agents/core/chat_agent.py` imports `OPENAI_API_KEY` from `core.config` — this import will be removed (replaced by `ANTHROPIC_API_KEY`)

</code_context>

<specifics>
## Specific Ideas

- D-01: `FiqhCategory` Pydantic model with `category: Literal[...]` field — same shape as `SEAResult` but minimal. One field only.
- D-08: Filter condition: `isinstance(msg, AIMessage) and msg.content == "" and not getattr(msg, "tool_calls", None)`

</specifics>

<deferred>
## Deferred Ideas

- `get_classifier_model()` → `SMALL_LLM` correction — design intent, deferred to Phase 11 or follow-up (D-07)

</deferred>

---

*Phase: 09-llm-swap*
*Context gathered: 2026-04-10*
