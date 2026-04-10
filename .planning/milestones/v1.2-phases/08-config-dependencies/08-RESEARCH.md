# Phase 8: Config + Dependencies - Research

**Researched:** 2026-04-09
**Domain:** Python dependency management, environment variable configuration, FastAPI startup guards
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Both `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` use the **inline module-level guard** pattern — same as the existing `OPENAI_API_KEY` guard. A single combined `if not ANTHROPIC_API_KEY or not VOYAGE_API_KEY or not PINECONE_API_KEY` raise at module level (replacing the current `OPENAI_API_KEY` check). Tests that import `core.config` must set dummy values for `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` in their environment.

- **D-02:** `tiktoken` is **kept** in `requirements.txt`. The ingestion script `scripts/ingest_fiqh.py` uses it directly (`import tiktoken; ENCODING = tiktoken.get_encoding("cl100k_base")`). CONF-06 scope is narrowed to removing `langchain-openai` and `openai` only — tiktoken is NOT removed.

- **D-03:** `LARGE_LLM` default → `claude-sonnet-4-6`; `SMALL_LLM` default → `claude-haiku-4-5-20251001`. These are added as default values in `os.getenv()` calls. No additional validation guard beyond the existing no-default pattern.

- **D-04:** `EMBEDDING_MODEL` default → `voyage-4`; `EMBEDDING_DIMENSIONS` default → `1024`.

- **D-05:** Pin exact versions as specified in requirements: `langchain-anthropic==0.3.22`, `anthropic==0.87.0`, `voyageai==0.3.7`. Trust pinned versions — no version re-resolution.

### Claude's Discretion

- Exact position of the inline guard in `core/config.py` (before or after Pinecone guard) — planner decides based on logical grouping.
- Whether to add a brief comment explaining the deferred Supabase pattern vs inline pattern (for future maintainers).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONF-01 | `ANTHROPIC_API_KEY` replaces `OPENAI_API_KEY` in `core/config.py` startup validation guard | D-01: inline guard pattern. Existing guard on line 44 is the exact template. |
| CONF-02 | `VOYAGE_API_KEY` added to `core/config.py` with startup validation guard | D-01: added to same combined inline guard as ANTHROPIC_API_KEY. |
| CONF-03 | `LARGE_LLM` default updated to `claude-sonnet-4-6`; `SMALL_LLM` to `claude-haiku-4-5-20251001` | D-03: `os.getenv("LARGE_LLM", "claude-sonnet-4-6")` pattern. No existing default — currently `os.getenv("LARGE_LLM")` with no fallback. |
| CONF-04 | `EMBEDDING_MODEL` default updated to `voyage-4`; `EMBEDDING_DIMENSIONS` to `1024` | D-04: two `os.getenv()` calls at bottom of config.py (lines 88–89) already have defaults — just replace values. |
| CONF-05 | `langchain-anthropic==0.3.22`, `anthropic==0.87.0`, `voyageai==0.3.7` added to `requirements.txt` | Already installed in venv at these exact versions. Add three lines to requirements.txt alphabetically. |
| CONF-06 | `langchain-openai`, `openai` removed from `requirements.txt` (tiktoken kept) | `openai==1.91.0` on line 59, `langchain-openai==0.3.25` on line 42. Remove both lines. tiktoken on line 108 stays. |
| CONF-07 | `.env.example` updated — `ANTHROPIC_API_KEY` + `VOYAGE_API_KEY` added, `OPENAI_API_KEY` removed | `.env.example` currently has `OPENAI_API_KEY=your-openai-api-key-here` on line 9 under `# === OpenAI ===` section header. Replace section. |

</phase_requirements>

---

## Summary

Phase 8 is a pure config and packaging change — no pipeline logic, no LLM calls, no embedding calls. The work is constrained to four files: `core/config.py`, `requirements.txt`, `.env.example`, and the test suite awareness for the key guard change.

