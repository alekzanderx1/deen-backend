# Phase 1: Data Foundation - Research

**Researched:** 2026-03-23
**Domain:** PDF parsing, text chunking, dense/sparse embedding, Pinecone index ingestion
**Confidence:** HIGH

## Summary

Phase 1 ingests Sistani's "Islamic Laws" (4th edition) PDF into two dedicated Pinecone indexes (dense + sparse). The PDF is already committed at `documentation/fiqh_related_docs/english-islamic-laws-4th-edition.pdf` — 533 pages containing exactly 2796 uniquely numbered rulings (Ruling 1 through Ruling 2796, no gaps). PyMuPDF (`fitz`) is the correct parser — it is not yet installed in the project venv and must be added to `requirements.txt`.

The corpus contains approximately 396,047 tokens across all rulings, producing roughly 1,100–1,400 chunks at the 300–400 token target. 95% of individual rulings are at or below 300 tokens and require no splitting; only 82 rulings (2%) exceed 400 tokens and need secondary paragraph splitting. Chapter structure uses "CHAPTER ONE / Following a Jurist" headings and numbered sub-sections like "1. Kurr water" — both are extractable by walking page text. BM25Encoder from `pinecone-text` 0.11.0 is the locked sparse encoder; it requires NLTK `stopwords` and `punkt_tab` data that must be downloaded at setup time and serializes to JSON via `.dump()` / `.load()` (not pickle). Pinecone SDK 7.3.0 supports `vector_type="sparse"` with `metric="dotproduct"` for the sparse index.

**Primary recommendation:** Parse PDF with PyMuPDF direct text extraction (not pymupdf4llm — that is overkill for structured text). Split at ruling boundaries using `re.split(r'(Ruling\s+\d+\.)', text)`, apply secondary paragraph splitting only for the ~82 oversized rulings. Fit BM25Encoder on the full chunk corpus before upsert. Use `all-mpnet-base-v2` (768 dimensions, already loaded via `getDenseEmbedder()`) for dense embeddings. Upsert both indexes in batches of 100 vectors.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**PDF Source & Parsing**
- D-01: The PDF is committed in the repository. Researcher to locate the exact file path.
- D-02: Ruling numbers follow the format `"Ruling 1"`, `"Ruling 2"`, etc. The chunking regex anchors on this prefix: `Ruling\s+\d+`. Ruling-number boundaries are the primary split points (per INGE-02); paragraph boundaries are secondary.

**Sparse Encoder**
- D-03: Use `pinecone-text` BM25Encoder for sparse embeddings (per INGE-05, INGE-06). This differs from the existing `modules/embedding/embedder.py` which uses TF-IDF fitted at query-time. The fiqh ingestion pipeline uses BM25 and persists the fitted encoder to disk for consistent query-time encoding in Phase 2.
- D-04: TF-IDF (existing embedder) is NOT used for the fiqh indexes. Do not reuse `getSparseEmbedder()` from `modules/embedding/embedder.py` for fiqh.

**Pinecone Indexes**
- D-05: Dense index env var: `DEEN_FIQH_DENSE_INDEX_NAME` (value: `deen-fiqh-dense`). Already added to `.env`.
- D-06: Sparse index env var: `DEEN_FIQH_SPARSE_INDEX_NAME` (value: `deen-fiqh-sparse`). Already added to `.env`.
- D-07: Dense index config: 768 dimensions, cosine metric, serverless. Matches `sentence-transformers/all-mpnet-base-v2` output dimensions.
- D-08: Sparse index config: Sparse type, dotproduct metric, serverless. No fixed dimension (BM25 vectors are variable-length).
- D-09: Both indexes use the same cloud/region as the existing `DEEN_DENSE_INDEX_NAME` and `DEEN_SPARSE_INDEX_NAME` indexes.

**Ingestion Script**
- D-10: Script lives in `scripts/ingest_fiqh.py` — consistent with existing scripts in `scripts/`.
- D-11: Re-runnable with Pinecone upsert semantics. Re-running is safe if chunking strategy or metadata changes mid-process. Indexes do not need to be cleared manually between runs.
- D-12: Progress reporting: batch-level logs, e.g. `"Uploaded 200/1400 chunks"`. Not per-chunk verbose. Not summary-only.

