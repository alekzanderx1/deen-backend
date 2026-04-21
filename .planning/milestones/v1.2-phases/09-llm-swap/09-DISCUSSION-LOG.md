# Phase 9: LLM Swap - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 09-llm-swap
**Areas discussed:** Classifier preamble parsing, max_tokens in factory functions, get_classifier_model() model size

---

## Classifier Preamble Parsing

| Option | Description | Selected |
|--------|-------------|----------|
| Regex scan | re.search() for any of the 6 known category names anywhere in the response | |
| Structured output | model.with_structured_output(FiqhCategory) with Literal enum — same as sea.py | ✓ |
| Prompt hardening only | Add "CRITICAL: Output ONLY the category name" to system prompt | |

**User's choice:** Structured output
**Notes:** User preferred the bulletproof approach over regex; consistent with the existing `with_structured_output(SEAResult)` pattern already in `sea.py`.

---

## max_tokens in Factory Functions

| Option | Description | Selected |
|--------|-------------|----------|
| Set per-function defaults | generator=4096, classifier=2048, enhancer=512, translator=1024 | ✓ |
| ModelConfig only (LLM-04) | Leave factory functions without max_tokens; rely on LangChain's 1024 default | |
| Single default for all (4096) | All factory functions get max_tokens=4096 | |

**User's choice:** Per-function defaults
**Notes:** User asked how it was set up with OpenAI — clarified that OpenAI doesn't require max_tokens (defaults to model max), but Claude requires it (LangChain default is 1024 which is too low for SEA output). User confirmed sensible values are needed. Agreed on per-function values.

---

## get_classifier_model() Model Size

| Option | Description | Selected |
|--------|-------------|----------|
| Fix to SMALL_LLM now | Aligns with design intent; Haiku is fast/cheap for classification and SEA | |
| Leave as LARGE_LLM for now | Safer during migration — one less variable if something breaks | ✓ |

**User's choice:** Leave as LARGE_LLM for now
**Notes:** User preferred to minimize variables during the migration. SMALL_LLM correction deferred to Phase 11 or follow-up.

---

## Claude's Discretion

- Import style for `ChatAnthropic` (top-level vs. lazy) — planner decides
- Whether `get_translator_model()` keeps `.bind(temperature=0)` — preserve existing behavior

## Deferred Ideas

- `get_classifier_model()` → `SMALL_LLM` correction — deferred, not within Phase 9 scope
