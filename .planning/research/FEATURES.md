# Feature Landscape

**Domain:** Fiqh Agentic RAG — Twelver Shia Islamic legal Q&A grounded in Ayatollah Sistani's published rulings
**Researched:** 2026-03-23
**Sources:** FAIR-RAG paper, FARSIQA paper (Islamic domain evaluation), existing Deen backend codebase

---

## Table Stakes

Features users expect. Missing = product feels incomplete or untrustworthy. In a religious legal domain, "incomplete" means dangerous.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Query validation & scope routing** | Users will ask off-topic questions. Without gating, the system generates confidently wrong Islamic rulings. | Medium | Router must classify: VALID_OBVIOUS / VALID_SMALL / VALID_LARGE / OUT_OF_SCOPE / UNETHICAL. Existing fiqh classifier in `check_early_exit` node is present but performs poorly — must be replaced with explicit category routing. |
| **Negative rejection** | FARSIQA achieved 97% rejection accuracy vs 57% for naive RAG. The most critical metric for religious content — wrong answer is always worse than no answer. | Medium | Two-layer defense: (1) router rejects out-of-scope at the front, (2) generation prompt refuses when evidence is insufficient. Both are required. |
| **Fatwa disclaimer on every ruling** | Any system answering fiqh questions without an explicit "I am not issuing a fatwa" disclaimer will be considered unacceptable by Shia Muslims. | Low | Non-negotiable. Must be hardcoded in the generation prompt, not optional. Applies to ALL ruling responses, not just edge cases. |
| **Hybrid retrieval (dense + sparse + RRF)** | Fiqh texts use fixed Arabic/Persian terminology (najasah, wudu, tayammum). BM25 exact matching is required for these terms — dense-only retrieval will miss them. | Medium | Existing Pinecone dense + sparse infrastructure exists for hadith/Quran. A dedicated fiqh index using the same pattern is the path forward. |
| **Inline citations linking to source passages** | Without citations, users cannot verify answers. In a legal context this is a trust-breaker. | Medium | Every factual claim needs a `[n]` token in the generated text plus a references block at the end of the response. Source metadata (book, chapter, ruling number) must be stored per Pinecone chunk. |
| **Insufficient evidence partial answer + redirect** | When evidence is incomplete after 3 iterations, the system must not silently hallucinate. It must say what it found and where to get the rest. | Low | Standard generation fallback: "Here is what I found: [partial]. For a complete ruling, consult Sistani's official office." |
| **SSE status streaming for pipeline stages** | The FAIR-RAG loop takes 3 iterations and ~22 seconds. Without intermediate status events, the UI appears frozen. | Low | Existing SSE protocol in `pipeline_langgraph.py` already emits `status` events. Extend to emit fiqh-specific stages: decomposing, retrieving, assessing, refining. |
| **Fiqh corpus ingestion pipeline** | The system cannot answer anything without the data. PDF parsing, chunking, embedding, and Pinecone upload of Sistani's "Islamic Laws" is a prerequisite to all other features. | Medium-High | Chunking strategy from FARSIQA: ~300-400 tokens, paragraph-boundary-first, with chapter/section/topic metadata. Q&A chunks should prepend the question to the answer for retrieval matching. |

---

## Differentiators