**Document ID & Metadata**
- D-13: Each chunk's Pinecone vector ID must be derived from ruling number + chunk index (not `hadith_id`). Downstream retrieval and reranking for fiqh must use a different ID field.
- D-14: Required metadata per chunk (INGE-03): `source_book`, `chapter`, `section`, `ruling_number`, `topic_tags` (e.g. tahara, salah, sawm, hajj, khums).

### Claude's Discretion
- Exact chunk overlap strategy (e.g. zero overlap vs. N-token overlap between adjacent chunks)
- Batch size for Pinecone upsert calls
- Filename/path where the fitted BM25 encoder is persisted (e.g. `data/fiqh_bm25_encoder.pkl`)
- Whether to include a dry-run mode that prints detected ruling numbers without uploading

### Deferred Ideas (OUT OF SCOPE)
None raised during discussion.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INGE-01 | Parse Sistani's "Islamic Laws" (4th edition) PDF into structured text preserving chapter/section hierarchy and ruling numbers | PyMuPDF page.get_text() confirmed. CHAPTER ONE / numbered sub-section pattern documented. 2796 rulings confirmed. |
| INGE-02 | Chunk parsed text at ~300-400 tokens with ruling-number boundaries as primary split points, paragraph boundaries as secondary | 95% of rulings fit in ≤300 tokens natively. `re.split(r'(Ruling\s+\d+\.)', text)` pattern confirmed against actual PDF text. |
| INGE-03 | Each chunk tagged with metadata: source_book, chapter, section, ruling_number(s), topic_tags | Chapter heading pattern ("CHAPTER ONE / Following a Jurist") and sub-section pattern ("1. Kurr water") confirmed parseable. |
| INGE-04 | Dense embeddings for all chunks uploaded to dedicated Pinecone fiqh dense index | `getDenseEmbedder()` (all-mpnet-base-v2, 768 dims) confirmed reusable. Pinecone 7.3.0 `create_index` API verified. |
| INGE-05 | Sparse embeddings using pinecone-text BM25 for all chunks uploaded to dedicated fiqh sparse index | BM25Encoder API verified (fit, encode_documents, dump). Sparse index `vector_type="sparse"` confirmed in Pinecone 7.3.0. |
| INGE-06 | Sparse encoder initialized with fiqh corpus vocabulary for consistent ingestion and query-time encoding | BM25Encoder.dump() serializes to JSON. BM25Encoder.load() restores from JSON. NLTK dependency documented. |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- **Language:** Python 3.11 only. No other languages.
- **Naming:** `snake_case` for modules/functions/variables; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants.
- **Type hints:** Add type hints to new/changed functions.
- **Logging:** Prefer `logger.*` over `print()` in new code. Use `core/logging_config.py` pattern.
- **Error handling:** Catch exceptions in scripts and raise domain-appropriate errors. Do not leak internal details.
- **Imports:** Standard library first, then third-party, then local.
- **Path in scripts:** Add project root to `sys.path` via `Path(__file__).parent.parent` at the top (see `scripts/generate_primers.py`).
- **Config:** New env vars (`DEEN_FIQH_DENSE_INDEX_NAME`, `DEEN_FIQH_SPARSE_INDEX_NAME`) must be added to `core/config.py` following the existing `os.getenv()` pattern.
- **No reuse of getSparseEmbedder()** from `modules/embedding/embedder.py` for fiqh (D-04).
- **Commit style:** `feat: add fiqh ingestion script` format.
- **GSD workflow enforcement:** All changes go through a GSD plan.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pymupdf | 1.27.2.2 (latest) | PDF text extraction (`fitz.open`, `page.get_text()`) | Best-in-class Python PDF parser; handles complex layouts; zero dependency on Java/LibreOffice |
| pinecone-text | 0.11.0 (latest) | BM25Encoder for sparse embeddings | Pinecone's official sparse encoder; locked by D-03 |
| sentence-transformers | 3.4.1 (already installed) | Dense embeddings via all-mpnet-base-v2 | Already in venv via `getDenseEmbedder()`; 768 dimensions matches D-07 |
| tiktoken | 0.9.0 (already installed) | Token counting to enforce 300-400 token chunk target | Already in requirements.txt; `cl100k_base` encoding |
| langchain-text-splitters | 0.3.9 (already installed) | Secondary paragraph splitting for the ~82 oversized rulings | Already in requirements.txt; `TokenTextSplitter` handles overflow |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| nltk | (pinecone-text dependency) | Stopwords and punkt_tab for BM25Tokenizer | Required at BM25Encoder init; must download data at setup |
| pinecone | 7.3.0 (already installed) | Pinecone SDK for index creation and upsert | Already in venv |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pymupdf (fitz) | pymupdf4llm | pymupdf4llm adds markdown conversion overhead not needed here; structured text from `page.get_text()` is sufficient and simpler |
| pymupdf (fitz) | pdfplumber | pdfplumber is slower and has more difficulty with Unicode (Arabic transliterations) |
| BM25Encoder | TF-IDF from embedder.py | Explicitly forbidden by D-04; BM25 is more principled for retrieval |