The existing codebase already has `langchain-anthropic==0.3.22`, `anthropic==0.92.0`, and `voyageai==0.3.7` installed in the venv (verified via `pip index versions`). The `requirements.txt` does not yet list them. D-05 pins `anthropic==0.87.0` — this is intentionally behind the currently installed `0.92.0`. The planner must record this fact and pin exactly `0.87.0` as decided, not the installed version.

The guard replacement is the only structurally sensitive change: every module that imports `core.config` at module level will now require `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` in the environment (or a dummy value) instead of `OPENAI_API_KEY`. There are 17 files that transitively depend on `core/config.py` being importable. None of the existing unit tests set `OPENAI_API_KEY` explicitly — they rely on the `.env` file being present. The same approach carries forward for the new keys.

**Primary recommendation:** Make all four file changes in a single atomic wave. The guard swap is the highest-risk change; the rest are mechanical additions/removals.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.87.0 (pinned, D-05) | Anthropic Python SDK; used by langchain-anthropic | Official Anthropic SDK |
| langchain-anthropic | 0.3.22 (pinned, D-05) | `ChatAnthropic` class for LangChain/LangGraph integration | LangChain's official Anthropic binding |
| voyageai | 0.3.7 (pinned, D-05) | Voyage AI Python SDK; `voyageai.Client` for embedding calls | Official Voyage AI SDK |

### Packages Being Removed
| Library | Current Version | Reason for Removal |
|---------|----------------|---------------------|
| langchain-openai | 0.3.25 | Replaced by langchain-anthropic |
| openai | 1.91.0 | Replaced by anthropic |

### Packages Kept (commonly confused)
| Library | Version | Reason Kept |
|---------|---------|-------------|
| tiktoken | 0.9.0 | `scripts/ingest_fiqh.py` imports it directly; D-02 is explicit |

**Version notes (verified 2026-04-09):**

- `langchain-anthropic` latest is `1.4.0`; pinned to `0.3.22` per D-05. Version `0.3.22` confirmed available in PyPI and already installed in venv.
- `anthropic` latest is `0.92.0`; pinned to `0.87.0` per D-05. Version `0.92.0` is currently installed in venv — the `requirements.txt` pin will be `0.87.0` as decided. This is intentional.
- `voyageai` latest is `0.3.7`; pinned to `0.3.7` per D-05. Already installed in venv.

---

## Architecture Patterns

### Pattern 1: Inline Module-Level Guard (existing pattern)

**What:** Env vars read at import time via `os.getenv()`. A combined `if not VAR_A or not VAR_B` block at module level raises `ValueError` immediately, before any app startup logic runs.

**When to use:** For API keys that are required for the app to function at all. The guard fires when any module that imports `core.config` is loaded.

**Existing code (lines 44–45 of `core/config.py`):**
```python
# Current guard (to be replaced):
if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("Missing API keys! Ensure they are set in the .env file.")
```

**New guard (D-01):**
```python
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

if not ANTHROPIC_API_KEY or not VOYAGE_API_KEY or not PINECONE_API_KEY:
    raise ValueError("Missing API keys! Ensure ANTHROPIC_API_KEY, VOYAGE_API_KEY, and PINECONE_API_KEY are set in the .env file.")
```

The `OPENAI_API_KEY` variable assignment on line 10 and all references to it in `core/config.py` are removed. The variable is still referenced in `core/chat_models.py`, `agents/core/chat_agent.py`, `modules/classification/classifier.py`, `modules/enhancement/enhancer.py`, `modules/generation/stream_generator.py`, `modules/generation/generator.py`, and `services/embedding_service.py` — but those are out of scope for Phase 8 (Phase 9 and 11 handle them). At the end of Phase 8, those files will attempt `from core.config import OPENAI_API_KEY` and will get an `ImportError` (attribute no longer exists). This is acceptable because the app is not yet runnable end-to-end until Phase 9 completes. The planner should note this explicitly.

### Pattern 2: Deferred Startup Guard (existing, reference only)

**What:** `validate_supabase_config()` function called from `main.py` lifespan. Used for vars that test suites should be able to omit. NOT used for the new keys per D-01.

