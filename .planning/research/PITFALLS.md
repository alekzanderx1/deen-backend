# Domain Pitfalls: Fiqh Agentic RAG (FAIR-RAG / FARSIQA)

**Domain:** Agentic RAG for Islamic legal (fiqh) Q&A — Ayatollah Sistani's "Islamic Laws"
**Researched:** 2026-03-23
**Primary sources:** FAIR_RAG_Fiqh_Implementation_Guide.md (internal), FAIR-RAG paper analysis, FARSIQA paper analysis (122 error samples from Islamic domain)

---

## Failure Mode Baseline

Before listing pitfalls, anchor to the empirical failure distributions from the papers.
These numbers tell you where to spend engineering effort.

**FAIR-RAG (200 error samples, multi-hop QA):**
| Category | % of Errors |
|---|---|
| Retrieval Failure | 32.5% |
| Generation Failure | 31.0% |
| SEA Error | 24.5% |
| Query Decomposition | 9.0% |
| Evidence Filtering | 1.5% |
| Query Refinement | 1.5% |

**FARSIQA (122 error samples, Islamic domain — more relevant):**
| Category | % of Errors |
|---|---|
| Generation Failure | 54.9% |
| Retrieval Failure | 27.9% |
| Query Decomposition | 9.0% |
| Evidence Filtering | 5.7% |
| SEA Error | 2.5% |
| Query Refinement | 0% |

**Implication:** In the Islamic domain specifically, generation failures dominate — the LLM synthesizes incorrectly even when correct evidence is present. Generation prompt engineering is the highest-leverage work.

---

## Critical Pitfalls

Mistakes that cause product-level failures, safety regressions, or pipeline rewrites.

### Pitfall 1: LLM Synthesizes a Ruling From Parametric Memory Instead of Retrieved Evidence

**What goes wrong:** The generation step produces a confident Islamic ruling that comes from the LLM's training data, not the retrieved Sistani passages. The citation format makes it look grounded when it is not.

**Why it happens:** LLMs trained on large corpora contain Islamic jurisprudence knowledge. Without explicit, hard-enforced grounding constraints in the generation prompt, the model interpolates between retrieved docs and its own priors — especially on common topics (prayer, fasting) where its parametric knowledge is strong.

**Consequences:** A user receives a fatwa-like statement attributed to Sistani that does not actually appear in his published rulings. This is the highest-severity failure for this product. The FARSIQA paper labels this as 54.9% of all errors in the Islamic domain.

**Prevention:**
- Generation prompt must include an explicit hard constraint: "Every factual claim MUST appear verbatim or by direct paraphrase in a cited retrieved document. If you cannot cite it, do not say it."
- Use temperature=0 for generation — eliminates sampling variance that allows creative synthesis.
- Add a post-generation faithfulness check: pass generated answer + evidence back to the LLM and ask "Does every factual claim in this answer appear in the provided evidence? Reply YES or NO."
- Never use `VALID_OBVIOUS` routing to bypass RAG on rulings, only on indisputable general facts (e.g., "how many prayers per day").

**Warning signs:**
- Generated answers contain specific ruling details not present in the top-k retrieved chunks.
- Answers for obscure fiqh questions are fluent and confident — obscure questions should produce partial answers or refusals, not complete rulings.
- Citations reference real document IDs but the cited passage does not support the claim.

**Phase mapping:** Phase: Data Ingestion + Phase: Generation (address via prompt design before first end-to-end test).

---

### Pitfall 2: SEA Declares Sufficiency Too Early — Premature Loop Exit

**What goes wrong:** The Structured Evidence Assessment module returns `Sufficient: Yes` after the first retrieval pass even though the evidence only partially answers the question. The loop exits and generation proceeds on incomplete evidence.

**Why it happens:** Two failure subtypes from the paper:
1. The SEA prompt is ambiguous about what "confirmed" means — the model treats weak or tangential evidence as confirmation.
2. The SEA checklist misses a required finding because the mission deconstruction was too coarse.

**Consequences:** Multi-hop fiqh questions (base ruling + exception + conditions) get answered from only the base ruling chunk. The exception or condition is fabricated in generation. This compounds with Pitfall 1.

