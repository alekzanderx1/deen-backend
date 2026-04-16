---
phase: 08-config-dependencies
verified: 2026-04-09T00:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 6/7
  gaps_closed:
    - "CONF-06: tiktoken retained in requirements.txt — REQUIREMENTS.md updated to reflect intentional keep; gap resolved by requirements update, not code change"
  gaps_remaining: []
  regressions: []
human_verification: []
---

# Phase 8: Config + Dependencies Verification Report

**Phase Goal:** Wire in Anthropic and Voyage AI credentials and replace OpenAI dependencies so the backend is configured to run on the new provider stack.
**Verified:** 2026-04-09
**Status:** passed
**Re-verification:** Yes — after CONF-06 requirements update

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Importing core.config with all three keys set raises no error | VERIFIED | ANTHROPIC_API_KEY, VOYAGE_API_KEY, PINECONE_API_KEY all exported correctly from core/config.py lines 10-12 |
| 2 | Importing core.config without ANTHROPIC_API_KEY raises ValueError | VERIFIED | Guard at line 45: `if not ANTHROPIC_API_KEY or not VOYAGE_API_KEY or not PINECONE_API_KEY` |
| 3 | Importing core.config without VOYAGE_API_KEY raises ValueError | VERIFIED | Same guard covers all three keys; error message names all three |
| 4 | LARGE_LLM resolves to 'claude-sonnet-4-6' when env var absent | VERIFIED | core/config.py line 30: `LARGE_LLM = os.getenv("LARGE_LLM", "claude-sonnet-4-6")` |
| 5 | SMALL_LLM resolves to 'claude-haiku-4-5-20251001' when env var absent | VERIFIED | core/config.py line 31: `SMALL_LLM = os.getenv("SMALL_LLM", "claude-haiku-4-5-20251001")` |
| 6 | EMBEDDING_MODEL resolves to 'voyage-4' when env var absent | VERIFIED | core/config.py line 89: `EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-4")` |
| 7 | EMBEDDING_DIMENSIONS resolves to 1024 when env var absent | VERIFIED | core/config.py line 90: `EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))` |
| 8 | OPENAI_API_KEY is not exported by core.config | VERIFIED | No occurrence of OPENAI_API_KEY anywhere in core/config.py |
| 9 | requirements.txt contains langchain-anthropic==0.3.22, anthropic==0.87.0, voyageai==0.3.7 | VERIFIED | anthropic==0.87.0 at line 8; langchain-anthropic==0.3.22 at line 39; voyageai==0.3.7 at line 119 |
| 10 | requirements.txt does not contain langchain-openai or openai | VERIFIED | grep for 'openai' in requirements.txt returns zero matches |
| 11 | tiktoken is retained in requirements.txt (CONF-06 updated) | VERIFIED | tiktoken==0.9.0 at line 108; REQUIREMENTS.md CONF-06 explicitly states "tiktoken retained (imported directly by scripts/ingest_fiqh.py)" |
| 12 | .env.example documents ANTHROPIC_API_KEY and VOYAGE_API_KEY, no OPENAI_API_KEY | VERIFIED | Lines 10-11 present; no OPENAI_API_KEY anywhere in file |
| 13 | .env.example LLM defaults reflect Claude model names | VERIFIED | Line 12: LARGE_LLM=claude-sonnet-4-6; line 13: SMALL_LLM=claude-haiku-4-5-20251001 |
| 14 | .env.example embedding defaults reflect voyage-4 and 1024 | VERIFIED | Line 54: EMBEDDING_MODEL=voyage-4; line 56: EMBEDDING_DIMENSIONS=1024 |

**Score:** 14/14 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `core/config.py` | Updated API key guards and env var defaults | VERIFIED | ANTHROPIC_API_KEY + VOYAGE_API_KEY exported; combined startup guard at line 45; Claude/Voyage defaults at lines 30-31, 89-90; no OPENAI_API_KEY |
| `requirements.txt` | Pinned Anthropic + Voyage AI packages; OpenAI packages removed | VERIFIED | langchain-anthropic==0.3.22, anthropic==0.87.0, voyageai==0.3.7 present; langchain-openai and openai absent; tiktoken==0.9.0 intentionally retained |
| `.env.example` | Updated env template for v1.2 | VERIFIED | v1.2 header at line 6; Anthropic + Voyage AI section at lines 9-13; voyage-4/1024 embedding defaults; no OpenAI references |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `core/config.py` | module-level startup guard | `if not ANTHROPIC_API_KEY or not VOYAGE_API_KEY or not PINECONE_API_KEY` | VERIFIED | Pattern confirmed at line 45; error message names all three keys |
| `requirements.txt` | `langchain-anthropic==0.3.22` | pip install | VERIFIED | Exact pinned version at line 39 |
| `requirements.txt` | `anthropic==0.87.0` | pip install | VERIFIED | Exact pinned version at line 8 |
| `requirements.txt` | `voyageai==0.3.7` | pip install | VERIFIED | Exact pinned version at line 119 |

