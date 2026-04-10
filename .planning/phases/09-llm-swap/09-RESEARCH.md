# Phase 9: LLM Swap - Research

**Researched:** 2026-04-10
**Domain:** LangChain ChatAnthropic migration — all 5 target files
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 (LLM-05):** Use `with_structured_output` for `classify_fiqh_query()`. Define `FiqhCategory` Pydantic model with `category: Literal["VALID_OBVIOUS", "VALID_SMALL", "VALID_LARGE", "VALID_REASONER", "OUT_OF_SCOPE_FIQH", "UNETHICAL"]`. Call `model.with_structured_output(FiqhCategory)` and return `result.category`. Remove current free-text `.strip().upper()` parser. Error fallback remains `OUT_OF_SCOPE_FIQH`.

**D-02 (LLM-01 + LLM-04):** All `chat_models.py` factory functions set explicit `max_tokens` on `ChatAnthropic(...)`:
- `get_generator_model()` → `max_tokens=4096`
- `get_classifier_model()` → `max_tokens=2048`
- `get_enhancer_model()` → `max_tokens=512`
- `get_translator_model()` → `max_tokens=1024`

**D-03 (LLM-04):** `ModelConfig` in `agent_config.py` gets `max_tokens=4096` default.

**D-04 (LLM-01, LLM-02):** All factory functions use `ChatAnthropic(model=..., api_key=ANTHROPIC_API_KEY, max_tokens=...)` directly — not `init_chat_model`. Import from `langchain_anthropic`. `OPENAI_API_KEY` import removed from `chat_models.py` and `chat_agent.py`.

**D-05 (LLM-03):** `ModelConfig.agent_model` fallback updated from `"gpt-4o"` to `"claude-sonnet-4-6"`.

**D-06 (LLM-04):** `ModelConfig.temperature` validator: `le=2.0` → `le=1.0`. `ModelConfig.max_tokens` default: `None` → `4096`.

**D-07:** `get_classifier_model()` continues to return `LARGE_LLM` (not SMALL_LLM). SMALL_LLM correction deferred to Phase 11.

**D-08 (LLM-06):** `_agent_node` in `chat_agent.py` filters `AIMessage` entries from history where `content == "" AND tool_calls is empty/absent`. Condition: `isinstance(msg, AIMessage) and msg.content == "" and not getattr(msg, "tool_calls", None)`.

**D-09 (LLM-07):** `scripts/hikmah_generation/generate_hikmah_tree.py` — `init_llm()` "default" branch switches from `init_chat_model(..., openai_api_key=OPENAI_API_KEY)` to `ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY)`. The script already loads `.env`.

### Claude's Discretion
- Exact import style for `ChatAnthropic` (top-level import vs. lazy import inside function) — follow existing pattern in the file.
- Whether `get_translator_model()` keeps the `.bind(temperature=0)` chain call — preserve existing behavior, just swap the base model.