**Prevention:**
- SEA prompt must explicitly state: "Only declare 'Yes' if ALL required findings are confirmed. If any finding is only partially addressed, the verdict is 'No'."
- Do NOT allow "logical inference" to bridge gaps for legal rulings. The paper permits logical inference for general facts (nationality from birthplace), but for fiqh rulings inference is a hallucination risk. Only explicit textual support should count as confirmed.
- Require SEA to list confirmed findings with the exact evidence sentence that supports each one. This forces the model to identify genuine confirmation rather than reasoning from priors.

**Warning signs:**
- Multi-hop fiqh questions resolve in exactly 1 iteration consistently.
- SEA "Confirmed Findings" section is verbose and narrative (paraphrasing) rather than quoting evidence.
- Answer quality on exception/condition queries is lower than on base ruling queries.

**Phase mapping:** Phase: SEA Module Implementation. Write targeted tests with questions that require 2-3 iterations — assert loop does not exit at iteration 1 for these.

---

### Pitfall 3: PDF Parsing Breaks Ruling Continuity — Cross-Page Fragments

**What goes wrong:** Sistani's "Islamic Laws" (4th edition, ~112 pages) uses numbered rulings with sub-clauses that span pages. Standard PDF extractors split at page boundaries, producing chunks like "...continued from previous page" or cutting in the middle of a conditional clause ("If X then..."). The second fragment loses its antecedent entirely.

**Why it happens:** PDF text extraction (PyMuPDF, pdfplumber) is line/page-aware, not semantically aware. Ruling #712 may start on page 89 and conclude on page 90. If chunked at page boundaries, both halves become orphaned.

**Consequences:** Retrieved chunks contain incomplete rulings. A chunk like "...in this case the prayer is invalid" with no context about what condition triggers invalidity is worse than having no chunk — the generator may invent the missing condition.

**Prevention:**
- Extract full PDF text as a continuous string first, THEN chunk by semantic boundaries (paragraph markers, ruling numbers, whitespace patterns).
- Preserve ruling numbers in metadata. Sistani's book uses numbered rulings (e.g., "Issue 712:"). Use these as anchor points for chunking — each ruling should be a minimum chunk unit.
- After extraction, run a validation pass: flag any chunk that starts mid-sentence (first word is lowercase, no subject) or ends without punctuation. These indicate splits mid-ruling.
- Target chunk size 300-400 tokens (FARSIQA recommendation) but never break a ruling number boundary to hit the token target — allow chunks up to 500 tokens if needed to keep a ruling intact.

**Warning signs:**
- Chunks contain phrases like "however," "in this case," "as mentioned above" without antecedent context.
- Retrieval for specific ruling numbers returns different fragments of the same ruling as separate documents.
- During ingestion quality audit, chunks that begin with lowercase words.

**Phase mapping:** Phase: Data Ingestion (PDF Parsing). This must be solved before any embeddings are generated — re-chunking requires re-embedding the entire corpus.

---

### Pitfall 4: Dense Retrieval Alone Misses Arabic/Persian Fiqh Terminology

**What goes wrong:** Users ask about "tahara", "wudu", "najasah", "ghusl", "tayammum", "khums", "ijtihad". The Sistani PDF uses these exact Arabic terms transliterated into English. Dense (semantic) embeddings trained on general corpora represent these terms poorly — they are out-of-distribution vocabulary.

**Why it happens:** Embedding models like `text-embedding-3-large` have seen Arabic terms in Arabic script but not necessarily in their Roman transliteration ("wudu" vs "وضو"). Semantic search fails because the embedding space doesn't cluster these terms correctly.

**Consequences:** A user asks "what is the ruling on ghusl after janabah" — dense retrieval returns passages about general purification or prayer but misses the specific ghusl ruling. BM25 would find it by exact keyword match but dense retrieval alone does not.

**Prevention:**
- Implement hybrid retrieval (dense + sparse/BM25) from day one — do not prototype with dense-only and add sparse later. The FARSIQA paper used Elasticsearch with simultaneous BM25 + vector search. Pinecone's sparse index (already used in the existing stack for hadith) supports this.
- Use RRF (Reciprocal Rank Fusion, k=60) to merge rankings. This requires no hyperparameter tuning.
- In the query decomposition prompt, explicitly instruct the LLM to include Arabic/Persian fiqh terms in sub-queries where appropriate (see FAIR_RAG_Fiqh_Implementation_Guide.md Section 15.2).

**Warning signs:**
- Retrieval for transliterated Arabic terms returns 0 or low-score results while the PDF clearly contains those passages.
- BM25-only retrieval outperforms dense retrieval for keyword-heavy fiqh queries.