**Installation (additions to requirements.txt):**
```bash
pip install "pymupdf==1.27.2.2" "pinecone-text==0.11.0"
```

**Version verification (confirmed against PyPI on 2026-03-23):**
- `pymupdf`: 1.27.2.2 (latest)
- `pinecone-text`: 0.11.0 (latest)

---

## Architecture Patterns

### Recommended Project Structure
```
scripts/
└── ingest_fiqh.py              # Main ingestion script (D-10)

data/
└── fiqh_bm25_encoder.json      # Persisted BM25 params (Claude's discretion)

documentation/
└── fiqh_related_docs/
    └── english-islamic-laws-4th-edition.pdf   # Source PDF (confirmed at this path)
```

### Pattern 1: PDF Parsing with Ruling-Boundary Extraction
**What:** Extract full text via PyMuPDF, then split on `Ruling\s+\d+\.` pattern
**When to use:** This is the only required parsing strategy for this corpus

The PDF's ruling format is:
```
Ruling 1. A Muslim's belief in the fundamentals of religion...
```

Chapter headings appear as:
```
CHAPTER ONE
Following a Jurist (Taqlīd)
```

Sub-section headings appear as:
```
1. Kurr water
2. Qalīl water
```

**Parsing approach:**
```python
import fitz
import re

def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    return "\n".join(pages)

def split_by_rulings(full_text: str) -> list[tuple[str, int]]:
    """Returns list of (ruling_text, ruling_number) tuples."""
    parts = re.split(r'(Ruling\s+(\d+)\.)', full_text)
    # parts alternates: preamble, "Ruling N.", ruling_number, body, ...
    ...
```

### Pattern 2: BM25Encoder Fit-then-Persist
**What:** Fit BM25 on all chunk texts before any upsert, then persist to disk
**When to use:** Must happen before sparse upsert; same encoder reloaded at query time

```python
# Source: pinecone_text/sparse/bm25_encoder.py (confirmed API)
from pinecone_text.sparse import BM25Encoder

encoder = BM25Encoder()
encoder.fit(all_chunk_texts)           # list[str] of all chunks
encoder.dump("data/fiqh_bm25_encoder.json")   # JSON serialization

# At query time (Phase 2):
encoder = BM25Encoder()
encoder.load("data/fiqh_bm25_encoder.json")
sparse_vec = encoder.encode_queries("ablution ruling")
```

**NLTK setup required before BM25Encoder instantiation:**
```python
import ssl
import nltk
ssl._create_default_https_context = ssl._create_unverified_context  # macOS workaround
nltk.download('stopwords', quiet=True)
nltk.download('punkt_tab', quiet=True)
```

### Pattern 3: Pinecone Index Creation (Serverless)
**What:** Create dense and sparse indexes if they do not already exist
**When to use:** At the start of the ingestion script; idempotent via `if index_name not in pc.list_indexes().names()`

