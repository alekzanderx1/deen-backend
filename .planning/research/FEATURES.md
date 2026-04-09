# Feature Research: Claude + Voyage AI Migration (v1.2)

**Domain:** LLM provider swap (OpenAI → Anthropic Claude) + embedding provider swap (OpenAI → Voyage AI)
**Researched:** 2026-04-09
**Overall confidence:** HIGH for tool calling, streaming, structured output, API key conventions (official docs + LangChain reference verified). MEDIUM for embedding quality comparison on English Islamic text (vendor benchmarks only; no independent Islamic-domain benchmark found).

---

## Tool Calling

### Compatibility with existing `.bind_tools()` pattern

**Verdict: YES, fully compatible. Interface is identical.**

`langchain-anthropic` exposes `ChatAnthropic`, which implements the same LangChain `BaseChatModel` interface as `ChatOpenAI`. The `.bind_tools(tools)` call works with the same `@tool`-decorated LangChain tool definitions already in `agents/tools/`. No changes to tool definitions or the tool list in `ChatAgent.__init__` are required.

```python
# Current pattern — works unchanged with ChatAnthropic
llm = init_chat_model(model="claude-sonnet-4-6", ...)
llm_with_tools = llm.bind_tools(self.tools)
```

`init_chat_model` from `langchain.chat_models` auto-detects provider by model name prefix (`claude-*` → Anthropic). This means `core/chat_models.py` functions need only the model string and API key parameter updated.

### Known issue: empty `AIMessage` with `astream()` and tool calling (HIGH SEVERITY — verify before shipping)

A confirmed bug exists in `langchain-anthropic` when combining `astream()` with programmatic tool calling using Anthropic's "advanced-tool-use" beta header (GitHub issue #34406, opened Dec 2025). The aggregated `AIMessage` after streaming can be empty rather than containing tool call data.

**Impact to this codebase:** The main agentic pipeline uses `compiled_graph.astream()` (LangGraph node events, not raw model `astream`). The `_agent_node` uses `self.llm.invoke(messages)` — synchronous invoke, not `astream()`. The bug specifically targets `ChatAnthropic.astream()` with advanced tool use beta headers. The current code does not use that beta header, and uses `invoke()` inside nodes. **Risk is LOW** but must be verified with an integration test after switching.

### Separate issue: system-message-only requests in tool flows

GitHub issue #31657 documents an error when a tool-calling conversation passes a system message without any human/assistant turns. In `ChatAgent._agent_node`, `SystemMessage` is inserted at index 0 of the messages list before any tool calls. This pattern is fine — the issue only triggers when the messages list contains *only* a `SystemMessage` with no human turn. The existing code always has a `HumanMessage` appended immediately after inserting the system message.

### Parallel tool calls

Claude Sonnet 4 supports parallel tool execution natively. The existing graph processes tool calls sequentially via `ToolNode` — this behavior is unchanged. Claude may emit multiple tool calls in a single `AIMessage` (parallel), which `ToolNode` already handles correctly.

**Confidence:** HIGH — verified against LangChain official docs and known open issues.

---

## Streaming

### Compatibility with existing `chain.stream()` / `astream()` interface

**Verdict: YES, fully compatible. Same Runnable interface.**

`ChatAnthropic` implements the same LangChain `Runnable` interface. `chain.stream()` (sync) and `chain.astream()` (async) work identically. The token streaming in `core/pipeline_langgraph.py` uses `chain.stream()` as a synchronous iterator inside an `async def` generator — this pattern works unchanged with Claude.

The `compiled_graph.astream()` call in `ChatAgent.astream()` is LangGraph-level streaming (node events), not model-level streaming. This is unaffected by the LLM provider swap.

### Streaming token format differences

Claude's streaming response emits tokens as `AIMessageChunk` objects with `.content` as a string — identical to OpenAI's format. The `response_chunk` SSE event assembly loop in `pipeline_langgraph.py` requires no changes.