```python
# In core/config.py
def validate_supabase_config() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Missing Supabase config! ...")

# In main.py lifespan
validate_supabase_config()
```

**Relevance:** D-01 explicitly rejects this pattern for `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY`. Use the inline pattern instead.

### Pattern 3: os.getenv with Default (existing pattern for D-03, D-04)

```python
# Current (line 88-89 of core/config.py):
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))

# After Phase 8:
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-4")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
```

```python
# Current (lines 29-30):
LARGE_LLM = os.getenv("LARGE_LLM")
SMALL_LLM = os.getenv("SMALL_LLM")

# After Phase 8:
LARGE_LLM = os.getenv("LARGE_LLM", "claude-sonnet-4-6")
SMALL_LLM = os.getenv("SMALL_LLM", "claude-haiku-4-5-20251001")
```

### Recommended Change Sequence in `core/config.py`

1. Remove `OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")` from line 10.
2. Add `ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")` and `VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")` near the top API Keys section (around lines 10–12).
3. Replace the combined guard (lines 44–45) with the new three-key guard.
4. Update `LARGE_LLM` and `SMALL_LLM` defaults (lines 29–30).
5. Update `EMBEDDING_MODEL` and `EMBEDDING_DIMENSIONS` defaults (lines 88–89).

### Anti-Patterns to Avoid

- **Keeping `OPENAI_API_KEY` in the guard:** D-01 says replace, not add. The old key must be removed from the guard.
- **Using deferred pattern for new keys:** D-01 is explicit — inline guard only.
- **Removing tiktoken from requirements.txt:** D-02 is explicit — tiktoken stays. `scripts/ingest_fiqh.py` uses it directly.
- **Pinning `anthropic==0.92.0` (current installed):** D-05 specifies `0.87.0`. Use exactly what was decided.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var validation | Custom validation classes | `os.getenv()` + inline guard | Project already uses this pattern; consistent with existing codebase |
| Package version resolution | Dynamic version detection | Pinned `requirements.txt` entries | D-05 specifies exact versions; deterministic builds |
| Test env setup | Complex monkeypatching | `.env` file with dummy values | Existing tests use this approach |

---

## Common Pitfalls

### Pitfall 1: `OPENAI_API_KEY` Attribute Error After Guard Removal

**What goes wrong:** After removing `OPENAI_API_KEY` from `core/config.py`, importing modules like `core/chat_models.py`, `agents/core/chat_agent.py`, `modules/classification/classifier.py`, etc. will raise `ImportError: cannot import name 'OPENAI_API_KEY' from 'core.config'`.

**Why it happens:** 7 files import `OPENAI_API_KEY` from `core.config` at module level. Phase 8 only changes config — those files are not updated until Phase 9 and 11.

**How to avoid:** This is expected behavior for Phase 8. Document it clearly: "The app is not yet bootable after Phase 8 alone — `core/chat_models.py` and other files still reference the removed `OPENAI_API_KEY` export. Full boot is restored in Phase 9."

**Warning signs:** `ImportError` on `OPENAI_API_KEY` is expected; `ImportError` on `ANTHROPIC_API_KEY` or `VOYAGE_API_KEY` would mean the new exports were not added correctly.

### Pitfall 2: requirements.txt Duplicate Entries

**What goes wrong:** Adding `langchain-anthropic`, `anthropic`, `voyageai` without removing `langchain-openai` and `openai` creates a file with conflicting packages.

**Why it happens:** Editor/tool inserts additions at top or bottom without removing old entries.

**How to avoid:** Perform the add and remove in the same edit. Verify the resulting file has exactly one entry per package name. `langchain-openai` is on line 42; `openai` is on line 59.

### Pitfall 3: Pinned Version Mismatch

**What goes wrong:** Using the currently-installed `anthropic==0.92.0` instead of the pinned `0.87.0`.

**Why it happens:** `pip index versions` or `pip show anthropic` shows 0.92.0 installed, which could lead a developer to pin that version instead.