Features that set this product apart. Not universally expected, but meaningfully raise quality and trust.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Structured Evidence Assessment (SEA)** | The core innovation. Unlike abstractive summarization or direct QA, SEA explicitly enumerates required findings, checks each against evidence, and names gaps. This is what enables 97% negative rejection. Without it, the system either hallucinates or silently fails. | High | Three-step process: (1) mission deconstruction into required-findings checklist, (2) per-finding evidence synthesis with confirmed vs gaps, (3) sufficiency verdict. SEA is what turns the loop into a self-auditing process rather than blind retrieval. |
| **Query decomposition into independent sub-queries** | Complex fiqh questions frequently require multi-hop retrieval: find the base principle, then find the exception. Decomposition targets both in the first pass. FAIR-RAG component scored 4.13/5.0 in quality evaluation. | Medium | Generate 1-4 keyword-rich, semantically independent sub-queries. Use fiqh terminology in sub-queries explicitly (tahara, wudu, etc.). Only generate as many as truly needed — artificial inflation hurts precision. |
| **Iterative query refinement using confirmed facts** | Once SEA confirms partial facts, refinement generates laser-targeted queries using those confirmed facts rather than re-stating the original question. Query Refinement was the highest-scoring component in FARSIQA: 4.45-4.61/5.0 with zero failures. | Medium | Key principle: "Once confirmed the base ruling is X, the next query should use X directly, not re-derive it." Max 3 iterations, early exit when SEA declares sufficiency. |
| **Dynamic LLM allocation (small for routing/SEA, large for filtering/refinement/generation)** | 13% cheaper than static large model while achieving better negative rejection (97% vs 94%). Static reasoner model is 11.8x more expensive with worse faithfulness — do not use. | Medium | gpt-4o-mini for routing, decomposition, SEA. gpt-4.1 for evidence filtering, query refinement, answer generation. This allocation is validated by FARSIQA Table 6. |
| **Fiqh-specific ethical safeguards hardcoded in generation prompt** | Sensitive ruling categories (khums, inheritance, divorce, personal situation fatwas) need extra disclaimers beyond the standard fatwa disclaimer. This proactive layering is what separates a responsible Islamic platform from a generic chatbot. | Low | Extra disclaimer triggers for: personalized situation questions ("Should I specifically..."), khums calculations, inheritance shares, divorce questions. Always redirect these to Sistani's official office. |
| **Topic-tagged metadata per chunk enabling sectional filtering** | Sistani's book covers tahara, salah, sawm, hajj, khums, transactions, family law. Metadata tags allow future scoped retrieval ("only retrieve from tahara section for purity questions"). | Medium | Requires tagging during ingestion. Not used in initial retrieval but enables future query-type-aware scope filtering and improves citation quality (showing chapter context). |
| **Controversial/disputed ruling neutrality** | When retrieved evidence contains multiple scholarly positions or a ruling is contested, presenting views neutrally without endorsement is essential for religious credibility. | Low | Built into the generation prompt. When evidence contains "opinion A vs opinion B" patterns, output both without editorial stance. |

---

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Reasoning model routing (o1/o3 for complex inheritance)** | Static Reasoner in FARSIQA was 11.8x more expensive with worse faithfulness (57.7%) than Dynamic allocation (62.5%). The complexity tradeoff is bad, and the PROJECT.md explicitly defers this. | Use gpt-4.1 large for VALID_LARGE and VALID_REASONER queries in this milestone. Revisit after measuring real-world failure rates on complex queries. |
| **Multi-marji support (Khamenei, Fadlallah, etc.)** | Each marja has a different corpus, different terminology, and different rulings. Multi-marja conflation is a major religious sensitivity risk — users asking about Sistani must get Sistani only. | Hard-scope the retrieval to the Sistani index. Route any comparative-marja questions as out-of-scope or note "this system is limited to Sistani's rulings." |
| **Sistani.org Q&A scraping** | Web scraping introduces legal and maintenance risk. The book corpus is bounded, quality-controlled, and sufficient for MVP. Scraping should come after the book pipeline is validated. | Start with "Islamic Laws" 4th edition only. After the pipeline is proven, add official Q&A data as a second corpus phase. |
| **Arabic/Persian query answering** | Multilingual support doubles the embedding model complexity and requires separate evaluation for retrieval quality in each language. | English-first. The translation tool already in the pipeline handles non-English input at the query level. Fiqh content and retrieval remain English. |
| **LLM-as-Judge evaluation harness** | A systematic evaluation harness is valuable but should not block building the pipeline. Building it in this milestone conflates infrastructure and product. | Identify evaluation queries manually. Run spot-checks after each phase. Build a proper eval harness as a separate future milestone after the pipeline is stable. |
| **Fine-tuning or model training** | Out of scope per PROJECT.md. The FAIR-RAG architecture achieves state-of-the-art results without training. | Agentic pipeline engineering only. |
| **Frontend or UI changes** | This is a backend milestone. Frontend changes need product coordination. | Expose fiqh capability via the existing `/chat/stream/agentic` SSE endpoint. Frontend consumes the existing protocol. |

---

