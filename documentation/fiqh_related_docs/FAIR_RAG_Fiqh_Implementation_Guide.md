# FAIR-RAG & FARSIQA: Implementation Guide for Fiqh Q&A
> Analysis of the two papers for building a faithful, agentic RAG system for Ayatollah Sistani's Fiqh rulings.
> Scope: **No model training.** Focus is on the **agentic pipeline architecture only.**

---

## Table of Contents
1. [Core Concept: Why Standard RAG Fails for Fiqh](#1-core-concept-why-standard-rag-fails-for-fiqh)
2. [The FAIR-RAG Pipeline: Full Architecture Overview](#2-the-fair-rag-pipeline-full-architecture-overview)
3. [Phase 1: Query Validation & Adaptive Routing](#3-phase-1-query-validation--adaptive-routing)
4. [Phase 2: Query Decomposition](#4-phase-2-query-decomposition)
5. [Phase 3: Hybrid Retrieval & Reranking](#5-phase-3-hybrid-retrieval--reranking)
6. [Phase 4: Evidence Filtering](#6-phase-4-evidence-filtering)
7. [Phase 5: Structured Evidence Assessment (SEA) — The Core Innovation](#7-phase-5-structured-evidence-assessment-sea--the-core-innovation)
8. [Phase 6: Iterative Query Refinement](#8-phase-6-iterative-query-refinement)
9. [Phase 7: Faithful Answer Generation](#9-phase-7-faithful-answer-generation)
10. [Dynamic LLM Allocation Strategy](#10-dynamic-llm-allocation-strategy)
11. [Fiqh-Specific Adaptations from FARSIQA](#11-fiqh-specific-adaptations-from-farsiqa)
12. [Iteration Count: How Many Loops?](#12-iteration-count-how-many-loops)
13. [Failure Mode Taxonomy](#13-failure-mode-taxonomy)
14. [Evaluation Metrics to Track](#14-evaluation-metrics-to-track)
15. [Complete Prompt Templates](#15-complete-prompt-templates)
16. [Implementation Checklist for Your FastAPI Backend](#16-implementation-checklist-for-your-fastapi-backend)

---

## 1. Core Concept: Why Standard RAG Fails for Fiqh

Standard "retrieve-then-read" RAG uses a single retrieval pass. This fails for Fiqh for several reasons that mirror the paper's findings:

| Problem | Why It Matters for Fiqh |
|---|---|
| **Single-pass retrieval misses multi-hop facts** | A Fiqh ruling often requires chaining: e.g., "ruling on X" → find the base principle → find the exception → synthesize. |
| **Hallucination risk** | LLMs generate confident but wrong rulings from parametric knowledge, which is catastrophic in a religious legal context. |
| **Query formulation failures** | Users rarely phrase Fiqh questions in retrieval-optimal language. |
| **No gap awareness** | Standard RAG doesn't know what it *doesn't* know — it generates anyway. |
| **Evidence noise** | Retrieved chunks often contain tangentially related rulings that can mislead the generator. |

The FAIR-RAG solution: **treat evidence gathering as an iterative, self-auditing process** that only generates an answer when evidence is verified as complete.

---

## 2. The FAIR-RAG Pipeline: Full Architecture Overview

The pipeline is a loop, not a linear chain. Here is the complete flow:

```
User Query
    │
    ▼
[Phase 1] Query Validation & Adaptive Routing
    │
    ├── OBVIOUS / OUT_OF_SCOPE / UNETHICAL → Direct response / Rejection
    │
    └── Valid complex query → Continue
                │
                ▼
        [Phase 2] Query Decomposition (up to 4 sub-queries)
                │
                ▼
        ┌──────────────────────────────────────────────┐
        │           ITERATIVE LOOP (max 3x)            │
        │                                              │
        │  [Phase 3] Hybrid Retrieval & Reranking      │
        │       (Dense + Sparse → RRF → top-k docs)    │
        │                │                             │
        │                ▼                             │
        │  [Phase 4] Evidence Filtering                │
        │       (Remove irrelevant docs)               │
        │                │                             │
        │                ▼                             │
        │  [Phase 5] Structured Evidence Assessment    │
        │       (SEA: checklist audit → gaps?)         │
        │                │                             │
        │     ┌──────────┴──────────┐                  │
        │   Yes: sufficient       No: gaps remain      │
        │     │                     │                  │
        │     │            [Phase 6] Query Refinement  │
        │     │            (Generate targeted queries) │
        │     │                     │                  │
        │     │              Loop back to Phase 3      │
        └─────┼─────────────────────────────────────── ┘
              │
              ▼
        [Phase 7] Faithful Answer Generation
              │
              ▼
        Final Answer (with citations)
```

**Key architectural principle:** The loop continues until the SEA module confirms sufficiency OR the maximum iteration count is reached. The system *never generates speculatively* — it either has verified evidence or it says so.

---

## 3. Phase 1: Query Validation & Adaptive Routing

### Purpose
Before doing anything expensive, classify the query to:
1. **Reject** out-of-scope or unethical questions immediately.
2. **Shortcut** trivially obvious questions (bypass RAG entirely).
3. **Pre-allocate** the right LLM size for the final generation step.

### Categories (adapted for Fiqh)

| Category | Description | Action |
|---|---|---|
| `VALID_OBVIOUS` | Common knowledge Islamic fact ("How many rak'ahs in Fajr?") | Answer directly from LLM parametric knowledge, skip RAG |
| `VALID_SMALL` | Simple factual Fiqh lookup ("Is X halal or haram?") | RAG with small LLM for generation |
| `VALID_LARGE` | Explanation/reasoning required ("Why is X makruh?") | RAG with large LLM |
| `VALID_REASONER` | Multi-hop deduction ("Calculate inheritance shares for...") | RAG with reasoning-capable LLM |
| `OUT_OF_SCOPE_FIQH` | Not a Sistani Fiqh question | Politely reject, redirect |
| `UNETHICAL` | Harmful or inappropriate request | Reject |

### Critical Rule for Fiqh Scope
From FARSIQA: **"If the question is anchored to a specific Islamic personality, book, concept, historical event, or place, it MUST be considered IN SCOPE."** For your use case, the anchor is Ayatollah Sistani's rulings specifically.

### Routing Prompt Template
See [Section 15.1](#151-query-validation-prompt) for the full prompt adapted for Fiqh.

---

## 4. Phase 2: Query Decomposition

### Purpose
Break a complex Fiqh question into up to **4 semantically independent sub-queries**, each targeting a different facet of the question. This maximizes retrieval recall.

### Key Principles
- Each sub-query should be **keyword-rich and independently searchable**.
- Sub-queries should be **semantically distinct** — no redundancy.
- **Generate only as many as truly necessary** (1–4). Don't artificially inflate.
- Sub-queries should cover **all conceptual facets** of the original.

### Fiqh Example

**Original Query:** "What is Sistani's ruling on praying in a place where the floor has najasah, if the worshipper does not touch it?"

**Decomposed Sub-queries:**
1. "Sistani ruling prayer najasah floor"
2. "Conditions for validity of prayer in impure location"
3. "Does the body touching najasah invalidate salah Sistani"
4. "Najasah on prayer location conditions exceptions"

### Why This Matters for Multi-Hop Fiqh
Many Fiqh rulings require first retrieving the **base principle**, then retrieving the **specific exception or condition**. Decomposition ensures both are targeted in the first retrieval pass.

### Ablation Result
The paper found Query Decomposition scored **4.13/5.0** in component-level quality evaluation. It is one of the most reliable components of the pipeline.

---

## 5. Phase 3: Hybrid Retrieval & Reranking

### Retrieval Strategy
Use **both** dense (semantic) and sparse (keyword/BM25) retrieval, then merge with Reciprocal Rank Fusion (RRF).

| Method | Strength | Weakness |
|---|---|---|
| Dense (embedding-based) | Semantic similarity, handles paraphrases | Misses exact term matches, out-of-distribution vocabulary |
| Sparse (BM25) | Exact keyword matches (names, terms, Arabic words) | No semantic understanding |
| **RRF (combined)** | Best of both | Requires both indexes |

### Why Both Matter for Fiqh
Fiqh texts use specific Arabic/Persian terminology (e.g., *najasah*, *wudu*, *tayammum*, *ijtihad*). BM25 is essential for exact term matching. Dense retrieval handles paraphrased user questions.

### RRF Algorithm
Reciprocal Rank Fusion score for document `d`:
```
RRF(d) = Σ 1 / (k + rank_i(d))
```
Where `k=60` is standard, and `rank_i(d)` is the document's rank in retrieval method `i`. This requires **no hyperparameter tuning** and is the recommended approach.

### Configuration from Papers
- **FAIR-RAG**: Top-5 documents per sub-query (dense-only in controlled experiments)
- **FARSIQA**: Top-3 from dense + Top-3 from sparse = up to 6 candidates per sub-query, then RRF → final top-3

**Recommendation for your implementation:** Start with top-3 per retriever, RRF to top-5 per sub-query. Adjust based on your corpus density.

### Indexing Backend
FARSIQA used **Elasticsearch 8.x** with a custom mapping supporting simultaneous BM25 and vector search. Each indexed document should include:
- Text chunk
- Dense vector embedding
- Source URL / document ID (for citations)
- Metadata (source book, chapter, topic if available)

---

## 6. Phase 4: Evidence Filtering

### Purpose
After retrieval, an LLM agent reviews all candidate documents and **discards irrelevant ones** before passing them to SEA. This reduces noise for the downstream reasoning step.

### Core Principle: Be Inclusive
> **"BE INCLUSIVE: When in doubt, KEEP the document."**

This is explicitly stated in both papers. The filter should only remove documents that are **completely irrelevant** — about a different entity or topic entirely. Partial relevance = keep.

### What to Remove
- Documents about **different** scholars or schools when Sistani-specific answer is requested
- Documents about **completely unrelated topics**
- Near-duplicate documents (keep the most informative one)

### What to Keep (Even If Imperfect)
- Documents about the correct topic, even without the specific ruling
- Documents with biographical/contextual information about related entities
- Documents with partial facts that contribute to the full answer

### Filtering is Done Per Batch
Documents are filtered in batches with a prompt that includes the original user query as the relevance anchor — NOT the sub-query. This keeps filtering **question-centric**.

### Performance Note
The paper found Evidence Filtering F1 ranges from **55–76%**, indicating it's imperfect. The "be inclusive" principle is important — the SEA module downstream handles further verification. **Don't over-filter.**

---

## 7. Phase 5: Structured Evidence Assessment (SEA) — The Core Innovation

### What SEA Is
SEA is the **analytical gating mechanism** of the entire loop. It determines whether the collected evidence is sufficient to answer the question, and if not, precisely identifies what is missing.

### Why SEA Over Alternatives?

| Alternative | Why It Fails |
|---|---|
| Abstractive summarization | "Hides" gaps by creating fluent narrative — you don't know what's missing |
| Direct QA | Binary pass/fail — doesn't tell you *what* is missing |
| **SEA (checklist)** | Explicitly enumerates required findings, checks each one, names the gaps |

### SEA's Three-Step Process

**Step 1: Mission Deconstruction**
The LLM agent deconstructs the query into a numbered checklist of "Required Findings" — the specific pieces of information needed to answer it completely.

**Step 2: Intelligence Synthesis & Analysis**
For each required finding, the agent checks the evidence:
- **Confirmed Findings**: What is supported by the evidence (with logical inferences allowed — don't require explicit statements)
- **Remaining Gaps**: What is still missing, stated as actionable search requirements

**Step 3: Final Assessment**
- `Sufficient: Yes` → Exit loop, proceed to generation
- `Sufficient: No` → Identify gaps, trigger Query Refinement

### Critical Behavioral Rules for the SEA Agent
From the paper's prompt engineering:
1. **Be question-centric, not evidence-centric.** Ignore interesting but irrelevant facts.
2. **Make logical inferences.** If evidence says person was born in Iran, infer nationality. Don't say "it does not explicitly state."
3. **Only confirm if evidence truly supports it.** Don't hallucinate confirmations.
4. **Remaining Gaps must be actionable** — phrased as what to search for next.

### SEA Performance
- Multi-hop datasets: **72–83% accuracy** — reliable for complex queries
- Simple factoid datasets (TriviaQA): **54%** — less reliable for single-hop (this is expected; the loop just runs once anyway)

### Fiqh-Specific SEA Checklist Example

**Query:** "What is Sistani's ruling on fasting for a traveler who intends to stay for 10 days?"

**Required Findings:**
1. Does Sistani address fasting rules for travelers?
2. What is the threshold of intended stay that changes the ruling?
3. Is a 10-day stay sufficient to obligate fasting?
4. Are there any conditions or exceptions?

SEA checks each → if any remain unconfirmed → trigger refinement.

---

## 8. Phase 6: Iterative Query Refinement

### Purpose
When SEA identifies gaps, generate **new, laser-focused sub-queries** targeting only the missing information — using already-confirmed facts to make queries more precise.

### Key Principle: Use Confirmed Facts to Narrow
> "Once the summary confirms the director is 'Christopher Nolan', the next query should be 'Christopher Nolan children ages', not a generic 'director of Inception children ages'."

For Fiqh: Once confirmed that the base ruling is X, the refinement query should use X directly, not re-derive it.

### Refinement Query Rules
- Generate 1–4 new queries (only as many as needed)
- Each query targets exactly one gap
- Never repeat or rephrase previous queries
- Leverage confirmed facts to add precision

### Fiqh Example

**Confirmed:** "Sistani rules that a traveler who intends to stay 10 days must pray full prayers"
**Gap:** "Does the same 10-day rule apply to fasting?"

**Refined Query:** "Sistani ruling fasting traveler 10 days intention stay" — NOT "Sistani traveler fasting"

### Query Refinement Performance
Scored **4.45–4.61/5.0** in component-level evaluation — the **highest-performing component** in the pipeline. The targeted, gap-driven approach works very well.

---

## 9. Phase 7: Faithful Answer Generation

### Purpose
Once evidence is verified as sufficient by SEA, generate a final answer that is **strictly grounded** in the retrieved evidence only.

### Generation Constraints (Critical for Fiqh)
The generation prompt must enforce:

1. **Source-only answers**: No parametric knowledge. Every claim must come from a retrieved document.
2. **Citation embedding**: Every fact gets a reference token `[1]`, `[2]`, etc., linking to the source document.
3. **No speculation**: If evidence is ultimately incomplete, state that directly — do not guess.
4. **Neutrality on disputed matters**: Present multiple scholarly views if they exist in the evidence.

### Fiqh-Specific Generation Rules (Critical)

From FARSIQA, these **must** be included in the generation prompt:

#### Fatwa Disclaimer (Non-Negotiable)
The system must **never issue a fatwa**. Include this disclaimer when any ruling is requested:

```
[Warning] I am not authorized to issue religious rulings (fatwas). 
This answer is based on Ayatollah Sistani's published works and 
authenticated sources retrieved from the knowledge base. For a 
definitive ruling specific to your situation, please consult a 
qualified religious authority or Ayatollah Sistani's official office.
```

#### Handling Controversial/Disputed Rulings
If the retrieved evidence contains multiple opinions or the question touches on a disputed matter:
- Present all views found in the evidence **neutrally**
- Do not endorse one over another
- Make clear these are scholarly positions, not your own rulings

#### Insufficient Evidence Response
If the loop exhausts iterations and evidence is still incomplete:
```
[Warning] The available sources did not contain complete information 
to provide a definitive ruling on this question. Based on the 
retrieved evidence, here is what can be said: [partial answer]
For a complete ruling, please consult Ayatollah Sistani's official 
resources or a qualified jurist.
```

### Answer Structure
- Short factual ruling: Direct answer + citation + disclaimer if needed
- Complex ruling: Structured paragraphs, each claim cited, summary at end
- Out-of-scope (missed by router): Politely redirect

---

## 10. Dynamic LLM Allocation Strategy

### The Core Idea
Different tasks in the pipeline have different complexity requirements. Use **smaller, cheaper models** for simple tasks and **larger models** for critical reasoning tasks.

### Task-to-Model Mapping (from FARSIQA)

| Task | Recommended Model Size | Rationale |
|---|---|---|
| Query Validation & Routing | Small | Simple classification task |
| Query Decomposition | Small | Pattern-based decomposition |
| Structured Evidence Assessment (SEA) | Small–Medium | Structured checklist, but needs some reasoning |
| Evidence Filtering | **Large** | Subtle relevance judgments require stronger reasoning |
| Query Refinement | **Large** | Critical precision task — wrong queries waste iterations |
| Final Answer Generation | **Large / Reasoner** | Most complex; depends on query type from router |

### Cost-Benefit Results from FARSIQA (Table 6)

| Config | Correctness | Faithfulness | Neg. Rejection | Cost ($/query) | Latency |
|---|---|---|---|---|---|
| Static Small | 3.38 | 35.4% | 74.0% | 5.33e-4 | 30.1s |
| Static Large | 4.03 | 65.6% | 94.0% | 2.89e-3 | 21.8s |
| Static Reasoner | 4.33 | 57.7% | 82.0% | 2.96e-2 | 77.9s |
| **Dynamic (recommended)** | **4.06** | **62.5%** | **97.0%** | **2.51e-3** | **22.1s** |

**Key insight:** Dynamic allocation is **13% cheaper than Static Large** while achieving **better Negative Rejection** (97% vs 94%). The Static Reasoner is 11.8x more expensive with worse faithfulness.

### Recommendation for Your Implementation
- Use a small/medium model (e.g., GPT-4o-mini, Llama-3-8B) for routing, decomposition, SEA
- Use a large model (e.g., GPT-4o, Llama-3.1-70B) for filtering, refinement, and generation
- Reserve a reasoning model (e.g., o1, DeepSeek-R1) only for `VALID_REASONER` queries (complex inheritance calculations, etc.)

---

## 11. Fiqh-Specific Adaptations from FARSIQA

### Knowledge Base Design
FARSIQA used a mix of **encyclopedic sources** and **Q&A platform data**. For Sistani-specific Fiqh:

**Priority sources:**
- Ayatollah Sistani's official books (*Islamic Laws*, *A Code of Practice for Muslims in the West*, etc.)
- Official Sistani.org Q&A responses
- Authenticated question-and-answer compilations

**Chunking Strategy (from FARSIQA):**
- Split by paragraph first (preserves semantic cohesion)
- Sub-split paragraphs exceeding a token limit into sentences
- For Q&A data: prepend the question to each answer chunk — this dramatically improves retrieval because queries match questions, not answer text
- Target chunk size: ~300–400 tokens (FARSIQA used 378 tokens based on their model's architecture)

**Metadata to include per chunk:**
- Source book/document name
- Chapter/section
- Source URL (for citation)
- Topic tags if available (e.g., "tahara", "salah", "sawm", "hajj", "khums")

### Query Validation: Scope Definition for Fiqh
Your routing prompt needs a clear definition of what is in-scope. Be explicit:
- **In-scope:** Questions about halal/haram, prayer, fasting, purification, transactions, family law, etc. — specifically as answered by Sistani's published rulings
- **Out-of-scope:** General Islamic history, other scholars' opinions (unless comparative), non-Islamic questions
- **Hybrid (stay in-scope):** If anchored to Sistani, even adjacent questions are in-scope ("What did Sistani say about using smartphones during Ramadan?")

### Ethical Safeguards Specific to Fiqh
From FARSIQA's generation prompt — these must be hardcoded:
1. **Never issue a fatwa** — always disclaim
2. **Never answer questions about specific personal situations** with a definitive ruling — refer to Sistani's office
3. **For disputed rulings between mara'ja**, present neutrally and note the disagreement
4. **Khums, inheritance, divorce** — always add an extra disclaimer to consult directly

### Negative Rejection — The Critical Metric
FARSIQA achieved **97% Negative Rejection accuracy** (vs 57% for naive RAG). This is the metric that matters most for your use case — the system must correctly refuse to answer when:
- The question is outside Sistani's documented rulings
- The knowledge base doesn't contain relevant information
- The question requires a personalized fatwa

The routing layer is the **first** defense; the generation prompt's "insufficient evidence" clause is the **second**.

---

## 12. Iteration Count: How Many Loops?

### Evidence from Both Papers

**FAIR-RAG (Table 4) — Multi-hop QA datasets:**
| Iterations | Avg. Answer Rank (lower=better) | Improvement Rate vs Iter 1 |
|---|---|---|
| 1 | 2.73–3.08 | — |
| 2 | 2.20–2.31 | 58–69% |
| **3** | **2.10–2.38** | **63–71%** ← optimal |
| 4 | 2.43–2.66 | 61–67% (degrades!) |

**FARSIQA (Table 5) — Islamic domain:**
| Iterations | Avg. Answer Rank | Improvement vs Iter 1 |
|---|---|---|
| 1 | 3.32 | — |
| 2 | 2.50 | 74.9% |
| **3** | **2.10** | **80.1%** ← optimal |
| 4 | 2.08 | 77.3% (negligible gain, +7% cost) |

### Conclusion: Use Max 3 Iterations
- Moving from 1 → 2 iterations is the **biggest quality jump** (58–75% improvement rate)
- Moving from 2 → 3 gives additional meaningful improvement
- Moving from 3 → 4 gives **negligible or negative** quality change while increasing cost by ~7% and latency by ~7%
- **Hard-code `max_iter = 3` as your default**

### For Simple Queries
The SEA module will declare sufficiency after iteration 1 for most simple Fiqh lookups. The loop exits early — you don't always pay the 3-iteration cost.

---

## 13. Failure Mode Taxonomy

Understanding failure modes helps you prioritize improvements. Both papers categorized errors systematically.

### FAIR-RAG Failure Distribution (200 error samples)
| Category | % of Errors | Description |
|---|---|---|
| Retrieval Failure | 32.5% | Correct docs not in corpus at all |
| Generation Failure | 31.0% | Right evidence, wrong synthesis |
| SEA Error | 24.5% | Premature sufficiency or wrong gap analysis |
| Query Decomposition | 9.0% | Wrong sub-queries from the start |
| Evidence Filtering | 1.5% | Good docs discarded |
| Query Refinement | 1.5% | Ineffective follow-up queries |

### FARSIQA Failure Distribution (122 error samples — Islamic domain)
| Category | % of Errors | Description |
|---|---|---|
| **Generation Failure** | **54.9%** | Dominant — LLM synthesizes incorrectly even with good evidence |
| Retrieval Failure | 27.9% | Knowledge base gaps for obscure Fiqh questions |
| Query Decomposition | 9.0% | Misparse of compound relational queries |
| Evidence Filtering | 5.7% | Over-aggressive pruning |
| SEA Error | 2.5% | Premature termination |
| Query Refinement Error | 0% | Zero failures — most robust component |

### Actionable Insights for Fiqh

1. **Generation is your biggest risk.** Invest heavily in the generation prompt's constraints. The LLM will synthesize incorrectly even with good evidence.
2. **Knowledge base coverage is second.** For obscure Fiqh edge cases, the system simply won't find the answer — make sure your knowledge base is comprehensive for Sistani's published works.
3. **SEA errors cause premature answers.** If SEA incorrectly says "sufficient" too early, the loop stops and generation proceeds with incomplete evidence. Use clear, structured prompts for SEA.
4. **Query Refinement almost never fails** — trust it.

### Common Generation Failure Subtypes (Relevant to Fiqh)
- **Incorrect Entity Mapping**: "Model chose wrong ruling from a list of candidates"
- **Flawed Logical Inference**: Especially on comparative questions ("which is stricter?")
- **Misinterpretation of Granularity**: User asks about a general case, model answers a specific sub-case
- **Ignoring Correct Evidence**: With conflicting docs, model may ground on the wrong one

---

## 14. Evaluation Metrics to Track

### End-to-End Metrics
| Metric | Description | Target |
|---|---|---|
| **Answer Correctness** (LLM-as-Judge) | Semantic correctness vs ground truth, 1–5 scale | ≥4.0 score rate: aim for >70% |
| **Answer Faithfulness** | % of answers classified "Fully Faithful" | >60% (FARSIQA achieved 62.5%) |
| **Negative Rejection Accuracy** | % of out-of-scope questions correctly refused | >95% (FARSIQA: 97%) |
| **Answer Relevance** | How well answer addresses the question, 1–5 | >3.8 |
| **Noise Robustness** | % correct despite noisy context | >80% |

### Component-Level Metrics (for debugging)
| Component | Metric | FARSIQA Baseline |
|---|---|---|
| Query Decomposition | LLM Judge score (1–5) | 4.13 |
| Evidence Filtering | F1 (precision + recall) | 74.2% |
| SEA | Accuracy | 66.0% |
| Query Refinement | LLM Judge score (1–5) | 4.61 |

### Lexical Metrics (Secondary)
- **Exact Match (EM)**: Strict; useful for factoid questions
- **F1 Token Overlap**: More lenient; good for partial credit

### LLM-as-Judge for Semantic Evaluation
Use a capable LLM (e.g., GPT-4o) as a judge for semantic correctness with a simple binary Yes/No prompt. FAIR-RAG achieved **90% agreement with human annotators** using this approach.

---

## 15. Complete Prompt Templates

These are adapted from the papers for a Fiqh/Sistani context in English. Translate to Persian/Arabic as needed for your use case.

### 15.1 Query Validation Prompt

```
**Situation:** A user has submitted a question to a Shia Islamic Fiqh Q&A system focused 
on the rulings of Ayatollah Sistani.

**Intent:**
1. Determine if the question is within the system's scope (Fiqh and Islamic knowledge 
   related to Sistani's rulings) and adheres to ethical guidelines.
2. If valid, assess complexity and determine the appropriate processing strategy.

**Classify the question into exactly one of these categories:**

- "VALID_OBVIOUS": The question is about well-known Islamic facts that can be answered 
  from general common knowledge (e.g., "How many times a day do Muslims pray?"). 
  Answer directly, bypass RAG.

- "VALID_SMALL": Simple factual Fiqh lookup with a direct answer (e.g., "Is smoking 
  haram according to Sistani?"). Use RAG with small LLM.

- "VALID_LARGE": Requires explanation, reasoning, or contextual understanding 
  (e.g., "Explain Sistani's ruling on combining prayers during travel"). 
  Use RAG with large LLM.

- "VALID_REASONER": Requires multi-step deduction, calculations, or complex rule 
  application (e.g., "Calculate the khums on these assets given these conditions..."). 
  Use RAG with reasoning LLM.

- "OUT_OF_SCOPE": The question has no anchor to Islamic Fiqh, Sistani's rulings, 
  or related Islamic knowledge (e.g., "How do I configure WiFi?"). Politely decline.

- "UNETHICAL": The question promotes harm, asks for impermissible content, or 
  violates ethical guidelines. Reject.

**Important Rules:**
- If the question is anchored to Sistani, Islamic jurisprudence, or related concepts — 
  it is IN SCOPE even if it touches adjacent topics.
- Questions about other mara'ja can be answered if they help contextualize Sistani's 
  position.
- PREFER "VALID_LARGE" as the default for most valid Fiqh questions.

**User Question:** "{user_query}"

**Output:** (Only output the label on a new line after "Selected Label:")
Selected Label:
```

### 15.2 Query Decomposition Prompt

```
**Situation:** You are an expert query analyst for a Shia Islamic Fiqh Q&A system. 
A user has asked a question that may be complex or multi-faceted. Decompose it into 
focused, independently searchable sub-queries.

**Intent:** Break the original question into up to 4 distinct, keyword-rich sub-queries 
that collectively cover all aspects of the question. Each sub-query should be optimized 
for retrieval from a Fiqh knowledge base.

**Principles:**
1. Identify distinct concepts: separate the ruling sought, the subject matter, 
   the conditions, and any comparative elements.
2. Use domain-specific terms: include Arabic/Persian Fiqh terminology where appropriate 
   (e.g., tahara, wudu, najasah, tayammum, halal, haram, makruh, mustahab).
3. Each sub-query should be independently searchable.
4. Cover all facets — leave no part of the original question without a corresponding 
   sub-query.

**Example:**
Original Question: "What is Sistani's ruling on a person who doubts whether their 
wudu was valid after they have already begun praying?"

Sub-queries:
- Sistani ruling doubt during prayer wudu validity
- Shak (doubt) after wudu Sistani Islamic law
- Prayer validity if wudu doubtful Sistani
- Ruling continuing prayer after doubt tahara

**User Query:** "{user_query}"

**Constraints:**
- Generate 1 to 4 sub-queries only.
- Each on a new line prefixed with "- ".
- Do not add explanations.

Optimized Queries:
```

### 15.3 Evidence Filtering Prompt

```
**Situation:** Documents have been retrieved for a Fiqh question. Filter out any 
documents that are completely irrelevant.

**CRITICAL PRINCIPLE: BE INCLUSIVE. When in doubt, KEEP the document.**

A document is only "Not Useful" if it:
- Is about a completely different topic unrelated to the question
- Is about a different scholar's ruling when Sistani-specific is needed AND adds no context
- Contains no information about any entity in the question

**Original User Query:** "{original_query}"

**Retrieved Documents (Batch {batch_number}):**
{numbered_candidates_text_for_prompt}

**KEEP documents that contain:**
- Any ruling or discussion related to the topic (even partial)
- Contextual information about related concepts
- Background information that helps understand the ruling
- Related Fiqh principles that may apply

**REMOVE only documents that:**
- Are about an entirely different Fiqh topic with no connection
- Discuss a different scholar with no relevance to Sistani's methodology

**Output:** List ONLY the IDs of documents to REMOVE, or "None" if all should be kept.
Format: [doc_X], [doc_Y] or None

Unhelpful Document IDs:
```

### 15.4 Structured Evidence Assessment (SEA) Prompt

```
**Role:** You are a Strategic Fiqh Evidence Analyst. Your mission is to determine 
whether the provided evidence is sufficient to accurately answer the user's Fiqh question.

**Core Mission:** Be QUESTION-CENTRIC. Deconstruct the query into a checklist of 
required informational components, then systematically verify each against the evidence. 
Ignore all information that does not address the checklist items.

**You MUST follow this exact format:**

**1. Mission Deconstruction:**
- **Main Goal:** [State the primary objective of the question]
- **Required Findings:** [List each specific piece of information needed for a complete answer]

**2. Intelligence Synthesis & Analysis:**
- **Confirmed Findings:** [For each required finding, state what evidence confirms it. 
  Make logical inferences — do not require explicit statements. Do NOT use weak phrases 
  like "it does not explicitly state."]
- **Remaining Gaps:** [State any required findings not yet confirmed, phrased as 
  what needs to be searched. Write "None" if all confirmed.]

**3. Final Assessment:**
- **Conclusion:** [Summarize what can and cannot be answered]
- **Sufficient:** [Single word: "Yes" or "No"]

**Rules:**
- Only declare "Yes" if ALL required findings are confirmed.
- Logical inferences from strong evidence count as confirmed.
- Do not confirm findings that are not supported by the evidence.
- Remaining Gaps must be actionable search requirements, not vague statements.

---
**Original Question:**
"{original_query}"

**Evidence:**
{combined_evidence}
```

### 15.5 Query Refinement Prompt

```
**Situation:** Initial evidence gathering was incomplete. Use the analysis summary 
to generate new, targeted sub-queries that fill exactly the identified gaps.

**Intent:** Generate new search queries targeting ONLY the missing information. 
Use confirmed facts to make the new queries more precise.

**Logic:**
- USE confirmed facts from the summary to narrow the new queries
  (e.g., if confirmed that the ruling topic is "tayammum", the query should say 
  "tayammum" not "Islamic purification alternative")
- TARGET only the remaining gaps — one query per gap ideally
- NEVER repeat or rephrase previous queries

**Original Question:** {original_query}

**Analysis Summary (confirmed facts + remaining gaps):**
{analysis_summary}

**Previous Queries Used:**
{combined_previous_queries}

**Constraints:**
- Generate 1 to 4 new sub-queries only.
- Each on a new line prefixed with "- ".
- Make them keyword-rich and specific.
- Do not add explanations.

Improved Queries:
```

### 15.6 Faithful Answer Generation Prompt

```
**Situation:** You are an expert Islamic Fiqh assistant specializing in the rulings 
of Ayatollah Sistani. Evidence has been retrieved and verified. Generate a faithful, 
accurate, and well-cited answer.

**STRICT RULES — YOU MUST FOLLOW ALL OF THESE:**

1. **Source-Only Answers:** Base your answer EXCLUSIVELY on the provided evidence. 
   Do NOT use your parametric knowledge or add any information not found in the evidence.
   
2. **Citation Required:** After every factual claim, embed a citation token [1], [2], etc. 
   linking to the source document number.

3. **No Fatwa Issuance:** You are NOT authorized to issue fatwas. If the question asks 
   for a ruling, include this disclaimer:
   "[Note: This response is based on Ayatollah Sistani's published works as retrieved 
   from authenticated sources. For a definitive ruling on your specific situation, 
   please consult a qualified jurist or Ayatollah Sistani's official office.]"

4. **Neutrality on Disputed Matters:** If the evidence presents multiple scholarly 
   views, present all of them without endorsing any.

5. **Insufficient Evidence:** If the evidence does not contain enough information to 
   answer the question:
   "[Warning: The available sources did not contain complete information for a 
   definitive answer. Based on retrieved evidence: [partial answer]. 
   Please consult Ayatollah Sistani's official resources for a complete ruling.]"

6. **If NO relevant evidence exists at all:** Respond only with:
   "[Warning: No relevant information was found in the knowledge base for this question. 
   Please consult Ayatollah Sistani's official website or a qualified religious authority.]"

7. **Structure:** 
   - Short factual ruling: 1–2 sentences + citation + disclaimer if needed
   - Complex ruling: structured paragraphs, each claim cited, brief summary at end

**Evidence (numbered, with source):**
{combined_evidence}

**Original Question:**
{original_query}

**Answer:**
```

---

## 16. Implementation Checklist for Your FastAPI Backend

### Architecture Changes Required

- [ ] **Add query validation/routing endpoint** as the entry point — run this before any retrieval
- [ ] **Implement hybrid retrieval** — add BM25/sparse search alongside your existing dense retrieval; implement RRF merging
- [ ] **Add evidence filtering step** after retrieval aggregation, using an LLM agent with the filtering prompt
- [ ] **Implement SEA module** — this is the most critical new component; it must produce structured output (confirmed findings, gaps, sufficiency verdict)
- [ ] **Add query refinement agent** — generates follow-up queries based on SEA's gap analysis
- [ ] **Build the iteration loop** — wire the above into a loop with `max_iter=3` and early exit on `sufficient=Yes`
- [ ] **Replace generation prompt** with the faithful generation prompt that enforces citations and fatwa disclaimers
- [ ] **Add citation tracking** — maintain a list of source documents used so the generator can reference them

### LLM Agent Configuration

- [ ] Define which LLM handles each task (small vs. large vs. reasoner)
- [ ] Implement structured output parsing for SEA (need to extract: confirmed findings, gaps, sufficiency boolean)
- [ ] Implement structured output parsing for routing (need: one of 6 category labels)
- [ ] Add retry logic for malformed LLM outputs

### State Management Per Request

Each query needs a running state object:
```python
{
  "original_query": str,
  "query_type": str,          # from router
  "selected_generator": str,  # from router
  "all_sub_queries": list,    # grows each iteration
  "aggregated_evidence": list, # grows each iteration
  "analysis_summary": str,    # from last SEA run
  "iteration_count": int,
  "is_sufficient": bool
}
```

### Fiqh-Specific Knowledge Base Setup

- [ ] Ingest Ayatollah Sistani's complete published works (Islamic Laws, etc.)
- [ ] Ingest Sistani.org Q&A data — prepend questions to answer chunks
- [ ] Chunk at ~350 tokens with paragraph-boundary awareness
- [ ] Index each chunk with: text, embedding vector, source URL, document title, topic tags
- [ ] Ensure Elasticsearch (or equivalent) supports simultaneous BM25 + vector search
- [ ] Test retrieval on 20–30 sample Fiqh questions before deploying the full pipeline

### Testing Priorities

1. **Negative rejection** — test with 20 clearly out-of-scope questions; all should be refused
2. **Simple Fiqh rulings** — should resolve in 1 iteration
3. **Multi-hop Fiqh** — e.g., "Ruling X depends on condition Y, what is condition Y for case Z?"
4. **Fatwa disclaimer** — verify it appears on every answer that states a ruling
5. **Citation presence** — every factual claim should have a `[n]` token

---

## Summary: The 5 Things That Matter Most

1. **SEA is the innovation.** The checklist-based gap analysis is what makes this architecture reliable. Implement it carefully — it controls the entire loop.

2. **3 iterations maximum.** Both papers converge on this. More doesn't help; it adds noise and cost.

3. **Negative rejection is your #1 safety metric.** For Fiqh, refusing to answer incorrectly is as important as answering correctly. FARSIQA achieved 97% — target that.

4. **The generation prompt is your last defense against hallucination.** Heavy constraints, fatwa disclaimers, citation requirements, and evidence-only instructions must all be enforced here.

5. **Query Refinement almost never fails (0% error rate in FARSIQA).** Once SEA identifies gaps correctly, the refinement module reliably generates good follow-up queries. Invest your debugging effort in SEA, not refinement.