**How to avoid:** D-05 is explicit: pin `0.87.0`. The installed version in venv is ahead of the pinned version — this is intentional per the context decisions.

### Pitfall 4: `.env.example` Comment Block Inconsistency

**What goes wrong:** Replacing `OPENAI_API_KEY` entry but leaving the `# === OpenAI ===` section header or leaving stale model name defaults (`gpt-4.1-2025-04-14`).

**Why it happens:** Partial edit of `.env.example`.

**How to avoid:** Replace the entire `# === OpenAI ===` section block (lines 8–11 of `.env.example`) with a `# === Anthropic ===` section containing `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, and updated `LARGE_LLM`/`SMALL_LLM` values. Also update `EMBEDDING_MODEL` and `EMBEDDING_DIMENSIONS` in the Memory/Personalization section.

### Pitfall 5: Test Suite Breaking on Guard Change

**What goes wrong:** Tests that import modules which transitively load `core/config.py` will now fail if `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` are absent from the test environment.

**Why it happens:** The inline guard fires on any `import core.config` (directly or transitively). The old guard checked `OPENAI_API_KEY`; tests that set `OPENAI_API_KEY` (or rely on `.env`) but not the new keys will fail.

**How to avoid:** The test suite already relies on `.env` being present (per `test_agentic_streaming_sse.py` line 10 docstring). Add `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` to the `.env` file used during test runs. Unit tests in `tests/` that mock LLM calls (e.g., `test_fiqh_classifier.py`) mock at the module level after import — they will still require the keys to be present for the import to succeed. A dummy value (e.g., `sk-ant-test`) satisfies the guard.

---

## Code Examples

### Verified: Final state of `core/config.py` API Keys section

```python
# Source: core/config.py (current state + Phase 8 changes)
import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")

# Retrieve API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# ... (rest of vars unchanged) ...
LARGE_LLM = os.getenv("LARGE_LLM", "claude-sonnet-4-6")
SMALL_LLM = os.getenv("SMALL_LLM", "claude-haiku-4-5-20251001")
# ...

if not ANTHROPIC_API_KEY or not VOYAGE_API_KEY or not PINECONE_API_KEY:
    raise ValueError("Missing API keys! Ensure ANTHROPIC_API_KEY, VOYAGE_API_KEY, and PINECONE_API_KEY are set in the .env file.")

# ... (validate_supabase_config and DB config unchanged) ...

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-4")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
```

### Verified: requirements.txt additions

```
# Add these three lines (alphabetical placement):
anthropic==0.87.0        # after "annotated-types"
langchain-anthropic==0.3.22   # after "langchain==" entry block
voyageai==0.3.7          # after "vcrpy" entry

# Remove these two lines:
langchain-openai==0.3.25
openai==1.91.0
```

### Verified: `.env.example` section replacement

```bash
# Replace:
# === OpenAI ===
OPENAI_API_KEY=your-openai-api-key-here
LARGE_LLM=gpt-4.1-2025-04-14
SMALL_LLM=gpt-4o-mini-2024-07-18

