# Phase 8: Config + Dependencies - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire ANTHROPIC_API_KEY + VOYAGE_API_KEY into `core/config.py`; swap pip packages (add langchain-anthropic, anthropic, voyageai; remove langchain-openai, openai — NOT tiktoken); update env var defaults for LARGE_LLM, SMALL_LLM, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS; update `.env.example`. The app must boot with Claude + Voyage AI credentials and fail fast when they are absent. No pipeline logic, no LLM wiring, no embedding calls — config and packaging only.

</domain>

<decisions>
## Implementation Decisions

### API Key Startup Guards (CONF-01, CONF-02)

- **D-01:** Both `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` use the **inline module-level guard** pattern — same as the existing `OPENAI_API_KEY` guard. A single combined `if not ANTHROPIC_API_KEY or not VOYAGE_API_KEY or not PINECONE_API_KEY` raise at module level (replacing the current `OPENAI_API_KEY` check). Tests that import `core.config` must set dummy values for `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` in their environment.

### tiktoken Removal Scope (CONF-06)

- **D-02:** `tiktoken` is **kept** in `requirements.txt`. The ingestion script `scripts/ingest_fiqh.py` uses it directly (`import tiktoken; ENCODING = tiktoken.get_encoding("cl100k_base")`). CONF-06 scope is narrowed to removing `langchain-openai` and `openai` only — tiktoken is NOT removed.

### Env Var Defaults (CONF-03, CONF-04)

- **D-03:** `LARGE_LLM` default → `claude-sonnet-4-6`; `SMALL_LLM` default → `claude-haiku-4-5-20251001`. These are added as default values in `os.getenv()` calls. No additional validation guard beyond the existing no-default pattern.
- **D-04:** `EMBEDDING_MODEL` default → `voyage-4`; `EMBEDDING_DIMENSIONS` default → `1024`.

### Package Versions (CONF-05)

- **D-05:** Pin exact versions as specified in requirements: `langchain-anthropic==0.3.22`, `anthropic==0.87.0`, `voyageai==0.3.7`. Trust pinned versions — no version re-resolution.

### Claude's Discretion

- Exact position of the inline guard in `core/config.py` (before or after Pinecone guard) — planner decides based on logical grouping.
- Whether to add a brief comment explaining the deferred Supabase pattern vs inline pattern (for future maintainers).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Config and Requirements
- `core/config.py` — Current guard patterns, env var loading; the file being modified in this phase
- `.env.example` — Current template; CONF-07 updates it
- `requirements.txt` — Current pinned dependencies; CONF-05/CONF-06 modify it

### Phase Requirements
- `.planning/REQUIREMENTS.md` §Config + Dependencies (CONF-01..07) — Acceptance criteria for all 7 requirements

### Script with tiktoken dependency
- `scripts/ingest_fiqh.py` — Uses `tiktoken` directly; must NOT be broken by this phase (tiktoken stays)

### Downstream phases (for awareness only — do not modify)
- `services/embedding_service.py` — Will use VOYAGE_API_KEY in Phase 10; this phase only adds it to config
- `agents/config/agent_config.py` — Will use new LARGE_LLM default in Phase 9; this phase only adds the default to config

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing inline guard pattern (`if not OPENAI_API_KEY or not PINECONE_API_KEY: raise ValueError(...)`) — copy pattern, replace OPENAI_API_KEY with ANTHROPIC_API_KEY, add VOYAGE_API_KEY
- `validate_supabase_config()` deferred pattern — reference only; NOT used for new keys per D-01

### Established Patterns
- `core/config.py` module-level: env vars loaded at import time via `os.getenv()`, guards raise `ValueError` immediately
- `EMBEDDING_MODEL` and `EMBEDDING_DIMENSIONS` already use `os.getenv()` with defaults — same pattern for updated defaults

### Integration Points
- `agents/config/agent_config.py`: fallback `LARGE_LLM or "gpt-4o"` will pick up the new default from config (Phase 9 work, not this phase)
- `services/embedding_service.py`: uses `EMBEDDING_MODEL` and `EMBEDDING_DIMENSIONS` from config — will get new defaults automatically
- `db/models/embeddings.py`: hardcodes `EMBEDDING_DIMENSIONS = 1536` separately — **not changed in this phase** (changed in Phase 10)
- `alembic/versions/20260122_create_embedding_tables.py`: also hardcodes 1536 — **not changed in this phase** (Phase 10 migration handles this)

</code_context>

<specifics>
## Specific Ideas

No specific references or "I want it like X" moments — open to standard approaches for guard and requirements.txt formatting.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-config-dependencies*
*Context gathered: 2026-04-09*
