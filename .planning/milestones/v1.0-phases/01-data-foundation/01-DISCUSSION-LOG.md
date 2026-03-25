# Phase 1: Data Foundation - Discussion Log

**Session:** 2026-03-23
**Areas discussed:** PDF source & ruling format, Pinecone index configuration, Ingestion idempotency

---

## Area 1: PDF Availability & Ruling Format

**Q: Do you have Sistani's "Islamic Laws" (4th edition) PDF, and where does it live?**
Selected: Yes, in the repo — PDF already committed or sitting in the project directory

**Q: How are ruling numbers formatted in the actual PDF?**
Selected/typed: "They are written as: 'Ruling 1', 'Ruling 2', etc..."
→ Chunking regex anchors on `Ruling\s+\d+`

---

## Area 3: Pinecone Fiqh Indexes

**Configuration guidance provided:**
- Dense: 768 dimensions, cosine metric, serverless (matches all-mpnet-base-v2)
- Sparse: Sparse type, dotproduct metric, serverless (no fixed dimension for BM25)

**Q: What will you name the two fiqh Pinecone indexes?**
Selected: deen-fiqh-dense / deen-fiqh-sparse

**Follow-up (user-initiated):** User asked for full console configuration details for both indexes.
Guidance given: Dense = 768 dim + cosine; Sparse = Sparse type + dotproduct. Same cloud/region as existing indexes.

**User action:** Created both indexes and added env vars as `DEEN_FIQH_DENSE_INDEX_NAME` and `DEEN_FIQH_SPARSE_INDEX_NAME` in `.env`.
(Note: env var prefix uses `DEEN_FIQH_` not `FIQH_` as initially suggested.)

---

## Area 4: Ingestion Idempotency

**Q: Should the ingestion script support re-runs, or is one-shot acceptable?**
Selected: Re-runnable with upsert — script uses Pinecone upsert so re-running is safe

**Q: What kind of progress output do you want during ingestion?**
Selected: Batch-level logs — e.g. "Uploaded 200/1400 chunks"

---

## Area 2: Sparse Encoder (not selected for discussion)

Not discussed by user choice. Decision falls to requirements spec: INGE-05 mandates `pinecone-text` BM25Encoder. Recorded as D-03/D-04 in CONTEXT.md.