Claude can include `thinking` blocks in streaming output if extended thinking is enabled. This feature is disabled by default and should remain disabled for this project (adds latency and cost, adds no value for retrieval-grounded answers).

**Confidence:** HIGH — verified against LangChain streaming documentation.

---

## Structured Output

### Compatibility with `model.with_structured_output(SEAResult)`

**Verdict: YES, fully compatible. Method signature identical.**

`ChatAnthropic.with_structured_output(PydanticModel)` is supported and works with the same Pydantic `BaseModel` subclasses used today. The `SEAResult` and `Finding` Pydantic models in `modules/fiqh/sea.py` require zero changes.

```python
# Current pattern in sea.py — works unchanged
model = chat_models.get_classifier_model()
structured_model = model.with_structured_output(SEAResult)
result = structured_model.invoke(prompt_messages)
```

**Implementation method:** By default, `langchain-anthropic` uses Anthropic's function-calling API under the hood for structured output. To use Anthropic's native JSON schema mode (which guarantees schema adherence), pass `method="json_schema"`. The default (function-calling based) is sufficient for SEA and does not require changes.

**Version requirement:** `with_structured_output` requires `langchain-anthropic >= 1.1.0`. The current requirements.txt does not pin langchain-anthropic at all (it is not in requirements.txt — it would be a new addition). Install `langchain-anthropic >= 1.3.0` (latest stable as of April 2026).

**Confidence:** HIGH — verified against LangChain reference docs and Anthropic structured output docs.

---

## System Prompt Behavior

### How Claude handles `SystemMessage` vs OpenAI

**Functional difference: LOW impact, but one structural note.**

In the Anthropic Messages API, the `system` prompt is a top-level field separate from the `messages` array. LangChain's `ChatAnthropic` transparently handles this: it extracts `SystemMessage` objects from the messages list and places them in the API request's `system` field. No code changes needed in `chat_agent.py` or the agent prompts.

**Behavioral differences:**

1. **Instruction following:** Claude Sonnet 4 follows system prompt instructions with high fidelity. The existing system prompt in `agents/prompts/agent_prompts.py` (AGENT_SYSTEM_PROMPT) should work as-is.

2. **Refusal behavior:** Claude has built-in content policies that overlap somewhat with the UNETHICAL classifier. In practice for Islamic education content, this does not cause spurious refusals — Claude's policies target clearly harmful content, not religious guidance.

3. **Claude 4 best practices:** Anthropic's Claude 4 prompt engineering guide recommends being explicit about desired behavior rather than listing forbidden behaviors. The current system prompts are positive-framing and should work well.

4. **Empty content in tool flows:** When Claude returns a tool call response, the `AIMessage.content` may be an empty string `""` (tool call data is in `tool_calls`, not `content`). This is the same behavior as OpenAI. The existing `_should_continue` routing checks `getattr(last_message, "tool_calls", None)` — this works correctly.

**Confidence:** MEDIUM — behavioral nuances based on published Claude 4 guidance and community reports.

---

## Context Window: claude-haiku-4-5 vs gpt-4o-mini

### Practical implications for classification and SEA tasks

| Property | claude-haiku-4-5-20251001 | gpt-4o-mini-2024-07-18 |
|----------|--------------------------|------------------------|
| Context window (input) | 200,000 tokens | 128,000 tokens |
| Max output tokens | 8,192 | 16,384 |
| Structured output | Yes (via tool calling / json_schema) | Yes (json_schema native) |

**For the fiqh classifier (`classify_fiqh_query`):** The input is a single user query (< 100 tokens) + a fixed system prompt (~350 tokens). Context window size is irrelevant at this scale — both models handle it trivially.

**For SEA (`assess_evidence`):** The input is the user query + formatted retrieved evidence (up to 20 docs × ~500 tokens each = ~10,000 tokens) + system prompt (~300 tokens). This fits comfortably in both context windows. The 200K Haiku context window becomes an advantage only if evidence volume grows substantially (e.g., evidence from 50+ retrieved docs). Current max is 20 docs per iteration × 3 iterations = 60 docs, still well within gpt-4o-mini's 128K limit.

