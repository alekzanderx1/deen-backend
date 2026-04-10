# Requirements: v1.2 Claude Migration

## Milestone Goal

Replace all OpenAI model usage with Anthropic Claude (LLM) and Voyage AI (embeddings) across the full pipeline. The LangGraph + FastAPI + Pinecone + Redis architecture is unchanged — only the model providers swap.

## v1 Requirements

### Config + Dependencies (CONF)

- [x] **CONF-01**: `ANTHROPIC_API_KEY` replaces `OPENAI_API_KEY` in `core/config.py` startup validation guard
- [x] **CONF-02**: `VOYAGE_API_KEY` added to `core/config.py` with startup validation guard
- [x] **CONF-03**: `LARGE_LLM` env var default updated to `claude-sonnet-4-6`; `SMALL_LLM` to `claude-haiku-4-5-20251001`
- [x] **CONF-04**: `EMBEDDING_MODEL` default updated to `voyage-4`; `EMBEDDING_DIMENSIONS` to `1024`
- [x] **CONF-05**: `langchain-anthropic==0.3.22`, `anthropic==0.87.0`, `voyageai==0.3.7` added to `requirements.txt`
- [x] **CONF-06**: `langchain-openai`, `openai` removed from `requirements.txt`; `tiktoken` retained (imported directly by `scripts/ingest_fiqh.py`)
- [x] **CONF-07**: `.env.example` updated — `ANTHROPIC_API_KEY` + `VOYAGE_API_KEY` added, `OPENAI_API_KEY` removed

### LLM Migration (LLM)

- [x] **LLM-01**: `core/chat_models.py` factory functions use `ChatAnthropic(api_key=ANTHROPIC_API_KEY)` instead of `init_chat_model(..., openai_api_key=)`
- [ ] **LLM-02**: `agents/core/chat_agent.py` uses `ChatAnthropic` with `ANTHROPIC_API_KEY`; `openai_api_key=` kwarg removed
- [x] **LLM-03**: `agents/config/agent_config.py` fallback model string updated from `gpt-4o` to `claude-sonnet-4-6`
- [x] **LLM-04**: `ModelConfig` in `agent_config.py` gets `max_tokens=4096` default and temperature validator `le=1.0`
- [ ] **LLM-05**: `modules/fiqh/classifier.py` `classify_fiqh_query()` response parsing robust to Claude preamble text
- [ ] **LLM-06**: `_agent_node` in `chat_agent.py` filters empty `AIMessage` content before passing history to LLM
- [ ] **LLM-07**: `scripts/hikmah_generation/generate_hikmah_tree.py` updated to use `ANTHROPIC_API_KEY`

### Embedding Migration (EMBED)

- [ ] **EMBED-01**: `services/embedding_service.py` uses `voyageai.Client(api_key=VOYAGE_API_KEY)` to generate embeddings
- [ ] **EMBED-02**: `generate_embedding()` and `generate_embeddings_batch()` adapted to voyage-4 response shape (`result.embeddings`)
- [ ] **EMBED-03**: `scripts/reembed_pgvector.py` backfill script re-generates voyage-4 embeddings for all existing `note_embeddings` and `lesson_chunk_embeddings` rows
- [ ] **EMBED-04**: `db/models/embeddings.py` `Vector(1536)` columns changed to `Vector(1024)`
- [ ] **EMBED-05**: Alembic migration: add `embedding_new vector(1024)` column → backfill populates it → drop old `vector(1536)` column → rename → recreate HNSW indexes

### Cleanup (CLEAN)

- [ ] **CLEAN-03**: Dead `from openai import OpenAI` and module-level `OpenAI()` instances removed from 4 files (`stream_generator.py`, `classification/classifier.py`, `fiqh/classifier.py`, `pipeline.py`)
- [ ] **CLEAN-04**: `openai` and `langchain-openai` removal verified — `grep -r "from openai"` returns zero results; app starts clean

## Future Requirements

- Retry logic with `tenacity` for Claude Tier 1 rate limits (50 RPM) under concurrent load
- Reasoning / extended thinking mode for complex fiqh queries (Claude Sonnet 4.6 supports it)
- Voyage AI `voyage-code-3` for any future code-adjacent retrieval tasks

## Out of Scope

- Replacing Pinecone retrieval embeddings (HuggingFace `all-mpnet-base-v2` — unaffected, stays as-is)
- Adding other Anthropic model providers (Bedrock, Vertex) — direct API only
- Frontend changes — backend API only; SSE protocol is unchanged
- Fine-tuning or prompting optimisation for Claude — model swap only, prompts unchanged
- Adding Claude extended thinking / reasoning mode — out of scope for this migration

## Traceability

| REQ-ID | Phase | Plan |
|--------|-------|------|
| CONF-01 | Phase 8 | — |
| CONF-02 | Phase 8 | — |
| CONF-03 | Phase 8 | — |
| CONF-04 | Phase 8 | — |
| CONF-05 | Phase 8 | — |
| CONF-06 | Phase 8 | — |
| CONF-07 | Phase 8 | — |
| LLM-01 | Phase 9 | 09-01-PLAN.md |
| LLM-02 | Phase 9 | — |
| LLM-03 | Phase 9 | 09-01-PLAN.md |
| LLM-04 | Phase 9 | 09-01-PLAN.md |
| LLM-05 | Phase 9 | — |
| LLM-06 | Phase 9 | — |
| LLM-07 | Phase 9 | — |
| EMBED-01 | Phase 10 | — |
| EMBED-02 | Phase 10 | — |
| EMBED-03 | Phase 10 | — |
| EMBED-04 | Phase 10 | — |
| EMBED-05 | Phase 10 | — |
| CLEAN-03 | Phase 11 | — |
| CLEAN-04 | Phase 11 | — |