```python
# Source: Pinecone SDK 7.3.0 (confirmed API)
from pinecone import Pinecone, ServerlessSpec
from pinecone.db_control.enums import VectorType, Metric

pc = Pinecone(api_key=PINECONE_API_KEY)

# Dense index
if DEEN_FIQH_DENSE_INDEX_NAME not in [i.name for i in pc.list_indexes()]:
    pc.create_index(
        name=DEEN_FIQH_DENSE_INDEX_NAME,
        dimension=768,
        metric="cosine",
        vector_type="dense",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),  # match existing indexes
    )

# Sparse index — no dimension parameter for sparse
if DEEN_FIQH_SPARSE_INDEX_NAME not in [i.name for i in pc.list_indexes()]:
    pc.create_index(
        name=DEEN_FIQH_SPARSE_INDEX_NAME,
        metric="dotproduct",
        vector_type="sparse",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
```

### Pattern 4: Pinecone Upsert Format
**What:** Upsert dense and sparse vectors using the correct SDK data structures
**When to use:** After encoding all chunks

```python
# Source: pinecone.db_data.dataclasses (confirmed API)
from pinecone.db_data.dataclasses import Vector, SparseValues

# Dense upsert (via LangChain PineconeVectorStore or direct SDK)
# Direct SDK approach for ingestion (consistent with retriever pattern):
dense_idx = pc.Index(DEEN_FIQH_DENSE_INDEX_NAME)
dense_idx.upsert(
    vectors=[
        Vector(
            id=f"fiqh-{ruling_number}-{chunk_idx}",
            values=dense_embedding,       # list[float], 768 dims
            metadata={
                "text_en": chunk_text,
                "source_book": "Islamic Laws 4th Edition",
                "chapter": chapter,
                "section": section,
                "ruling_number": ruling_number,
                "topic_tags": topic_tags,  # list[str]
            }
        )
        for ...
    ],
    namespace="ns1",
    batch_size=100,
)

# Sparse upsert
sparse_idx = pc.Index(DEEN_FIQH_SPARSE_INDEX_NAME)
sparse_idx.upsert(
    vectors=[
        {
            "id": f"fiqh-{ruling_number}-{chunk_idx}",
            "sparse_values": {
                "indices": sparse_vec["indices"],
                "values": sparse_vec["values"],
            },
            "metadata": { ... same metadata ... }
        }
        for ...
    ],
    namespace="ns1",
    batch_size=100,
)
```

### Pattern 5: Config Extension
**What:** Add fiqh index env vars to `core/config.py`
**When to use:** Must be done before the script can use the config module

```python
# In core/config.py — add after existing index names:
DEEN_FIQH_DENSE_INDEX_NAME = os.getenv("DEEN_FIQH_DENSE_INDEX_NAME")
DEEN_FIQH_SPARSE_INDEX_NAME = os.getenv("DEEN_FIQH_SPARSE_INDEX_NAME")
```

Note: Do NOT add a ValueError guard on these during module import — the existing guards on `DEEN_DENSE_INDEX_NAME` would block the server from starting if fiqh env vars are absent. Guard inside the script only.

### Anti-Patterns to Avoid
- **Reusing `getSparseEmbedder()`:** Explicitly forbidden by D-04. TF-IDF is fit at query-time per request and cannot produce consistent sparse vectors across documents.
- **Using `hadith_id` as vector ID field:** D-13 forbids this. Use `fiqh-{ruling_number}-{chunk_idx}` format.
- **Storing BM25 as pickle:** BM25Encoder.dump() uses JSON (confirmed in source). JSON is portable and security-safe across Python versions.
- **Importing `core.config` without fiqh vars added first:** The config module raises ValueError on missing `DEEN_DENSE_INDEX_NAME` at import time — ensure fiqh vars are added before first config import.
- **Using `dimension` parameter when creating sparse index:** Pinecone 7.3.0 `create_index` accepts `dimension=None` (default) for sparse indexes — do not pass `dimension=768`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token counting | Manual word count | `tiktoken.get_encoding('cl100k_base').encode(text)` | Word count != tokens; OpenAI/HuggingFace models count differently |
| BM25 sparse encoding | Custom TF-IDF → sparse vector | `pinecone_text.sparse.BM25Encoder` | mmh3 hashing, consistent indices across fit/encode cycles, JSON persistence |
| PDF text extraction | Custom page parser | `fitz.open(path); page.get_text()` | Handles Unicode, ligatures, Arabic transliterations correctly |
| Secondary chunking | Manual paragraph split | `langchain_text_splitters.TokenTextSplitter` | Handles token boundaries correctly, already in requirements.txt |
| Dense embeddings | Direct `sentence_transformers` call | `getDenseEmbedder().embed_documents(texts)` | Reuses already-loaded model; avoids double-loading 420MB model |