**For query decomposition and refinement tasks:** Same conclusion — well within both limits.

**Practical impact:** The larger context window of Haiku 4.5 provides no meaningful advantage for current task shapes. The more relevant consideration is instruction-following quality for the 6-category classifier output — Haiku 4.5 has shown higher consistency on nuanced classification compared to GPT-4o-mini in published comparisons. Validate with a sample of 20+ fiqh queries after migration.

**Confidence:** MEDIUM — context window specs from official model pages; classification quality comparison from third-party benchmarks, not fiqh-domain-specific.

---

## Embedding Quality: voyage-4 vs text-embedding-3-small

### Dimension comparison and migration requirements

| Property | voyage-4 | text-embedding-3-small |
|----------|----------|----------------------|
| Default dimensions | 1024 | 1536 |
| Supported dimensions | 256, 512, 1024, 2048 | 256–1536 (variable) |
| Context window | 32,000 tokens | 8,191 tokens |
| Architecture | MoE (Mixture of Experts) | Dense transformer |

**The 1024 vs 1536 dimension difference requires a DB migration.** Both `note_embeddings` and `lesson_chunk_embeddings` tables have `Vector(1536)` columns (hard-coded in `db/models/embeddings.py` as `EMBEDDING_DIMENSIONS = 1536`). These must be altered to `Vector(1024)`. All existing pgvector data in these tables must be re-embedded and re-inserted — old 1536-dim vectors are incompatible with 1024-dim column constraints.

voyage-4 can also produce 2048-dim vectors via Matryoshka learning (MRL). Using 2048 dims would avoid shrinking the column, but adds ~2x storage cost and query latency. **Recommendation: use 1024 (voyage-4 default) and migrate the column.** This is the documented voyage-4 recommended dimension for general retrieval tasks.

### Quality on English Islamic text

**Verdict: voyage-4 is higher quality than text-embedding-3-small for general English retrieval. No Islamic-domain-specific benchmark exists.**

On Voyage AI's RTEB benchmark (29 retrieval datasets), voyage-4 outperforms OpenAI's text-embedding-3-large by 14.05% and text-embedding-3-small by a larger margin. The Deen app uses `text-embedding-3-small` — this is the weakest OpenAI embedding model, so the quality gap favoring voyage-4 is likely meaningful.