**Phase mapping:** Phase: Retrieval Infrastructure. Sparse index and RRF must be in place before evaluation — not an optimization to add later.

---

### Pitfall 5: Over-Aggressive Evidence Filtering Discards Relevant Chunks

**What goes wrong:** The evidence filtering step removes chunks that seem tangential but contain the specific exception or condition needed to answer a multi-hop question. The remaining evidence looks clean but is incomplete. SEA then cannot find the required finding.

**Why it happens:** The filtering model judges a chunk irrelevant because it discusses a general principle rather than the specific question — but that general principle is exactly the missing piece for the chain of reasoning.

**Consequences:** The loop iterates 3 times without finding the missing evidence (because it was already discarded in iteration 1). The system exhausts iterations and falls back to a partial answer — when the information was actually retrieved but thrown away.

**Prevention:**
- Internalize and enforce the paper's core rule: "BE INCLUSIVE. When in doubt, KEEP the document." The filter should only remove chunks about completely different topics or different scholars with no relevance to Sistani.
- Filtering is anchored to the ORIGINAL USER QUERY, not the sub-query. This is explicitly stated in the paper. Filtering by sub-query creates over-pruning.
- F1 of 55-76% is the expected range for this component. Do not tune the filter to achieve high precision at the cost of recall — the SEA module downstream handles further verification.

**Warning signs:**
- Evidence Filtering F1 (measuring against human judgment of relevance) exceeds 85% — this likely indicates over-pruning.
- Questions involving exceptions or conditions fail more often than base ruling questions.
- Increasing the number of retrieved docs doesn't improve answer quality (they're all getting filtered).

**Phase mapping:** Phase: Evidence Filtering. Tune toward recall, not precision.

---

### Pitfall 6: Fiqh Classifier Boundary Errors — Wrong Routing of Edge-Case Queries

**What goes wrong:** The existing fiqh classifier (noted in PROJECT.md as "doesn't perform well") routes edge-case queries incorrectly. Two failure modes: (1) fiqh questions about adjacent topics get routed as non-fiqh and miss the FAIR-RAG pipeline entirely, (2) general Islamic history questions get misrouted into the expensive fiqh pipeline.

**Why it happens:** The current binary classifier (`classify_fiqh_query` in `modules/classification/classifier.py`) returns a simple true/false. It has no granularity for the `VALID_OBVIOUS` / `VALID_SMALL` / `VALID_LARGE` / `VALID_REASONER` / `OUT_OF_SCOPE_FIQH` taxonomy that FAIR-RAG requires.

**Consequences:**
- Under-classification: A user asking "What does Sistani say about business contracts?" gets treated as a general Islamic question, receives a hadith-grounded answer, no fiqh evidence.
- Over-classification: A user asking "What is the history of Islamic jurisprudence?" enters the fiqh pipeline, wastes 3 iterations, likely exits with insufficient evidence.

**Prevention:**
- Replace the binary classifier with a multi-class classifier using the 6-category taxonomy from the FAIR-RAG routing prompt (Section 15.1 of the implementation guide).
- Apply the FARSIQA anchoring rule: "If the question is anchored to a specific Islamic personality, book, concept, historical event, or place, it MUST be considered IN SCOPE." For this product, the anchor is Ayatollah Sistani.
- Build a classifier evaluation set of 50+ labeled examples before deploying the new classifier. Include edge cases: comparative questions ("Does Sistani agree with X scholar?"), adjacent topics ("Sistani's view on modern medicine"), historical context questions.

**Warning signs:**
- User feedback that fiqh questions get generic Hadith/Quran answers.
- High rate of `OUT_OF_SCOPE` classifications on questions containing "Sistani" or fiqh terms.
- The pipeline reaches `VALID_OBVIOUS` and bypasses RAG for nuanced ruling questions.

**Phase mapping:** Phase: Query Classification (must be addressed before FAIR-RAG pipeline is wired in).

---

## Moderate Pitfalls

### Pitfall 7: Query Decomposition Generates Redundant Sub-Queries

**What goes wrong:** The decomposition step generates 4 sub-queries where 2 are semantically identical with minor rephrasing. The retrieval pass then fetches largely overlapping documents, wasting token budget and not actually expanding coverage.

