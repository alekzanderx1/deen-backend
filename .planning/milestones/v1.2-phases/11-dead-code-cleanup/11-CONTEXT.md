# Phase 11: Dead Code Cleanup — Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove all dead OpenAI references from application code now that the Claude + HuggingFace migration (Phases 8-10) is complete. The `openai` and `langchain-openai` packages were already removed from `requirements.txt` in Phase 8 (CONF-06). Phase 11 removes the remaining dead import statements and module-level `OpenAI()` instantiations that were left as compatibility stubs, updates the now-stale test mocks in `test_embedding_service.py`, and removes the `OPENAI_API_KEY = ""` shim from `core/config.py`.

After this phase: `grep -r "from openai"` returns zero hits across all application files and the full test suite passes with `openai` uninstalled.

## Actual codebase state (verified 2026-04-10)

**Files with dead `from openai import OpenAI` (CLEAN-03):**
- `modules/classification/classifier.py:1` — `from openai import OpenAI` (unused; all calls go through `chat_models`)
- `modules/classification/classifier.py:6` — `from core.config import OPENAI_API_KEY` (unused)
- `modules/generation/stream_generator.py:2` — `from openai import OpenAI` (dead)
- `modules/generation/stream_generator.py:3` — `from core.config import OPENAI_API_KEY` (dead)
- `modules/generation/stream_generator.py:13` — `client = OpenAI(api_key=OPENAI_API_KEY)` (dead module-level instantiation)
- `modules/enhancement/enhancer.py:1` — `from core.config import OPENAI_API_KEY` (unused)
- `modules/generation/generator.py:1` — `from core.config import OPENAI_API_KEY` (unused)

**Config shim to remove (CLEAN-03):**
- `core/config.py:97-101` — `OPENAI_API_KEY = ""` stub + comment explaining Phase 11 will remove it

**Comments referencing OpenAI (cosmetic — in core/pipeline.py):**
- `core/pipeline.py:33,74,110` — inline comments `# Step 5: Generate AI response using OpenAI` etc.

**Tests to update (CLEAN-04):**
- `tests/test_embedding_service.py` — fixtures mock `services.embedding_service.OpenAI` and assert 1536-dim vectors. `EmbeddingService` now uses `getDenseEmbedder()` from HuggingFace (768-dim). Tests need to mock `modules.embedding.embedder.getDenseEmbedder` instead.

**Package to remove:**
- `voyageai==0.3.7` in `requirements.txt` — added in Phase 8, never used after Phase 10 switched to HuggingFace (Phase 10 context: "voyageai stays for now — Phase 11 handles package cleanup")

**Already clean (no action needed):**
- `openai` and `langchain-openai` — absent from `requirements.txt` ✓
- `services/embedding_service.py` — already uses `getDenseEmbedder()`, no OpenAI ✓
- `modules/fiqh/classifier.py` — no openai imports ✓
</domain>

<decisions>
## Implementation Decisions

### D-01: Dead import removal
Remove all `from openai import OpenAI`, `from core.config import OPENAI_API_KEY`, and `client = OpenAI(...)` lines from the 4 application modules. Do not change function logic — these identifiers are unused after Phase 9.

### D-02: Config shim removal
Delete `core/config.py` lines 97-101 (the `OPENAI_API_KEY = ""` stub and its comment). Once the imports referencing it are gone there is no reason to export it.

### D-03: Test rewrite
`tests/test_embedding_service.py` fixtures mock the wrong object. Rewrite `mock_openai_client` → `mock_embedder` fixture that patches `modules.embedding.embedder.getDenseEmbedder` to return a mock with `embed_query` and `embed_documents` methods returning 768-dim vectors. Update all assertion sites that assume 1536 dimensions to 768.

### D-04: voyageai package removal
Remove `voyageai==0.3.7` from `requirements.txt`. No application code imports it (grep confirmed).

### D-05: pipeline.py comments
Update 3 inline comments in `core/pipeline.py` that say "using OpenAI" to say "using LLM" — low-effort cosmetic correctness.

### D-06: Plan split
- Plan 1: Application code + config shim + requirements.txt (no test impact)
- Plan 2: Test file rewrite + final verification (grep + startup check)
</decisions>