The Islamic text corpus (Sistani's "Islamic Laws", hadith collections) is English-language domain-specific legal/religious text. voyage-4 is designed for general-purpose retrieval across diverse domains. No independent Islamic-domain benchmark was found. However, for English legal/procedural text retrieval, voyage-4's retrieval quality improvements on MTEB are well-documented.

**Caveat on vendor benchmarks:** Voyage AI's benchmarks are self-reported on their own RTEB dataset selection. Independent MTEB leaderboard results (as of early 2026) confirm voyage-4's advantage over `text-embedding-3-small` on English retrieval tasks, but the exact margin varies by domain.

**Pinecone indexes (Fiqh + Hadith + Quran):** These use a separate embedding pipeline (`modules/embedding/embedder.py`) via HuggingFace `all-mpnet-base-v2` (dense) and TF-IDF sparse. These are NOT OpenAI embeddings and are NOT affected by this migration. The migration scope is only the pgvector columns in PostgreSQL used by `EmbeddingService`.

**Confidence:** MEDIUM — quality superiority well-supported for English retrieval generally; Islamic-domain specific quality is inferred, not measured.

---

## API Key Conventions

### LLM: Anthropic Claude

The official Anthropic API environment variable is `ANTHROPIC_API_KEY`. This is the canonical name, documented in all Anthropic SDK and langchain-anthropic references.

`ChatAnthropic` (and `init_chat_model` with a `claude-*` model) auto-reads `ANTHROPIC_API_KEY` from the environment. The `anthropic_api_key` parameter (alias `api_key`) can be passed explicitly, but if not provided, the env var is used automatically.

**The user has `CLAUDE_API_KEY` in their `.env`.** This will NOT be auto-read by the SDK. Two options:
- Rename the env var to `ANTHROPIC_API_KEY` (recommended — aligns with SDK auto-loading)
- Read `CLAUDE_API_KEY` in `core/config.py` and pass it explicitly as `api_key=CLAUDE_API_KEY` when constructing `ChatAnthropic`

Explicit passing is more transparent and avoids global env var rename. Either approach works. The `core/config.py` already reads `OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")` — the same pattern applies: `CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")` and pass to `init_chat_model(..., api_key=CLAUDE_API_KEY)`.

Note: `core/config.py` line 44 currently raises `ValueError` if `OPENAI_API_KEY` is missing. This guard must be updated to check for the Claude key instead.

### Embeddings: Voyage AI

The Voyage AI environment variable is `VOYAGE_API_KEY`. The `langchain-voyageai` package auto-reads this. The `voyageai` SDK also reads it.

Two integration paths:
1. `pip install langchain-voyageai` — provides `VoyageAIEmbeddings` class compatible with LangChain's embeddings interface
2. `pip install voyageai` — the native SDK; more direct control, less abstraction

For this codebase, `EmbeddingService` directly calls `self.client.embeddings.create(...)` using the OpenAI client. The replacement should use `voyageai.Client` or `langchain-voyageai`'s `VoyageAIEmbeddings`. Using `langchain-voyageai` is preferred for consistency with the existing LangChain-heavy stack.

---

## Summary Table

| Feature | OpenAI Behavior | Claude Behavior | Migration Complexity | Risk |
|---------|----------------|-----------------|---------------------|------|
| `.bind_tools()` | Works via langchain-openai | Works via langchain-anthropic | Low — same interface | LOW |
| Tool call format | `tool_calls` on AIMessage | `tool_calls` on AIMessage | None | LOW |
| `chain.stream()` / `astream()` | Token chunks as AIMessageChunk | Token chunks as AIMessageChunk | None | LOW |
| `compiled_graph.astream()` | Works (LangGraph) | Works (LangGraph) | None | LOW |
| `with_structured_output(Pydantic)` | Works | Works — same method signature | None | LOW |
| System prompt (SystemMessage) | In messages list | Extracted to `system` field by LangChain | None — LangChain handles | LOW |
| API key env var | `OPENAI_API_KEY` | `ANTHROPIC_API_KEY` (user has `CLAUDE_API_KEY`) | Low — update config.py | LOW |
| Embedding dimensions | 1536 (text-embedding-3-small) | 1024 (voyage-4 default) | Medium — Alembic migration required | MEDIUM |
| Embedding data | Existing pgvector rows (1536) | Must re-embed all existing rows (1024) | Medium — re-embed job required | MEDIUM |
| EmbeddingService client | `openai.OpenAI` | `voyageai.Client` or `VoyageAIEmbeddings` | Low — isolated to EmbeddingService | LOW |
| Embedding env var | `OPENAI_API_KEY` | `VOYAGE_API_KEY` | Low | LOW |
| `astream()` + tool calling bug | Not present | Exists (issue #34406, Dec 2025) | None for this codebase (uses `invoke` inside nodes) | LOW — verify with test |
| Pinecone embeddings (fiqh/hadith/Quran) | all-mpnet-base-v2 (HuggingFace) | Unchanged — not affected | None | NONE |

---

## Dependencies Introduced / Removed

**Add:**
- `langchain-anthropic >= 1.3.0` — Claude chat model integration
- `langchain-voyageai >= 0.1.4` — Voyage AI embeddings integration (OR `voyageai >= latest`)

**Remove:**
- `langchain-openai` — no longer needed for LLM (kept only if OpenAI embeddings are used elsewhere)
- `openai` direct SDK — used in `EmbeddingService` and has 3 global import references per PROJECT.md; remove after migration

**Audit required:** Search for all `from openai import` and `import openai` usages before removing the `openai` package from requirements.txt. `EmbeddingService` is the primary user; confirm no other service uses the OpenAI client for embeddings or completions.

---

## Key Migration Steps and Their Dependencies

```
Step 1: Add langchain-anthropic + langchain-voyageai to requirements.txt
         (no code changes yet, no breaking changes)

Step 2: Update core/config.py
         - Remove OPENAI_API_KEY guard (ValueError on line 44-45)
         - Add CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
         - Add VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
         - Update EMBEDDING_MODEL, EMBEDDING_DIMENSIONS (1536 → 1024)
         (breaks EmbeddingService and chat_models — must complete steps 3+4 immediately)

Step 3: Update core/chat_models.py
         - Replace openai_api_key=OPENAI_API_KEY with api_key=CLAUDE_API_KEY
         - Update model strings: LARGE_LLM → claude-sonnet-4-6, SMALL_LLM → claude-haiku-4-5-20251001
         (LangChain auto-detects Anthropic from model name prefix)

Step 4: Update services/embedding_service.py
         - Replace OpenAI client with Voyage AI client
         - Update generate_embedding() and generate_embeddings_batch()
         - No change to callers (batch interface preserved)

Step 5: Alembic migration — resize Vector columns 1536 → 1024
         - ALTER COLUMN embedding TYPE Vector(1024) in note_embeddings and lesson_chunk_embeddings
         - Update db/models/embeddings.py EMBEDDING_DIMENSIONS = 1024

Step 6: Re-embed existing data
         - All existing note_embeddings and lesson_chunk_embeddings rows are invalidated
         - Write a one-shot re-embedding script or truncate + let app regenerate lazily
         - If data volume is small (dev/staging), truncate is simplest
         - If production data exists, script required

Step 7: Remove langchain-openai and openai from requirements.txt
         - Only after verifying no remaining OpenAI references
         - Audit: grep -r "from openai import\|import openai\|langchain_openai\|langchain-openai" .
```

Steps 1-4 must land together (a single plan/PR) because core/config.py changes break both EmbeddingService and chat_models simultaneously. Steps 5-6 are the DB migration and can be a separate plan.

---

## Sources

- [LangChain ChatAnthropic integration](https://docs.langchain.com/oss/python/integrations/chat/anthropic) — bind_tools, with_structured_output, streaming
- [langchain_anthropic API reference](https://python.langchain.com/api_reference/anthropic/chat_models/langchain_anthropic.chat_models.ChatAnthropic.html) — anthropic_api_key field, env var auto-read
- [langchain-anthropic PyPI](https://pypi.org/project/langchain-anthropic/) — version 1.3.4 (latest stable)
- [GitHub issue #34406 — empty AIMessage with astream + tool calling](https://github.com/langchain-ai/langchain/issues/34406) — Dec 2025, status: under investigation
- [GitHub issue #31657 — system messages in tool calling flows](https://github.com/langchain-ai/langchain/issues/31657) — known edge case
- [Voyage AI embeddings docs](https://docs.voyageai.com/docs/embeddings) — voyage-4 dimensions (1024 default), context length 32K
- [Voyage AI voyage-4 model announcement](https://blog.voyageai.com/2026/01/15/voyage-4/) — MoE architecture, quality benchmarks vs OpenAI
- [langchain-voyageai PyPI](https://pypi.org/project/langchain-voyageai/) — LangChain integration package
- [VOYAGE_API_KEY env var reference](https://reference.langchain.com/python/langchain-community/embeddings/voyageai/VoyageEmbeddings/voyage_api_key) — confirmed env var name
- [Claude 4 best practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices) — system prompt guidance
- [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — json_schema mode
- [Claude Haiku 4.5 vs GPT-4o-mini comparison](https://blog.galaxy.ai/compare/claude-haiku-4-5-vs-gpt-4o-mini) — context window and classification quality