**Key insight:** The ingestion script is batch-oriented and one-shot. Reusing project infrastructure (`getDenseEmbedder`, `Pinecone` from `core.vectorstore`) avoids duplicate initialization costs (the sentence-transformer model is 420MB and takes ~10s to load).

---

## Runtime State Inventory

> Omitted — this is a greenfield data ingestion phase with no existing runtime state to migrate.

---

## Common Pitfalls

### Pitfall 1: NLTK Data Not Downloaded
**What goes wrong:** `BM25Encoder()` instantiation raises `LookupError: Resource stopwords not found` even after `pip install pinecone-text`.
**Why it happens:** `pinecone-text` depends on NLTK but does not auto-download NLTK corpus data.
**How to avoid:** Add NLTK download calls at the top of the script, before `BM25Encoder()`:
```python
import nltk
nltk.download('stopwords', quiet=True)
nltk.download('punkt_tab', quiet=True)
```
**Warning signs:** `LookupError` mentioning `stopwords` or `punkt_tab` at startup.

### Pitfall 2: Sparse Index Created with `dimension` Parameter
**What goes wrong:** Pinecone raises an error when creating a sparse index if `dimension` is passed.
**Why it happens:** Sparse indexes have variable-length vectors; dimension is meaningless.
**How to avoid:** Omit `dimension` entirely when calling `create_index` with `vector_type="sparse"`.
**Warning signs:** `PineconeApiException` mentioning dimension validation during index creation.

### Pitfall 3: BM25 Encode Before Fit
**What goes wrong:** `ValueError: BM25 must be fit before encoding documents`.
**Why it happens:** `encode_documents()` or `encode_queries()` called before `fit()` on a fresh encoder.
**How to avoid:** Always call `encoder.fit(all_texts)` before any encode call. In the ingestion script, collect all chunk texts first, fit, then encode.
**Warning signs:** `ValueError: BM25 must be fit before encoding`.

### Pitfall 4: Regex Matches Ruling Numbers in Footnotes/Appendices
**What goes wrong:** The regex `Ruling\s+\d+` also matches references to rulings within parenthetical cross-references like "(see Ruling 712)" — producing phantom small chunks.
**Why it happens:** The PDF text contains inline cross-references to ruling numbers.
**How to avoid:** After splitting, filter out chunks with fewer than ~20 tokens. The actual ruling text always starts with "Ruling N." as a sentence opener, while cross-references are mid-sentence and produce negligible text fragments.
**Warning signs:** Chunks with < 20 tokens in the parsed output.

### Pitfall 5: Chapter/Section Metadata Not Propagated to All Chunks
**What goes wrong:** Some chunks have empty `chapter` or `section` metadata because the parser resets context at page boundaries rather than tracking state across the document.
**Why it happens:** Chapter headings appear once per chapter opener page; subsequent ruling pages within the same chapter carry no heading repeat.
**How to avoid:** Parse the document linearly top-to-bottom, tracking `current_chapter` and `current_section` state variables that persist across ruling boundaries.
**Warning signs:** Chunks where `chapter == ""` despite being mid-chapter content.

### Pitfall 6: Dense Embedding Batch Size Causing OOM
**What goes wrong:** Embedding all 1,400 chunks at once with `embed_documents()` may OOM on machines with limited RAM.
**Why it happens:** sentence-transformers loads all texts into memory simultaneously for batch encoding.
**How to avoid:** Embed in sub-batches of 32–64 texts. `HuggingFaceEmbeddings.embed_documents()` can handle this transparently if called with sub-batches.
**Warning signs:** Memory error or process killed during embedding phase.