### Deferred Ideas (OUT OF SCOPE)
- `get_classifier_model()` → `SMALL_LLM` correction — deferred to Phase 11 or follow-up (D-07).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLM-01 | `core/chat_models.py` factory functions use `ChatAnthropic(api_key=ANTHROPIC_API_KEY)` instead of `init_chat_model` | Verified: ChatAnthropic constructor accepts `model`, `api_key`, `max_tokens`, `temperature`. `OPENAI_API_KEY` no longer exists in `core.config` — import must change or code breaks at collection time. |
| LLM-02 | `agents/core/chat_agent.py` uses `ChatAnthropic` with `ANTHROPIC_API_KEY`; `openai_api_key=` removed | `_create_llm_with_tools()` at line 56-62 is the target. `from core.config import OPENAI_API_KEY` at line 32 must change to `ANTHROPIC_API_KEY`. `bind_tools` works on `ChatAnthropic`. |
| LLM-03 | `agents/config/agent_config.py` fallback model updated from `gpt-4o` to `claude-sonnet-4-6` | Line 70: `default=LARGE_LLM or "gpt-4o"`. `LARGE_LLM` is already `"claude-sonnet-4-6"` from config. The string fallback `"gpt-4o"` must change to `"claude-sonnet-4-6"`. |
| LLM-04 | `ModelConfig` gets `max_tokens=4096` default and temperature validator `le=1.0` | Claude API max temperature is 1.0 (verified). `max_tokens` is required by Claude API — no default omission. Current `max_tokens=None` and `le=2.0` both need updating. |
| LLM-05 | `classify_fiqh_query()` response parsing robust to Claude preamble text | Current `.strip().upper()` regex fails if Claude emits "Here is the category: VALID_SMALL". Fix: `with_structured_output(FiqhCategory)` — same pattern as `sea.py`. Verified: `ChatAnthropic.with_structured_output` returns `RunnableSequence`. |
| LLM-06 | `_agent_node` filters empty `AIMessage` content before passing history to LLM | Claude emits `AIMessage(content="", tool_calls=[...])` during tool-calling sequences. Empty content with no tool_calls is spurious and causes Claude API errors. Filter condition verified to work correctly. |
| LLM-07 | `scripts/hikmah_generation/generate_hikmah_tree.py` updated to use `ANTHROPIC_API_KEY` | `init_llm()` at line 259-274 has a "default" branch that imports `OPENAI_API_KEY` from `core.config` — this import fails at runtime since Phase 8 removed that export. Must switch to `ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY)`. |
</phase_requirements>

---

## Summary

Phase 9 replaces `init_chat_model(..., openai_api_key=)` with `ChatAnthropic(model=..., api_key=ANTHROPIC_API_KEY, max_tokens=...)` across five files. The scope is narrowly bounded: only the five files listed in CONTEXT.md `<canonical_refs>`. Legacy pipeline modules (`modules/classification/classifier.py`, `modules/enhancement/enhancer.py`, `modules/generation/generator.py`, `modules/generation/stream_generator.py`) also import `OPENAI_API_KEY` but are deferred to Phase 11 cleanup.

Two Claude-specific compatibility issues are resolved in this phase: (1) fiqh classifier preamble text — the current `.strip().upper()` parser breaks when Claude prefixes its response with prose; fixed by switching to `with_structured_output(FiqhCategory)`. (2) Empty `AIMessage` content — Claude emits `content=""` in tool-calling sequences; spurious empty messages without tool_calls must be filtered in `_agent_node`.

**Critical discovery:** `core/chat_models.py` currently imports `OPENAI_API_KEY` from `core.config`, but Phase 8 already removed that export. Every test that imports `chat_models` (or any module that imports it) fails at collection time with `ImportError: cannot import name 'OPENAI_API_KEY' from 'core.config'`. Fixing `chat_models.py` in Plan 1 is the highest-priority unblock — it makes the test suite collectable again.

**Primary recommendation:** Execute all LLM-01 through LLM-07 changes in a single plan. The changes are low-risk substitutions; there is no reason to split into multiple plans. The order is: `chat_models.py` first (unblocks all tests), then `agent_config.py` (D-05, D-06), then `chat_agent.py` (LLM-02, LLM-06), then `classifier.py` (LLM-05), then `generate_hikmah_tree.py` (LLM-07).

---

## Standard Stack

### Core Libraries (already installed — Phase 8 complete)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `langchain-anthropic` | 0.3.22 | `ChatAnthropic` class — LangChain wrapper for Anthropic API | Installed and importable; `ChatAnthropic` confirmed importable from `langchain_anthropic` |
| `anthropic` | 0.87.0 (pinned) / 0.92.0 (installed) | Underlying Anthropic SDK | requirements.txt pins 0.87.0 per Phase 8 decision; installed version is 0.92.0 |

Note: `anthropic==0.92.0` is installed in the venv, but `requirements.txt` pins `anthropic==0.87.0`. This discrepancy exists from Phase 8. Phase 9 does not change `requirements.txt` — only code changes.