## Feature Dependencies

```
Fiqh corpus ingestion
    └── Pinecone fiqh index (dense + sparse)
            └── Hybrid retrieval (RRF)
                    └── Evidence filtering
                            └── SEA (Structured Evidence Assessment)
                                    ├── Iterative query refinement (when gaps found)
                                    │       └── Hybrid retrieval (loop back, max 3x)
                                    └── Faithful answer generation (when sufficient)
                                            ├── Inline citations
                                            ├── Fatwa disclaimer
                                            └── Insufficient evidence partial answer

Query validation & routing (must precede all above)
    ├── Negative rejection (out-of-scope path)
    └── VALID_OBVIOUS shortcut (bypass RAG entirely)

Query decomposition (parallel to routing, feeds retrieval)

Dynamic LLM allocation (cross-cutting, applies per pipeline stage)

SSE status streaming (cross-cutting, wraps all stages)
```

**Critical path:** Corpus ingestion → Pinecone index → Hybrid retrieval → SEA → Generation. Every other feature depends on this sequence being complete.

**Non-blocking in parallel:**
- Query validation improvements can be built independently of corpus ingestion
- SSE status events can be scaffolded before the RAG loop is wired
- Dynamic LLM allocation is a configuration concern, not a blocker

---

## MVP Recommendation

**Build in this order:**

1. **Corpus ingestion pipeline** — No other feature is testable without this. PDF parsing, chunking with metadata, embedding, Pinecone upload. Non-blocking for routing work but the critical path dependency.

2. **Improved query classifier + negative rejection** — Replace the underperforming fiqh early-exit with the 6-category router (VALID_OBVIOUS / VALID_SMALL / VALID_LARGE / OUT_OF_SCOPE / UNETHICAL). Wire negative rejection as the first defense layer.

3. **FAIR-RAG iterative loop as LangGraph sub-graph** — The core milestone deliverable. Decompose → Retrieve (hybrid RRF) → Filter → SEA → Refine → Repeat (max 3x) → Generate. This is a single sub-graph that the main agent routes to when the query is classified as fiqh.

4. **Faithful generation with citations + disclaimer** — Strictly evidence-grounded generation, inline `[n]` citations, fatwa disclaimer hardcoded, insufficient-evidence fallback.

5. **SSE streaming of intermediate pipeline stages** — Extend existing status events to cover the fiqh sub-graph stages. Required before the feature is usable in the existing frontend.

**Defer:**
- Topic-tagged metadata filtering: ingestion can tag metadata, but retrieval-time scoping can be added post-launch once query patterns are understood
- Khums/inheritance/divorce extra disclaimers: implement the core safeguards first, add category-specific extra warnings in the second iteration
- Evaluation harness: manual spot-checks in this milestone, systematic eval in a future milestone

---

## Confidence Assessment

| Feature Area | Confidence | Notes |
|--------------|------------|-------|
| Table stakes identification | HIGH | Directly from FAIR-RAG and FARSIQA papers, crosschecked with PROJECT.md requirements |
| Differentiator ordering | HIGH | FARSIQA component-level scores (4.13, 4.61/5.0) provide empirical ranking |
| Anti-feature justifications | HIGH | Cost/quality data from FARSIQA Table 6 supports dynamic-vs-reasoner decision; project constraints documented in PROJECT.md |
| Feature dependencies | HIGH | Logical pipeline dependencies verified against existing LangGraph architecture |
| Complexity estimates | MEDIUM | Based on integration with existing stack; actual complexity depends on Pinecone fiqh index configuration |

---

## Sources

- FAIR-RAG paper (via `documentation/fiqh_related_docs/FAIR-RAG.pdf`)
- FARSIQA paper (via `documentation/fiqh_related_docs/FARSIQA.pdf`)
- FAIR-RAG implementation guide: `/Users/shawn.n/Desktop/Deen/deen-backend/documentation/fiqh_related_docs/FAIR_RAG_Fiqh_Implementation_Guide.md`
- Project requirements: `/Users/shawn.n/Desktop/Deen/deen-backend/.planning/PROJECT.md`
- Existing agent architecture: `agents/core/chat_agent.py`, `core/pipeline_langgraph.py`