### Pitfall 7: Pinecone Index Not Ready Before Upsert
**What goes wrong:** Upsert fails immediately after `create_index()` with "index not found".
**Why it happens:** Serverless index provisioning is async and takes a few seconds.
**How to avoid:** After `create_index()`, poll `pc.describe_index(name).status.ready` or use `time.sleep(5)` before upserting. The Pinecone SDK's `create_index` accepts a `timeout` parameter but defaults to returning immediately.
**Warning signs:** `NotFoundException` on first upsert after index creation.

---

## Code Examples

### PDF Extraction and Ruling Split
```python
# Source: PyMuPDF 1.27.2.2 API + confirmed against actual PDF
import fitz
import re

def load_pdf_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text() for page in doc)

# Ruling split: produces ["preamble...", "Ruling 1.", " body text ...", "Ruling 2.", " body text ...", ...]
RULING_PATTERN = re.compile(r'(Ruling\s+(\d+)\.)')
parts = RULING_PATTERN.split(full_text)
```

### BM25 Fit and Persist
```python
# Source: pinecone_text/sparse/bm25_encoder.py — confirmed API
from pinecone_text.sparse import BM25Encoder

encoder = BM25Encoder()
encoder.fit(chunk_texts)                          # list[str]
encoder.dump("data/fiqh_bm25_encoder.json")       # JSON, not pickle
```

### Pinecone Sparse Index Creation
```python
# Source: Pinecone SDK 7.3.0 — VectorType.SPARSE confirmed
pc.create_index(
    name=DEEN_FIQH_SPARSE_INDEX_NAME,
    metric="dotproduct",
    vector_type="sparse",          # no dimension= for sparse
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)
```

### Dense Embedding Reuse
```python
# Source: modules/embedding/embedder.py — existing project pattern
from modules.embedding.embedder import getDenseEmbedder

embedder = getDenseEmbedder()  # HuggingFaceEmbeddings, already-loaded model
dense_vecs = embedder.embed_documents(batch_of_texts)  # list[list[float]]
```

---

## Corpus Statistics (Verified Against Actual PDF)

| Statistic | Value |
|-----------|-------|
| PDF location | `documentation/fiqh_related_docs/english-islamic-laws-4th-edition.pdf` |
| Total pages | 533 |
| Total unique rulings | 2,796 (Ruling 1 through Ruling 2796, no gaps) |
| Total corpus tokens | ~396,047 |
| Rulings fitting in ≤300 tokens | 2,742 (95%) |
| Rulings 301–400 tokens | 55 |
| Rulings >400 tokens (need secondary split) | 82 (2%) |
| Estimated total chunks | ~1,100–1,400 |
| Dense vector dimensions | 768 (all-mpnet-base-v2) |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TF-IDF at query-time (existing embedder) | BM25 fit on corpus (pinecone-text) | D-04 decision | BM25 produces stable vocabulary-anchored indices; consistent between ingest and query |
| `pymupdf4llm` markdown conversion | Direct `fitz.page.get_text()` extraction | Deliberate choice | Simpler, no markdown noise, handles Unicode Arabic transliteration better |
| `hadith_id` metadata key | `ruling_number` + custom ID format | D-13 decision | Prevents confusion with hadith pipeline; fiqh retrieval in Phase 2 uses `ruling_number` |

**Deprecated/outdated:**
- `pymupdf4llm 0.0.17` (mentioned in STATE.md): Current latest is 1.27.2.2. The version numbering changed significantly. However, raw `pymupdf` (fitz) is preferred over pymupdf4llm for this use case.

---

## Open Questions

1. **Cloud/Region for new Pinecone indexes (D-09)**
   - What we know: D-09 says to use the same cloud/region as existing indexes. The `.env` is not readable.
   - What's unclear: The specific cloud/region values in the live Pinecone account.
   - Recommendation: The ingestion script should read the existing index metadata at startup to discover the cloud/region dynamically: `pc.describe_index(DEEN_DENSE_INDEX_NAME).spec.serverless.cloud` and `.region`. Fallback to `aws/us-east-1` as the most common Pinecone serverless region.