**Prevention:**
- Decomposition prompt must instruct: "Each sub-query must cover a DISTINCT facet. Check for redundancy before outputting — if two queries would retrieve the same passages, merge them or replace one."
- Validate during development: compute cosine similarity between sub-query embeddings. If two sub-queries have similarity > 0.92, flag as likely redundant.
- From the paper: generate only as many as truly necessary (1-4), never inflate. A simple fiqh lookup needs 1-2 sub-queries.

**Phase mapping:** Phase: Query Decomposition. Validate with similarity check during testing.

---

### Pitfall 8: Query Refinement Repeats Previous Queries

**What goes wrong:** In iteration 2 or 3, the refinement step generates queries that are semantically equivalent to queries already tried. The retrieval pass fetches the same documents, SEA reaches the same gaps, and the loop spins uselessly until `max_iter` is hit.

**Prevention:**
- The refinement prompt must receive the full history of previous sub-queries and be explicitly instructed: "NEVER repeat or closely rephrase a query that has already been tried."
- Track all previous queries in loop state. Before executing retrieval, check cosine similarity of new queries against previous ones — abort if > 0.90 similarity.
- Note from the paper: Query Refinement had 0% errors in FARSIQA and 1.5% in FAIR-RAG. This is the most robust component. The "use confirmed facts to narrow queries" principle is effective when followed.

**Phase mapping:** Phase: Iterative Loop State Management.

---

### Pitfall 9: LangGraph Sub-Graph State Leak Between Fiqh Sessions

**What goes wrong:** The FAIR-RAG iterative loop is implemented as a LangGraph sub-graph called from the main `ChatAgent` graph. If the sub-graph state (accumulated evidence, iteration counter, gap list) is not properly scoped per-request, residual state from one user's query bleeds into another user's query.

**Why it happens:** The existing `ChatAgent` uses `MemorySaver` as a checkpointer. If the fiqh sub-graph shares the same thread ID or global state, the iteration counter and evidence accumulator from a previous invocation persist.

**Consequences:** A user's query starts on "iteration 2" with evidence from someone else's query. SEA incorrectly declares sufficiency because it finds the previous user's evidence. Answers are cross-contaminated.

**Prevention:**
- The FAIR-RAG sub-graph must use a separate, isolated state schema (`FiqhPipelineState`) that is freshly instantiated per request — not shared with `ChatState`.
- Pass the sub-graph as a compiled runnable invoked with fresh input each call, not as a node in the same graph with shared checkpointing.
- Write an integration test that runs two simultaneous fiqh queries with different topics and asserts no evidence cross-contamination.

**Phase mapping:** Phase: LangGraph Integration.

---

### Pitfall 10: Missing Fatwa Disclaimer on Partial Answers

**What goes wrong:** The fatwa disclaimer is included on complete ruling responses but omitted when the system gives a partial answer (exhausted iterations, insufficient evidence). Users interpret partial answers as authoritative because no disclaimer is present.

**Prevention:**
- Disclaimer must be added unconditionally on ALL responses where a fiqh ruling is discussed — complete, partial, or uncertain.
- Implement disclaimer injection as a post-processing step in the pipeline, not only inside the generation prompt. This makes it harder to accidentally omit.
- For sensitive ruling categories (khums, inheritance, divorce, marriage), add an extra disclaimer per FARSIQA's recommendation: "For matters involving [category], please consult Ayatollah Sistani's official office directly."

**Phase mapping:** Phase: Generation / Response Formatting.

---

### Pitfall 11: SSE Status Events Block the Iterative Loop

**What goes wrong:** Each FAIR-RAG phase (decomposing, retrieving, assessing, refining) needs to emit SSE status events to the frontend. If these events are not non-blocking, the pipeline stalls waiting for flush confirmation, adding latency that compounds across 3 iterations.

**Prevention:**
- Status events should be fire-and-forget (enqueue to SSE stream, do not await confirmation).
- Keep status event payloads small (< 100 bytes): `{"status": "retrieving", "iteration": 2}` not full evidence dumps.
- Do not stream intermediate evidence or SEA output to the client — only status labels. Full evidence dumps over SSE add latency and expose internal pipeline state.

**Phase mapping:** Phase: SSE Integration.

---

## Minor Pitfalls

### Pitfall 12: Chunk Metadata Missing Chapter/Section Tags

**What goes wrong:** Chunks are ingested with only source book and text. During retrieval, citations display as "Islamic Laws (Sistani)" with no chapter reference. Users cannot verify the ruling in the physical book.