### Data-Flow Trace (Level 4)

Not applicable — this phase modifies configuration and packaging files only. No dynamic data rendering involved.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| config imports with all keys set | Python import + 7 key/default assertions | ALL ASSERTIONS PASSED (initial verification) | PASS |
| Guard fires without ANTHROPIC_API_KEY | Python import without key | ValueError mentioning ANTHROPIC_API_KEY (initial verification) | PASS |
| Guard fires without VOYAGE_API_KEY | Python import without key | ValueError mentioning VOYAGE_API_KEY (initial verification) | PASS |
| LARGE_LLM default = claude-sonnet-4-6 | Static read of core/config.py line 30 | `os.getenv("LARGE_LLM", "claude-sonnet-4-6")` confirmed | PASS |
| requirements.txt package assertions | Static grep: tiktoken, anthropic, langchain-anthropic, voyageai present; openai absent | All four present; zero openai matches | PASS |
| .env.example content assertions | Static read of .env.example | All Anthropic/Voyage entries confirmed; no OpenAI references | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| CONF-01 | 08-01-PLAN.md | ANTHROPIC_API_KEY replaces OPENAI_API_KEY in core/config.py startup guard | SATISFIED | core/config.py line 10: `ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")`; guard at line 45 |
| CONF-02 | 08-01-PLAN.md | VOYAGE_API_KEY added to core/config.py with startup guard | SATISFIED | core/config.py line 11: `VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")`; included in guard at line 45 |
| CONF-03 | 08-01-PLAN.md | LARGE_LLM default updated to claude-sonnet-4-6; SMALL_LLM to claude-haiku-4-5-20251001 | SATISFIED | Lines 30-31 confirmed with correct defaults |
| CONF-04 | 08-01-PLAN.md | EMBEDDING_MODEL default updated to voyage-4; EMBEDDING_DIMENSIONS to 1024 | SATISFIED | Lines 89-90 confirmed with correct defaults |
| CONF-05 | 08-02-PLAN.md | langchain-anthropic==0.3.22, anthropic==0.87.0, voyageai==0.3.7 added to requirements.txt | SATISFIED | All three packages present at exact pinned versions |
| CONF-06 | 08-02-PLAN.md | langchain-openai, openai removed from requirements.txt; tiktoken retained for ingestion scripts | SATISFIED | langchain-openai and openai absent (zero grep matches); tiktoken==0.9.0 present; REQUIREMENTS.md updated to document intentional retention |
| CONF-07 | 08-02-PLAN.md | .env.example updated — ANTHROPIC_API_KEY + VOYAGE_API_KEY added, OPENAI_API_KEY removed | SATISFIED | All assertions confirmed; v1.2 header present; no OpenAI references |

**Orphaned requirements:** None. All 7 CONF-01 through CONF-07 IDs mapped to Phase 8 in REQUIREMENTS.md are claimed in plan frontmatter and verified in the codebase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODO/FIXME/placeholder/stub patterns found in any of the three modified files.

### Human Verification Required

None. All checks are verifiable programmatically.

### Gaps Summary

No gaps. All 7 requirements are fully satisfied.

The only gap from the initial verification — CONF-06's tiktoken question — is resolved by the requirements update: REQUIREMENTS.md now explicitly documents that tiktoken is intentionally retained because `scripts/ingest_fiqh.py` imports it directly. The codebase state (tiktoken==0.9.0 in requirements.txt) correctly matches the updated requirement as written.

**Phase 8 goal fully achieved:** `core/config.py` exports the correct Anthropic and Voyage AI keys and model defaults, `requirements.txt` has all three provider packages pinned and all OpenAI packages removed, and `.env.example` guides developers to the new provider stack. The backend is configured to run on the Anthropic + Voyage AI provider stack.

---

_Verified: 2026-04-09_
_Verifier: Claude (gsd-verifier)_
