---
phase: 01-data-foundation
plan: "01"
subsystem: infra
tags: [pinecone, pymupdf, bm25, sparse-encoding, requirements, config, gitignore]

# Dependency graph
requires: []
provides:
  - pymupdf==1.27.2.2 pinned in requirements.txt for PDF parsing
  - pinecone-text==0.11.0 pinned in requirements.txt for BM25 sparse encoding
  - DEEN_FIQH_DENSE_INDEX_NAME exported from core/config.py via os.getenv
  - DEEN_FIQH_SPARSE_INDEX_NAME exported from core/config.py via os.getenv
  - data/ directory tracked in git with .gitkeep
  - data/*.json excluded from version control via .gitignore
affects:
  - 01-02 (ingestion script imports core.config fiqh vars and uses pymupdf/pinecone-text)
  - 01-03 (ingestion script uses these same vars and packages)
  - all fiqh retrieval phases that import DEEN_FIQH_DENSE_INDEX_NAME or DEEN_FIQH_SPARSE_INDEX_NAME

# Tech tracking
tech-stack:
  added:
    - pymupdf==1.27.2.2 (PDF parsing for fiqh book ingestion)
    - pinecone-text==0.11.0 (BM25Encoder for sparse index creation)
  patterns:
    - Fiqh index env vars follow same os.getenv() pattern as existing index vars in core/config.py
    - No module-level ValueError guard on optional feature env vars (guard lives in the consuming script)

key-files:
  created:
    - data/.gitkeep
  modified:
    - requirements.txt
    - core/config.py
    - .gitignore

key-decisions:
  - "No module-level ValueError guard for DEEN_FIQH_DENSE/SPARSE_INDEX_NAME — prevents server startup breakage for developers who haven't set up fiqh indexes yet"
  - "pymupdf==1.27.2.2 and pinecone-text==0.11.0 pinned at exact versions confirmed by research on 2026-03-23"
  - "data/*.json gitignored (BM25 encoder is reproducible generated artifact, not source of truth)"

patterns-established:
  - "Optional feature env vars: exported via os.getenv() without module-level guard; consuming script validates"

requirements-completed: [INGE-04, INGE-05, INGE-06]

# Metrics
duration: 2min
completed: 2026-03-24
---

# Phase 01 Plan 01: Dependencies and Config Bootstrapping Summary

**pymupdf and pinecone-text pinned in requirements.txt, fiqh Pinecone index env vars exported from core/config.py, and data/ directory scaffolded with BM25 encoder gitignored**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-24T01:40:05Z
- **Completed:** 2026-03-24T01:41:11Z
- **Tasks:** 3
- **Files modified:** 4 (requirements.txt, core/config.py, .gitignore, data/.gitkeep created)

## Accomplishments

- Pinned `pymupdf==1.27.2.2` and `pinecone-text==0.11.0` in requirements.txt in correct alphabetical positions
- Added `DEEN_FIQH_DENSE_INDEX_NAME` and `DEEN_FIQH_SPARSE_INDEX_NAME` to `core/config.py` immediately after the existing `QURAN_DENSE_INDEX_NAME` line, with no module-level ValueError guard
- Created `data/` directory with `.gitkeep` and added `data/*.json` to `.gitignore` so the BM25 encoder output is not committed

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pymupdf and pinecone-text to requirements.txt** - `203c451` (chore)
2. **Task 2: Register fiqh index env vars in core/config.py** - `2bf126e` (feat)
3. **Task 3: Add .gitignore entry for BM25 encoder JSON and create data/ directory placeholder** - `b38f879` (chore)

## Files Created/Modified

- `requirements.txt` - added `pinecone-text==0.11.0` (line 68) and `pymupdf==1.27.2.2` (line 76) in alphabetical order
- `core/config.py` - added `DEEN_FIQH_DENSE_INDEX_NAME` and `DEEN_FIQH_SPARSE_INDEX_NAME` after `QURAN_DENSE_INDEX_NAME`
- `.gitignore` - added `data/*.json` exclusion with comment
- `data/.gitkeep` - empty placeholder to track the directory in git

## Decisions Made

- No module-level ValueError guard on fiqh index vars: the existing guard already blocks startup if `DEEN_DENSE_INDEX_NAME` or `DEEN_SPARSE_INDEX_NAME` are unset. Adding a fiqh guard would break startup for developers who haven't yet configured fiqh indexes. The ingestion script will guard these values itself.
- Exact version pins (not `>=` constraints) following the project's existing lockfile pattern in requirements.txt.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

Two new environment variables are needed by the ingestion script (plans 01-02 and 01-03):

```
DEEN_FIQH_DENSE_INDEX_NAME=<your-fiqh-dense-pinecone-index>
DEEN_FIQH_SPARSE_INDEX_NAME=<your-fiqh-sparse-pinecone-index>
```

These vars are optional for normal server operation — the server starts without them. They are only required when running the fiqh ingestion script.

## Next Phase Readiness

- Plans 01-02 and 01-03 (ingestion script) can now be implemented: `pymupdf` and `pinecone-text` are available, and `core/config.py` exports the fiqh index names they need.
- The `data/` directory exists and is ready to receive the BM25 encoder JSON artifact.
- No blockers for next plans.

## Self-Check: PASSED

- FOUND: requirements.txt (contains pymupdf==1.27.2.2 and pinecone-text==0.11.0)
- FOUND: core/config.py (exports DEEN_FIQH_DENSE_INDEX_NAME and DEEN_FIQH_SPARSE_INDEX_NAME)
- FOUND: .gitignore (contains data/*.json rule)
- FOUND: data/.gitkeep
- FOUND: .planning/phases/01-data-foundation/01-01-SUMMARY.md
- COMMIT 203c451: chore(01-01): add pymupdf and pinecone-text to requirements.txt
- COMMIT 2bf126e: feat(01-01): register fiqh Pinecone index env vars in core/config.py
- COMMIT b38f879: chore(01-01): add data/ directory and gitignore BM25 encoder JSON

---
*Phase: 01-data-foundation*
*Completed: 2026-03-24*