### ChatAnthropic Constructor API (verified against installed 0.3.22)

```python
from langchain_anthropic import ChatAnthropic

# Correct instantiation pattern (D-04)
model = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key=ANTHROPIC_API_KEY,   # <-- parameter name is api_key, not anthropic_api_key
    max_tokens=4096,
    temperature=0.7,              # optional; valid range: 0.0 to 1.0
)
```

Key verified facts:
- Parameter name is `api_key` (not `anthropic_api_key`) when constructing `ChatAnthropic` directly
- `max_tokens` is a constructor parameter — required for Claude (no default)
- `temperature` valid range is `0.0` to `1.0` (Claude max is 1.0, not 2.0 like OpenAI)
- `bind_tools(tools)` works on `ChatAnthropic` — returns `RunnableBinding`
- `with_structured_output(Schema)` works on `ChatAnthropic` — returns `RunnableSequence`
- `.bind(temperature=0)` chain call works — returns `RunnableBinding` (for `get_translator_model()`)
- `.astream()` and `.stream()` both available

Note: `init_chat_model(model=..., anthropic_api_key=...)` also works (the hikmah script's non-default branch uses this). D-04 mandates using `ChatAnthropic(...)` directly for all factory functions, not `init_chat_model`.

---

## Architecture Patterns

### Pattern 1: ChatAnthropic Factory Function (D-04)

Replace every `init_chat_model(model=X, openai_api_key=Y)` with direct `ChatAnthropic(...)`:

```python
# BEFORE (current)
from core.config import OPENAI_API_KEY
from langchain.chat_models import init_chat_model

def get_generator_model():
    from core.config import LARGE_LLM
    chat_model = init_chat_model(model=LARGE_LLM, openai_api_key=OPENAI_API_KEY)
    return chat_model

# AFTER (Phase 9)
from langchain_anthropic import ChatAnthropic
from core.config import ANTHROPIC_API_KEY

def get_generator_model():
    from core.config import LARGE_LLM
    return ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY, max_tokens=4096)
```

### Pattern 2: with_structured_output for Classifier (D-01)

Mirror the existing `sea.py` pattern exactly:

```python
# sea.py pattern (already works, reference implementation)
model = chat_models.get_classifier_model()
structured_model = model.with_structured_output(SEAResult)
result = structured_model.invoke(_prompt.format_messages(...))
return result  # SEAResult instance

# NEW classifier.py pattern (D-01)
from pydantic import BaseModel
from typing import Literal

class FiqhCategory(BaseModel):
    category: Literal["VALID_OBVIOUS", "VALID_SMALL", "VALID_LARGE",
                      "VALID_REASONER", "OUT_OF_SCOPE_FIQH", "UNETHICAL"]

def classify_fiqh_query(query: str) -> str:
    try:
        model = chat_models.get_classifier_model()
        structured_model = model.with_structured_output(FiqhCategory)
        result = structured_model.invoke(_prompt.format_messages(query=query))
        return result.category
    except Exception:
        return "OUT_OF_SCOPE_FIQH"
```

The `_prompt` ChatPromptTemplate stays unchanged. The system prompt (`SYSTEM_PROMPT`) stays unchanged. Only the invocation and parsing change.

### Pattern 3: Empty AIMessage Filtering (D-08)

Insert filter before `self.llm.invoke(messages)` in `_agent_node`:

```python
# D-08: filter empty AIMessages with no tool_calls (Claude tool-calling artifact)
messages = [
    msg for msg in messages
    if not (
        isinstance(msg, AIMessage)
        and msg.content == ""
        and not getattr(msg, "tool_calls", None)
    )
]
response = self.llm.invoke(messages)
```

The filter must preserve `AIMessage(content="", tool_calls=[...])` — these are valid Claude tool-call requests.

### Pattern 4: ModelConfig Validator Update (D-05, D-06)

```python
# BEFORE
agent_model: str = Field(default=LARGE_LLM or "gpt-4o", ...)
temperature: float = Field(default=0.7, ge=0.0, le=2.0, ...)
max_tokens: Optional[int] = Field(default=None, ...)

# AFTER
agent_model: str = Field(default=LARGE_LLM or "claude-sonnet-4-6", ...)
temperature: float = Field(default=0.7, ge=0.0, le=1.0, ...)
max_tokens: int = Field(default=4096, ge=1, ...)
```

Note: `max_tokens` type changes from `Optional[int]` to `int` (removes Optional since it has a non-None default). The `Optional` import may need to be kept for other fields — check the file's other `Optional` uses before removing it.

### Pattern 5: Hikmah Script init_llm (D-09)

The script's `init_llm()` has two branches. The "default" branch uses `OPENAI_API_KEY` which no longer exists in `core.config`. After D-09:

```python
def init_llm(model_choice: str):
    global _llm
    from core.config import LARGE_LLM, ANTHROPIC_API_KEY
    from langchain_anthropic import ChatAnthropic

    if model_choice == "default":
        if not LARGE_LLM:
            raise ValueError("LARGE_LLM is not set in .env")
        print(f"[{timestamp()}] Using model: {LARGE_LLM} (Anthropic)")
        _llm = ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY, max_tokens=4096)
    else:
        # existing sonnet/opus branch — replace init_chat_model with ChatAnthropic
        model_id = "claude-sonnet-4-6" if model_choice == "sonnet" else "claude-opus-4-6"
        print(f"[{timestamp()}] Using model: {model_id} (Anthropic)")
        _llm = ChatAnthropic(model=model_id, api_key=ANTHROPIC_API_KEY, max_tokens=4096)
```

The interactive menu text at lines 834-836 should be updated to remove "(OpenAI)" label from option 1.

### Anti-Patterns to Avoid

- **Using `anthropic_api_key=` kwarg with `ChatAnthropic` directly:** Only `api_key=` is the correct parameter when constructing `ChatAnthropic(...)` directly. The `anthropic_api_key=` kwarg is for `init_chat_model()`'s auto-detection path.
- **Omitting `max_tokens`:** Claude API raises `400 Bad Request` if `max_tokens` is not set. OpenAI has a default; Claude does not.
- **Setting `temperature > 1.0`:** Claude's max temperature is 1.0. Values above 1.0 cause a validation error from the API.
- **Touching legacy pipeline modules:** `modules/classification/classifier.py`, `modules/enhancement/enhancer.py`, `modules/generation/generator.py`, `modules/generation/stream_generator.py` — all import `OPENAI_API_KEY` and will fail at import time. These are Phase 11 scope. The agentic pipeline does NOT call these modules for normal chat.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured category extraction | Custom regex to strip Claude preamble | `model.with_structured_output(FiqhCategory)` | Claude's tool-calling forces structured output reliably; regex breaks on any preamble variation |
| Streaming event translation | Custom event format conversion | LangGraph `compiled_graph.astream()` unchanged | LangGraph emits the same node-level events regardless of underlying LLM provider |

---

## Common Pitfalls

### Pitfall 1: `api_key` vs `anthropic_api_key` Parameter Name
**What goes wrong:** Using `ChatAnthropic(anthropic_api_key=ANTHROPIC_API_KEY)` raises a Pydantic validation warning or uses the wrong field.
**Why it happens:** `init_chat_model` accepts `anthropic_api_key=` as a provider-detection kwarg. `ChatAnthropic(...)` constructor uses `api_key=`.
**How to avoid:** Always use `api_key=ANTHROPIC_API_KEY` when constructing `ChatAnthropic` directly (verified against installed 0.3.22).

### Pitfall 2: Missing `max_tokens` Causes Claude 400 Error
**What goes wrong:** Claude API returns HTTP 400 on every LLM call when `max_tokens` is not set.
**Why it happens:** Claude API requires `max_tokens` — there is no server-side default.
**How to avoid:** Every `ChatAnthropic(...)` instantiation must include `max_tokens=N` (D-02, D-03).

### Pitfall 3: Classifier Test Suite Breaks After D-01
**What goes wrong:** `tests/test_fiqh_classifier.py` mocks `chat_models.get_classifier_model` to return a model whose `.invoke()` returns a `MagicMock` with `.content = "VALID_OBVIOUS"`. After D-01, `classify_fiqh_query()` calls `model.with_structured_output(FiqhCategory)` then `.invoke()` — it no longer reads `.content` directly.
**Why it happens:** The test mock was written for the free-text parser. After D-01, the function calls `.with_structured_output()` on the returned mock.
**How to avoid:** Update test helpers to use the `_mock_sea_model` pattern from `test_fiqh_sea.py` — mock both `with_structured_output` and the resulting chain's `invoke`. The `_mock_sea_model` helper in `test_fiqh_sea.py` is the exact template. Create a `_mock_classifier_model(category_str)` helper that returns a mock whose `.with_structured_output(...).invoke(...)` returns a `FiqhCategory(category=category_str)`.

### Pitfall 4: `chat_models.py` OPENAI_API_KEY Import Breaks Test Collection Right Now
**What goes wrong:** `from core.config import OPENAI_API_KEY` at line 1 of `chat_models.py` raises `ImportError: cannot import name 'OPENAI_API_KEY' from 'core.config'` — Phase 8 removed that export. Any test that imports `chat_models` (directly or transitively) fails at collection time with this error.
**Why it happens:** Phase 8 replaced `OPENAI_API_KEY` with `ANTHROPIC_API_KEY` in `core/config.py` but did not update `chat_models.py`.
**How to avoid:** The first change in this phase must be `chat_models.py` line 1: replace `from core.config import OPENAI_API_KEY` with `from core.config import ANTHROPIC_API_KEY`. This unblocks all test collection.

### Pitfall 5: Empty AIMessage Filter Applied Before History Is Set Up
**What goes wrong:** Filtering happens on `messages = list(state["messages"])` before the iteration-1 `SystemMessage` and `HumanMessage` are appended. If the filter runs after appending, it might strip valid messages.
**Why it happens:** `_agent_node` builds messages in-place, appending to the list.
**How to avoid:** Apply the filter on the initial `messages = list(state["messages"])` line — before iteration-1 content is appended. History messages come from Redis and may contain Claude's spurious empty `AIMessage` entries from prior turns.

### Pitfall 6: `ModelConfig.max_tokens` Type Change May Break Optional Import
**What goes wrong:** Changing `max_tokens: Optional[int] = Field(default=None, ...)` to `max_tokens: int = Field(default=4096, ...)` removes the `Optional` usage. If `Optional` is only used for `max_tokens`, the `Optional` import can be removed. But if another field still uses `Optional`, removing it causes `NameError`.
**Why it happens:** `from typing import Optional` import at the top of the file.
**How to avoid:** Before removing `Optional`, check all other `Optional[...]` annotations in `agent_config.py`. Confirmed: `max_tokens` is the only `Optional` field. The import can be removed when type changes to `int`.

### Pitfall 7: Hikmah Script Menu Text Still Says "OpenAI"
**What goes wrong:** Option 1 in the interactive menu at line 834 says "Default -- LARGE_LLM from .env (OpenAI)". After D-09, the default uses Anthropic.
**Why it happens:** The menu text wasn't in scope of CONTEXT.md.
**How to avoid:** Update line 834 to say "(Anthropic)" instead of "(OpenAI)".

---

## Code Examples

### chat_models.py — Full Replacement (verified pattern)

```python
# Source: verified against langchain-anthropic 0.3.22 installed
from langchain_anthropic import ChatAnthropic
from core.config import ANTHROPIC_API_KEY


def get_generator_model():
    from core.config import LARGE_LLM
    return ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY, max_tokens=4096)


def get_enhancer_model():
    from core.config import SMALL_LLM
    return ChatAnthropic(model=SMALL_LLM, api_key=ANTHROPIC_API_KEY, max_tokens=512)


def get_classifier_model():
    from core.config import LARGE_LLM
    return ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY, max_tokens=2048)


def get_translator_model():
    from core.config import LARGE_LLM
    base = ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY, max_tokens=1024)
    return base.bind(temperature=0)
```

### chat_agent.py — _create_llm_with_tools replacement (LLM-02)

```python
# Source: verified against langchain-anthropic 0.3.22 installed
from langchain_anthropic import ChatAnthropic
from core.config import ANTHROPIC_API_KEY  # replaces OPENAI_API_KEY

def _create_llm_with_tools(self):
    llm = ChatAnthropic(
        model=self.config.model.agent_model,
        api_key=ANTHROPIC_API_KEY,
        temperature=self.config.model.temperature,
        max_tokens=self.config.model.max_tokens,
    )
    return llm.bind_tools(self.tools)
```

### classifier.py — with_structured_output pattern (D-01)

```python
# Source: mirrors sea.py assess_evidence() pattern exactly
from pydantic import BaseModel
from typing import Literal

class FiqhCategory(BaseModel):
    category: Literal[
        "VALID_OBVIOUS", "VALID_SMALL", "VALID_LARGE",
        "VALID_REASONER", "OUT_OF_SCOPE_FIQH", "UNETHICAL"
    ]

def classify_fiqh_query(query: str) -> str:
    try:
        model = chat_models.get_classifier_model()
        structured_model = model.with_structured_output(FiqhCategory)
        result = structured_model.invoke(_prompt.format_messages(query=query))
        return result.category
    except Exception:
        return "OUT_OF_SCOPE_FIQH"
```

### Test mock update for classifier (Pitfall 3)

```python
# Replace _mock_llm_response helper in test_fiqh_classifier.py
from modules.fiqh.classifier import FiqhCategory  # import new Pydantic model

def _mock_classifier_model(category_str: str) -> MagicMock:
    """Helper: mock that simulates with_structured_output returning FiqhCategory."""
    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_model.with_structured_output.return_value = mock_structured
    mock_structured.invoke.return_value = FiqhCategory(category=category_str)
    return mock_model
```

---

## Files to Modify (Exact List)

| File | Lines Changed | Requirement |
|------|--------------|-------------|
| `core/chat_models.py` | Entire file (72 lines → ~30 lines) | LLM-01 |
| `agents/core/chat_agent.py` | Line 11 (import), line 32 (import), lines 56-62 (`_create_llm_with_tools`), ~line 147 (AIMessage filter) | LLM-02, LLM-06 |
| `agents/config/agent_config.py` | Line 70 (fallback), lines 74-85 (temperature + max_tokens validators) | LLM-03, LLM-04 |
| `modules/fiqh/classifier.py` | Add `FiqhCategory` model, rewrite `classify_fiqh_query()` body | LLM-05 |
| `scripts/hikmah_generation/generate_hikmah_tree.py` | Lines 259-274 (`init_llm()`), line 834 (menu text) | LLM-07 |
| `tests/test_fiqh_classifier.py` | `_mock_llm_response` helper → `_mock_classifier_model`, all parametrize test cases | Test alignment with D-01 |

**Not in scope for Phase 9:**
- `modules/classification/classifier.py` — imports `OPENAI_API_KEY` and `from openai import OpenAI` but is legacy pipeline; Phase 11
- `modules/enhancement/enhancer.py` — imports `OPENAI_API_KEY`; Phase 11
- `modules/generation/generator.py` — imports `OPENAI_API_KEY`; Phase 11
- `modules/generation/stream_generator.py` — imports `from openai import OpenAI`; Phase 11

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `init_chat_model(..., openai_api_key=)` | `ChatAnthropic(model=..., api_key=..., max_tokens=...)` | Phase 9 | Direct constructor, no auto-detection overhead |
| `response.content.strip().upper()` | `model.with_structured_output(FiqhCategory).invoke(...)` | Phase 9 | Reliable structured extraction, preamble-safe |
| `max_tokens=None` (optional) | `max_tokens=4096` (required) | Phase 9 | Claude API requirement |
| Temperature range `le=2.0` | Temperature range `le=1.0` | Phase 9 | Claude API max is 1.0 |
| `ModelConfig.agent_model` fallback `"gpt-4o"` | Fallback `"claude-sonnet-4-6"` | Phase 9 | Consistent with Phase 8 defaults |

**Currently broken (pre-Phase 9):**
- `chat_models.py` line 1: `from core.config import OPENAI_API_KEY` — this is an `ImportError` since Phase 8 removed that export. The module is currently uncollectable. This means `test_fiqh_classifier.py`, `test_fiqh_sea.py`, and any test importing `chat_models` transitively all fail at collection.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `langchain-anthropic` | All LLM-01..07 changes | Yes | 0.3.22 (installed) | — |
| `anthropic` | `langchain-anthropic` dependency | Yes | 0.92.0 (installed; requirements.txt pins 0.87.0) | — |
| `ChatAnthropic` import | `chat_models.py`, `chat_agent.py`, hikmah script | Yes (verified `from langchain_anthropic import ChatAnthropic` works) | — | — |
| `ANTHROPIC_API_KEY` in `core.config` | LLM-01, LLM-02, LLM-07 | Yes (Phase 8 added it) | — | — |

**Missing dependencies with no fallback:** None.

---

## Open Questions

1. **Legacy pipeline modules and OPENAI_API_KEY import**
   - What we know: `modules/classification/classifier.py`, `modules/enhancement/enhancer.py`, `modules/generation/generator.py`, `modules/generation/stream_generator.py` all import `OPENAI_API_KEY` from `core.config` — which no longer exists. These will fail at import time if any code path touches them.
   - What's unclear: Are these modules imported at application startup (not just when routes are called)? If `main.py` or any module-level import chain triggers them, the app itself won't start.
   - Recommendation: Check if any of these are imported at module level in `main.py` or `api/` routers. If yes, the plan must address them in Phase 9 even though they're formally Phase 11 scope. The safest fix is a try/except import guard or simply stubbing out the import.

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `core/chat_models.py`, `agents/core/chat_agent.py`, `agents/config/agent_config.py`, `modules/fiqh/classifier.py`, `modules/fiqh/sea.py`, `scripts/hikmah_generation/generate_hikmah_tree.py`, `core/config.py` — exact line-level verification
- Runtime verification: `from langchain_anthropic import ChatAnthropic` — executed in venv, confirmed importable
- Runtime verification: `ChatAnthropic(model=..., api_key=..., max_tokens=...)` — constructor verified with fake key
- Runtime verification: `ChatAnthropic.with_structured_output(FiqhCategory)` — returns `RunnableSequence` (confirmed)
- Runtime verification: `ChatAnthropic.bind_tools([...])` — returns `RunnableBinding` (confirmed)
- Runtime verification: AIMessage filter condition (D-08) — tested with empty, tool-call, and normal messages
- Runtime verification: Pydantic ModelConfig validator `le=1.0` boundary — tested 1.0 accepted, 1.5 rejected

### Secondary (MEDIUM confidence)
- `pip show langchain-anthropic` → Version: 0.3.22
- `pip show anthropic` → Version: 0.92.0 (venv); requirements.txt pins 0.87.0

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all imports and constructors verified by executing Python in the project venv
- Architecture: HIGH — all 5 target files read and mapped to exact change locations
- Pitfalls: HIGH — pitfalls 1-4 discovered by running existing tests and inspecting actual import errors

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable library APIs)
