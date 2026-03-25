---
phase: 01-data-foundation
plan: "02"
subsystem: infra
tags: [pymupdf, tiktoken, langchain-text-splitters, fiqh, pdf-parsing, chunking, bm25]

# Dependency graph
requires:
  - phase: 01-data-foundation-01
    provides: pymupdf and pinecone-text in requirements.txt; DEEN_FIQH_DENSE/SPARSE_INDEX_NAME in core/config.py
provides:
  - scripts/ingest_fiqh.py with parse_pdf(), chunk_rulings(), assign_topic_tag() functions
  - Ruling-boundary chunking with chapter/section/topic metadata on every chunk
  - --dry-run CLI mode for validation without Pinecone calls
  - _run_ingestion() stub ready for plan 03 embedding/upsert implementation
affects:
  - 01-03 (implements _run_ingestion() and BM25 encoding over chunks produced here)
  - all fiqh retrieval phases (use chunk metadata schema: id, text, source_book, chapter, section, ruling_number, topic_tags)

# Tech tracking
tech-stack:
  added:
    - fitz (pymupdf 1.27.2.2) — PDF text extraction
    - tiktoken cl100k_base — token counting for chunk size enforcement
    - langchain_text_splitters.TokenTextSplitter — secondary splitting for rulings >400 tokens
  patterns:
    - Ruling-boundary splitting: re.split(RULING_PATTERN, full_text) with stride-3 iteration over parts
    - Chapter/section state: position map built in single full-text scan; O(n) lookup per ruling
    - Duplicate ruling deduplication: seen_ruling_numbers set filters cross-reference phantom matches
    - Phantom chunk filter: MIN_CHUNK_TOKENS=20 token minimum per output chunk
    - Vector ID format: "fiqh-{ruling_number}-{chunk_idx}" (e.g. "fiqh-712-0")

key-files:
  created:
    - scripts/ingest_fiqh.py
    - tests/test_ingest_fiqh.py
  modified:
    - core/config.py (added DEEN_FIQH_DENSE_INDEX_NAME, DEEN_FIQH_SPARSE_INDEX_NAME)
    - requirements.txt (added pymupdf==1.27.2.2, pinecone-text==0.11.0)

key-decisions:
  - "Deduplicate ruling numbers by tracking seen_ruling_numbers set — PDF contains inline cross-references that match RULING_PATTERN and would produce duplicate chunk entries without this guard"
  - "Updated chunk count expectation from plan's 1000-1600 to 2700-3500: research underestimated; 2796 valid rulings each produce ~1 chunk, not merged"
  - "Zero chunk overlap: each ruling is a self-contained legal ruling; overlap between adjacent rulings has no retrieval benefit"

patterns-established:
  - "Chunk dict schema: id, text, source_book, chapter, section, ruling_number, topic_tags — all downstream fiqh code must use this schema"
  - "Position-map chapter tracking: scan full_text once for CHAPTER_PATTERN positions, then lookup by character offset per ruling"

requirements-completed: [INGE-01, INGE-02, INGE-03]

# Metrics
duration: 6min
completed: 2026-03-24
---

# Phase 01 Plan 02: PDF Parsing and Chunking Layer Summary

**PyMuPDF-based PDF parsing with ruling-boundary chunking producing 3000 structured chunks from 2796 Sistani rulings, with chapter/section/topic metadata on every chunk**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-24T01:41:07Z
- **Completed:** 2026-03-24T01:47:09Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 4

## Accomplishments

- Implemented `parse_pdf()` extracting 533 pages of text via PyMuPDF's `fitz.open()` + `page.get_text()`
- Implemented `chunk_rulings()` splitting at `Ruling N.` boundaries with chapter/section state propagation across ruling boundaries
- Secondary splitting via `TokenTextSplitter(chunk_size=350)` for the 78 rulings exceeding 400 tokens
- Phantom chunk filter: deduplicates regex matches for inline cross-references and filters chunks < 20 tokens
- `assign_topic_tag()` maps CHAPTER ONE–TWELVE to canonical tags (taqlid, tahara, salah, etc.)
- `--dry-run` mode logs ruling count, first 5 chunks with metadata, exits 0 without calling embedder or Pinecone
- 24 unit + integration tests covering all behaviors (synthetic text and real PDF)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: failing tests** - `540d8f7` (test)
2. **Task 1 GREEN: implementation** - `36d88e6` (feat)

## Files Created/Modified

