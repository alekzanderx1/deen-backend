# Phase 8: Config + Dependencies - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 08-config-dependencies
**Areas discussed:** tiktoken removal scope, API key guard pattern

---

## tiktoken Removal Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Keep tiktoken in requirements.txt | Ingestion script still uses tiktoken; remove langchain-openai and openai only | ✓ |
| Remove tiktoken, fix the script now | Swap token counting to character-based heuristic in ingest_fiqh.py | |
| Remove tiktoken, mark script broken | Remove from requirements.txt; fix in Phase 11 cleanup | |

**User's choice:** Keep tiktoken in requirements.txt
**Notes:** `scripts/ingest_fiqh.py` directly imports tiktoken for PDF chunking token counting (`ENCODING = tiktoken.get_encoding("cl100k_base")`). The ingestion script is still useful; breaking it would be scope creep. CONF-06 scope narrowed to langchain-openai + openai removal only.

---

## API Key Guard Pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Both inline (same as OPENAI_API_KEY) | Combined inline guard at module level; tests need dummy keys in env | ✓ |
| Both deferred (Supabase pattern) | validate_claude_config() called from main.py lifespan; tests don't need keys | |
| ANTHROPIC inline, VOYAGE deferred | Split by role — ANTHROPIC core, VOYAGE embedding-only | |

**User's choice:** Both inline
**Notes:** Consistent with the existing OPENAI_API_KEY guard pattern. Tests importing core.config will need ANTHROPIC_API_KEY and VOYAGE_API_KEY set in their environment (as dummy values).

---

## Claude's Discretion

- Exact position of new inline guard within core/config.py
- Whether to add inline comments explaining the two-pattern approach (inline vs deferred)

## Deferred Ideas

None.