**Prevention:**
- During PDF parsing, extract chapter and section headers (typically uppercase or bold in the PDF). Store these as metadata fields per chunk: `chapter`, `section`, `ruling_number`.
- Citations should render as: "Islamic Laws, Chapter: Tahara, Section: Wudu, Issue #712" not just "Islamic Laws."

**Phase mapping:** Phase: Data Ingestion.

---

### Pitfall 13: Top-k Retrieval Count Not Tuned for Fiqh Corpus Density

**What goes wrong:** The retrieval configuration from the existing hadith/Quran pipeline (designed for a large multi-source corpus) is reused unchanged for the fiqh index. The fiqh corpus is ~112 pages — small. Fetching top-10 per sub-query with 4 sub-queries produces 40 candidates, most of which overlap.

**Prevention:**
- Start with top-3 per retriever per sub-query (FARSIQA recommendation for small corpora), RRF to top-5 per sub-query.
- Measure retrieval recall before committing to a k value: for a sample of 30 queries where the correct chunk is known, what k is needed for 90% recall?
- The fiqh index should have its own retrieval configuration separate from the hadith/Quran configuration.

**Phase mapping:** Phase: Retrieval Infrastructure.

---

### Pitfall 14: Negative Rejection Tested Only at End-to-End Level

**What goes wrong:** Negative rejection (refusing to answer out-of-scope questions) is only tested as a final output check. Failures in the rejection path — where the classifier lets an out-of-scope query through and the pipeline exhausts iterations before giving up — waste significant latency and cost.

**Prevention:**
- Test negative rejection at the classifier level (unit) and at the generation level (integration) separately.
- The two rejection layers are: (1) routing classifier must catch obvious out-of-scope queries before the pipeline runs, (2) generation prompt must refuse when SEA never reaches sufficiency.
- Target: >95% negative rejection accuracy (FARSIQA achieved 97%). Measure separately for each rejection layer.

**Phase mapping:** Phase: Evaluation.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| PDF Parsing & Chunking | Cross-page ruling fragments (Pitfall 3) | Extract as continuous text, anchor chunks to ruling numbers |
| Fiqh Index Ingestion | Missing Arabic term exact-match support (Pitfall 4) | Build sparse index alongside dense from the start |
| Query Classifier Replacement | Binary classifier missing granularity (Pitfall 6) | 6-category taxonomy, evaluation set of 50+ labeled queries |
| Query Decomposition | Redundant sub-queries (Pitfall 7) | Similarity check between sub-query embeddings |
| Hybrid Retrieval | Wrong k value for small corpus (Pitfall 13) | Recall measurement before committing to k |
| Evidence Filtering | Over-pruning tangential but needed chunks (Pitfall 5) | Anchor to original query, default to inclusive |
| SEA Implementation | Premature sufficiency declaration (Pitfall 2) | Require explicit textual citation per confirmed finding |
| Iterative Loop State | State leak between sessions (Pitfall 9) | Isolated FiqhPipelineState per request |
| Generation Prompt | Parametric knowledge synthesis (Pitfall 1) | Hard grounding constraint + faithfulness post-check |
| Response Formatting | Missing disclaimer on partial answers (Pitfall 10) | Post-processing disclaimer injection, not prompt-only |
| SSE Streaming | Blocking status events add latency (Pitfall 11) | Fire-and-forget status events, minimal payloads |
| Evaluation | Negative rejection only tested end-to-end (Pitfall 14) | Unit test classifier + integration test generation separately |

---

## Sources

- Internal: `documentation/fiqh_related_docs/FAIR_RAG_Fiqh_Implementation_Guide.md` — Section 13 (Failure Mode Taxonomy), Section 6 (Evidence Filtering), Section 7 (SEA), Section 9 (Generation Constraints), Section 11 (Fiqh-Specific Adaptations) — HIGH confidence
- Internal: `.planning/PROJECT.md` — existing classifier known weakness noted — HIGH confidence
- Internal: `agents/core/chat_agent.py`, `modules/classification/classifier.py` — codebase inspection for integration pitfalls — HIGH confidence
- FAIR-RAG paper (via implementation guide): 200-sample error distribution — MEDIUM confidence (summarized, not direct paper access)
- FARSIQA paper (via implementation guide): 122-sample Islamic domain error distribution — MEDIUM confidence (summarized, not direct paper access)