# With:
# === Anthropic + Voyage AI ===
ANTHROPIC_API_KEY=your-anthropic-api-key-here
VOYAGE_API_KEY=your-voyage-api-key-here
LARGE_LLM=claude-sonnet-4-6
SMALL_LLM=claude-haiku-4-5-20251001
```

Also update the Memory/Personalization section:
```bash
# Replace:
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# With:
EMBEDDING_MODEL=voyage-4
EMBEDDING_DIMENSIONS=1024
```

---

## Runtime State Inventory

Step 2.5: SKIPPED — this is not a rename/refactor/migration phase. Phase 8 makes targeted additions and removals to config and packaging files only.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | All | Yes | 3.11.4 | — |
| pip | requirements.txt install | Yes | (venv) | — |
| langchain-anthropic | CONF-05 (in requirements.txt) | Yes (already in venv) | 0.3.22 | — |
| anthropic | CONF-05 (in requirements.txt) | Yes (already in venv, v0.92.0) | 0.92.0 installed; pin to 0.87.0 | — |
| voyageai | CONF-05 (in requirements.txt) | Yes (already in venv) | 0.3.7 | — |

**No missing dependencies with no fallback.**

Note: All three new packages are already installed in the local venv. `requirements.txt` update is the declaration step; `pip install -r requirements.txt` will confirm.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `OPENAI_API_KEY` inline guard | `ANTHROPIC_API_KEY` + `VOYAGE_API_KEY` inline guard | Phase 8 | Any code importing `OPENAI_API_KEY` from `core.config` breaks until Phase 9/11 fixes imports |
| `LARGE_LLM` no default | `LARGE_LLM` defaults to `claude-sonnet-4-6` | Phase 8 | `agents/config/agent_config.py` fallback `LARGE_LLM or "gpt-4o"` now resolves to `claude-sonnet-4-6` |
| `EMBEDDING_MODEL = text-embedding-3-small` | `EMBEDDING_MODEL = voyage-4` | Phase 8 | `services/embedding_service.py` picks up the new default automatically |
| `EMBEDDING_DIMENSIONS = 1536` | `EMBEDDING_DIMENSIONS = 1024` | Phase 8 | `services/embedding_service.py` picks up new dimensions; DB column is changed in Phase 10 |

**Deprecated/outdated after this phase:**
- `OPENAI_API_KEY` env var: no longer read by `core/config.py`; still referenced by 7 other files (fixed in Phase 9/11)
- `langchain-openai==0.3.25`: removed from requirements.txt
- `openai==1.91.0`: removed from requirements.txt

---

## Open Questions

1. **`LARGE_LLM` default picked up by `agents/config/agent_config.py` fallback**
   - What we know: `agent_config.py` has `LARGE_LLM or "gpt-4o"` as fallback. After Phase 8, `LARGE_LLM` will be `"claude-sonnet-4-6"` by default.
   - What's unclear: Is the fallback string in `agent_config.py` left as `"gpt-4o"` until Phase 9, or changed here? Per CONTEXT.md, Phase 9 handles LLM-03 — do not change it in Phase 8.
   - Recommendation: Leave `agent_config.py` unchanged in Phase 8. Document that `LARGE_LLM or "gpt-4o"` will now evaluate to `"claude-sonnet-4-6"` (the new default), so the fallback string `"gpt-4o"` is dead code but not harmful.

2. **anthropic 0.87.0 vs 0.92.0 in venv**
   - What we know: The venv has `0.92.0` installed; D-05 pins `0.87.0` in requirements.txt.
   - What's unclear: Will `pip install -r requirements.txt` downgrade to `0.87.0` in a fresh install?
   - Recommendation: Yes, a fresh `pip install -r requirements.txt` will install `0.87.0` exactly. The local venv mismatch is not a problem for this phase — the pinned version governs production and CI.

---

## Sources

### Primary (HIGH confidence)

- Direct file inspection: `core/config.py` — current guard pattern, env var loading, exact line numbers
- Direct file inspection: `requirements.txt` — current packages and line positions
- Direct file inspection: `.env.example` — current template content
- Direct file inspection: `scripts/ingest_fiqh.py` — tiktoken dependency confirmed (line 26: `import tiktoken`)
- `pip index versions langchain-anthropic anthropic voyageai` — version availability confirmed 2026-04-09
- `.planning/phases/08-config-dependencies/08-CONTEXT.md` — all decisions locked by user
- `main.py` — lifespan pattern, `validate_supabase_config()` call site confirmed

### Secondary (MEDIUM confidence)

- Grep of all files importing `OPENAI_API_KEY` from `core.config` — 7 files identified; these will need Phase 9/11 changes but are out of scope here

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — packages verified in PyPI and venv; versions confirmed with `pip index versions`
- Architecture: HIGH — full source inspection of `core/config.py`; patterns copied from existing code
- Pitfalls: HIGH — identified from direct code inspection of import graph; no speculation required

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable libraries, no fast-moving APIs in scope)