- `scripts/ingest_fiqh.py` — parse_pdf(), chunk_rulings(), assign_topic_tag(), _run_ingestion() stub, CLI entry point
- `tests/test_ingest_fiqh.py` — 24 tests covering parse_pdf, chunk_rulings, assign_topic_tag, RULING_PATTERN, real PDF integration
- `core/config.py` — added DEEN_FIQH_DENSE_INDEX_NAME and DEEN_FIQH_SPARSE_INDEX_NAME
- `requirements.txt` — added pymupdf==1.27.2.2 and pinecone-text==0.11.0

## Decisions Made

- **Ruling deduplication via seen_ruling_numbers set**: The PDF contains inline cross-references like "(see Ruling 712.)" that match `RULING_PATTERN`. Without deduplication, 83 phantom duplicates were produced (ruling numbers 2–318 each appearing twice). Fix: skip any ruling number already seen — only process first occurrence.
- **Updated chunk count expectation**: Research estimated 1000-1600 chunks; actual data shows 2796 rulings each producing ~1 chunk = ~3000 total. The research incorrectly assumed many rulings would be merged — the regex-based approach correctly keeps each ruling separate.
- **Zero overlap**: Each ruling is a self-contained atomic legal ruling; overlap between adjacent rulings has no semantic retrieval benefit and would inflate the index.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Deduplicate ruling numbers to prevent phantom chunks from inline cross-references**
- **Found during:** Task 1 (GREEN phase, running full dry-run verification)
- **Issue:** RULING_PATTERN matched 2879 positions instead of 2796 because the PDF contains 83 inline cross-references formatted as "Ruling N." (e.g. "(see Ruling 712.)") that produce duplicate entries with substantial body text (not just tiny phantom fragments filtered by MIN_CHUNK_TOKENS)
- **Fix:** Added `seen_ruling_numbers: set[int]` tracking in `chunk_rulings()` — skip any ruling number already processed; only keep first occurrence
- **Files modified:** scripts/ingest_fiqh.py
- **Verification:** Chunk count dropped from 3066 to 3000; `last_ruling_number` in log correctly shows 2796
- **Committed in:** 36d88e6 (Task 1 GREEN commit)

**2. [Rule 1 - Bug] Updated test chunk count expectation from 1000-1600 to 2700-3500**
- **Found during:** Task 1 (GREEN phase — integration test failure)
- **Issue:** Test asserted 1000-1600 chunks based on research estimate; actual data produces ~3000 because each of the 2796 rulings gets its own chunk (not merged as research assumed)
- **Fix:** Updated test to expect 2700-3500 chunks with explanatory comment
- **Files modified:** tests/test_ingest_fiqh.py
- **Verification:** All 24 tests pass
- **Committed in:** 36d88e6 (Task 1 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — Bug)
**Impact on plan:** Both fixes correct incorrect research assumptions. No scope creep. Core behavior (parsing, chunking, metadata, filtering) matches plan specification exactly.

## Issues Encountered

- Research underestimated chunk count (1000-1600 estimate vs ~3000 actual) — root cause: research assumed many rulings would be merged, but the ruling-boundary split produces one chunk per ruling for the ~95% of rulings under 400 tokens
- 83 inline cross-references in the PDF match RULING_PATTERN — resolved by deduplication rather than more complex regex (simpler and more robust)

## User Setup Required

None beyond what plan 01-01 documented (DEEN_FIQH_DENSE_INDEX_NAME and DEEN_FIQH_SPARSE_INDEX_NAME env vars). The `--dry-run` mode works without any env vars or external services.

## Next Phase Readiness

- `scripts/ingest_fiqh.py` is ready for plan 03 to implement `_run_ingestion()`: embed chunks with `getDenseEmbedder()`, fit BM25Encoder on all chunk texts, upsert to both fiqh Pinecone indexes
- Chunk schema is fixed: `{id, text, source_book, chapter, section, ruling_number, topic_tags}`
- 3000 chunks ready for embedding — embedding batch size of 32-64 recommended to avoid OOM (Pitfall 6 from research)
- `data/` directory exists for BM25 encoder persistence

## Self-Check: PASSED

- FOUND: scripts/ingest_fiqh.py
- FOUND: tests/test_ingest_fiqh.py
- FOUND: .planning/phases/01-data-foundation/01-02-SUMMARY.md
- FOUND commit 540d8f7: test(01-02): add failing tests for PDF parsing and chunking layer
- FOUND commit 36d88e6: feat(01-02): implement PDF parsing and chunking layer for fiqh ingestion

---
*Phase: 01-data-foundation*
*Completed: 2026-03-24*