2. **Chunk overlap strategy (Claude's Discretion)**
   - What we know: 95% of rulings are self-contained, atomic units of fiqh law. Overlap between adjacent rulings has no semantic benefit.
   - What's unclear: Whether oversized rulings split via paragraph boundaries should have overlap.
   - Recommendation: Zero overlap. Each ruling is a complete legal ruling; overlap would duplicate ruling text across chunks without retrieval benefit and increase index size.

3. **Topic tag assignment strategy (INGE-03)**
   - What we know: Required tags include tahara, salah, sawm, hajj, khums. Chapter headings map directly to topics.
   - What's unclear: Sub-chapter granularity (e.g., whether "ablution" should be tagged separately from "tahara").
   - Recommendation: Assign topic tags from chapter name using a lookup dict mapping chapter number/name to canonical tag. One tag per chunk is sufficient for Phase 1; multi-tag assignment is a v2 concern.

4. **BM25 encoder persistence location (Claude's Discretion)**
   - Recommendation: `data/fiqh_bm25_encoder.json`. Create the `data/` directory if absent. Add `data/*.json` to `.gitignore` since the encoder is derived from the PDF and can be regenerated. The JSON is ~50–200 KB (document frequency map for ~1,400 chunks).

5. **Batch size for Pinecone upsert (Claude's Discretion)**
   - Recommendation: 100 vectors per batch for both dense and sparse indexes. This is well within Pinecone's 2MB request limit and avoids timeout issues with large metadata payloads.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | All code | ✓ | 3.11.4 | — |
| pinecone SDK | Index creation + upsert | ✓ (venv) | 7.3.0 | — |
| sentence-transformers | Dense embeddings | ✓ (venv) | 3.4.1 | — |
| tiktoken | Token counting | ✓ (venv) | 0.9.0 | — |
| langchain-text-splitters | Secondary chunking | ✓ (venv) | 0.3.9 | — |
| pymupdf (fitz) | PDF parsing | ✗ (not in venv) | 1.27.2.2 available | None — must install |
| pinecone-text | BM25Encoder | ✗ (not in venv) | 0.11.0 available | None — locked by D-03 |
| NLTK stopwords/punkt_tab | BM25Encoder init | ✗ (not downloaded) | n/a | None — auto-downloadable |
| Pinecone API key + indexes | Index operations | ✓ (in .env) | — | — |

**Missing dependencies with no fallback:**
- `pymupdf==1.27.2.2` — must be added to `requirements.txt` and installed
- `pinecone-text==0.11.0` — must be added to `requirements.txt` and installed

**Missing dependencies with fallback:**
- NLTK data — downloadable at script startup via `nltk.download()`; no manual step needed if network is available

---

## Sources

### Primary (HIGH confidence)
- PyMuPDF 1.27.2.2 — confirmed via `pip3 index versions pymupdf` (2026-03-23)
- pinecone-text 0.11.0 — confirmed via `pip3 index versions pinecone-text` (2026-03-23)
- `pinecone_text/sparse/bm25_encoder.py` — read source directly; confirmed `fit`, `encode_documents`, `encode_queries`, `dump`, `load` API
- `pinecone.db_control.enums.VectorType` — confirmed `DENSE` and `SPARSE` values via venv inspection
- `pinecone.db_data.dataclasses.Vector`, `SparseValues` — confirmed signatures via `inspect.signature`
- Actual PDF `english-islamic-laws-4th-edition.pdf` — directly opened with PyMuPDF; 533 pages, 2796 unique rulings confirmed
- `core/config.py`, `core/vectorstore.py`, `modules/embedding/embedder.py`, `modules/retrieval/retriever.py`, `scripts/generate_primers.py` — all read directly

### Secondary (MEDIUM confidence)
- Pinecone serverless `ServerlessSpec(cloud, region)` — confirmed via venv import inspection; cloud/region values for existing indexes not verified (`.env` unreadable)

### Tertiary (LOW confidence)
- Pinecone index provisioning delay requiring a wait after `create_index` — standard pattern; specific timeout not confirmed against Pinecone docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages version-verified against PyPI; BM25 API confirmed from source
- Architecture: HIGH — PDF structure confirmed against actual document; Pinecone SDK API confirmed from venv inspection
- Pitfalls: HIGH for NLTK/dimension/fit-order pitfalls (confirmed from source); MEDIUM for metadata propagation and OOM (inferred from corpus structure)

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable ecosystem; Pinecone API changes infrequently)
