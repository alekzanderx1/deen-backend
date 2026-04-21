# Milestones

## v1.2 Claude Migration (Shipped: 2026-04-10)

**Phases completed:** 5 phases, 9 plans, 20 tasks

**Key accomplishments:**

- One-liner:
- ChatAnthropic replaces init_chat_model/OpenAI in all four factory functions, OPENAI_API_KEY shim added for legacy import compat, ModelConfig updated with Claude API constraints (temperature<=1.0, max_tokens=4096)
- ChatAnthropic wired end-to-end in ChatAgent and hikmah script; fiqh classifier made preamble-safe via with_structured_output(FiqhCategory); D-08 AIMessage filter added to prevent Claude tool-call sequence crashes
- One-liner:
- One-liner:
- Dead `openai` imports, `OPENAI_API_KEY` references, and `voyageai` dependency fully excised from application code — zero OpenAI import sites remain
- One-liner:
- Removed all 10 stale OpenAI/GPT references from user-facing docs, in-code comments, docstrings, and planning artifacts — README, DEPLOYMENT, CHATBOT, pipeline.py, README_LANGGRAPH, decomposer.py, and 09-VERIFICATION.md now accurately reflect the Claude + HuggingFace stack

---

## v1.1 Supabase Migration (Shipped: 2026-04-07)

**Phases completed:** 3 phases, 6 plans, 6 tasks

**Key accomplishments:**

- Supabase env vars (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) replace Cognito constants in core/config.py with startup ValueError guard
- JWKS fetch URL in core/auth.py changed from AWS Cognito to Supabase Auth endpoint; Cognito references fully removed
- httpx DELETE to Supabase Admin API replaces boto3 AdminDeleteUser in account deletion; GET /account/me cleaned of Cognito username field
- boto3 removed from requirements.txt and api/account.py; .env.example and README.md Environment Variables section added for operator onboarding

---

## v1.0 Fiqh Agentic RAG MVP (Shipped: 2026-03-25)

**Phases completed:** 4 phases, 12 plans, 17 tasks

**Key accomplishments:**

- pymupdf and pinecone-text pinned in requirements.txt, fiqh Pinecone index env vars exported from core/config.py, and data/ directory scaffolded with BM25 encoder gitignored
- PyMuPDF-based PDF parsing with ruling-boundary chunking producing 3000 structured chunks from 2796 Sistani rulings, with chapter/section/topic metadata on every chunk
- Full Pinecone fiqh ingestion pipeline: BM25Encoder fitted on 3000 chunks + dense embedding via all-mpnet-base-v2 + dual upsert to deen-fiqh-dense and deen-fiqh-sparse indexes with idempotent index creation
- 6-category fiqh classifier (classify_fiqh_query, gpt-4o-mini) added to modules/fiqh/classifier.py; fiqh_category field added to ChatState for downstream routing
- Query decomposer (decompose_query) with JSON fence stripping and safe fallback to original query; unit tests for classifier and decomposer (mocked LLM)
- Hybrid fiqh retriever using BM25 sparse + dense Pinecone raw index queries merged with Reciprocal Rank Fusion (k=60), returning up to 20 deduplicated docs per query via decomposed sub-queries.
- LLM-based evidence filter (gpt-4.1) and Structured Evidence Assessment (gpt-4o-mini with Pydantic structured output) for the FAIR-RAG pipeline — 23 mock-based unit tests, all pass
- Query refiner (gpt-4.1) targeting SEA gaps + confirmed facts, and answer generator (gpt-4.1) with inline [n] citations, ## Sources section, mandatory fatwa disclaimer, and insufficient-evidence warning — 23 mock-based unit tests, all pass
- Pure Python FAIR-RAG coordinator wiring all Phase 3 modules (filter, SEA, refiner, generator) with Phase 2 retriever into a max-3-iteration retrieve-filter-assess-refine loop — 9 mock-based unit tests, all pass
- FiqhState TypedDict (7 fields), ChatState fiqh result fields, and format_fiqh_references_as_json() — state contracts enabling Plans 02 and 03 to import concrete types without circular uncertainty

---
