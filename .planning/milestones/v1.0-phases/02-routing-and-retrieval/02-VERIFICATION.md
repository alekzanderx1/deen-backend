---
phase: 02-routing-and-retrieval
verified: 2026-03-24T00:00:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 2: Routing and Retrieval Verification Report

**Phase Goal:** Build the fiqh query routing and retrieval layer — classify queries into 6 categories, decompose complex queries into sub-queries, and retrieve relevant Sistani rulings from Pinecone using hybrid dense+sparse search with RRF merging.
**Verified:** 2026-03-24
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `classify_fiqh_query(query)` returns exactly one of the 6 category strings for any input | VERIFIED | `classifier.py` validates against `VALID_CATEGORIES` set; fallback is `OUT_OF_SCOPE_FIQH` |
| 2 | VALID_OBVIOUS, VALID_SMALL, VALID_LARGE, VALID_REASONER, OUT_OF_SCOPE_FIQH, UNETHICAL are the only possible return values | VERIFIED | `VALID_CATEGORIES` set defined at module level with all 6; any other string falls through to `OUT_OF_SCOPE_FIQH` |
| 3 | OUT_OF_SCOPE_FIQH is returned (not raised) on any unexpected LLM output | VERIFIED | `except Exception: return "OUT_OF_SCOPE_FIQH"` block in `classify_fiqh_query`; confirmed by `test_never_raises` and `test_returns_out_of_scope_on_exception` passing |
| 4 | gpt-4o-mini is used via `get_classifier_model()` — not gpt-4.1 | VERIFIED | `classifier.py` and `decomposer.py` both call `chat_models.get_classifier_model()`; no hardcoded model name; `core/chat_models.py` maps this to `SMALL_LLM` (gpt-4o-mini) |
| 5 | ChatState carries a `fiqh_category` field initialized to empty string, alongside existing `is_fiqh` | VERIFIED | `chat_state.py` line 52: `fiqh_category: str`; `create_initial_state()` line 157: `fiqh_category=""`; `is_fiqh=None` still present at line 49 |
| 6 | `modules/fiqh/__init__.py` exists — package is importable | VERIFIED | File exists (1 line, empty — Python package marker) |
| 7 | `decompose_query(query)` returns a list of 1-4 strings for any input | VERIFIED | `decomposer.py` caps at `sub_queries[:4]`; fallback is `[query]`; confirmed by all 8 decomposer test functions passing |
| 8 | `decompose_query` returns `[query]` as fallback when JSON parse fails | VERIFIED | `except Exception: return [query]` block; validated by `test_fallback_to_original_query_on_json_parse_error`, `test_fallback_on_empty_list_from_llm`, `test_fallback_on_exception` |
| 9 | Sub-queries include domain-specific fiqh terminology per QPRO-02 | VERIFIED | System prompt in `decomposer.py` explicitly requires Arabic/Persian fiqh terms (wudu, ghusl, salah, tahara, etc.); example outputs demonstrate this |
| 10 | `retrieve_fiqh_documents(query)` returns a list[dict] of up to 20 unique docs with RRF merge | VERIFIED | `result[:20]` cap in `retrieve_fiqh_documents`; `_rrf_merge` with k=60; deduplication via `seen` set; confirmed by all 10 retriever tests passing |
| 11 | BM25Encoder used for sparse encoding; `sparse_vector=` param used (not `vector=`) | VERIFIED | `retriever.py` line 19: `from pinecone_text.sparse import BM25Encoder`; line 123: `sparse_vector=sparse_vec`; no `getSparseEmbedder` usage |
| 12 | BM25 encoder path resolved relative to module file (not process cwd) | VERIFIED | `retriever.py` line 29: `BM25_ENCODER_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "fiqh_bm25_encoder.json"` |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `modules/fiqh/__init__.py` | fiqh package root | VERIFIED | Exists, empty (Python package marker) |
| `modules/fiqh/classifier.py` | `classify_fiqh_query(query: str) -> str`, exports `VALID_CATEGORIES` | VERIFIED | 68 lines, substantive implementation; both symbols importable |
| `modules/fiqh/decomposer.py` | `decompose_query(query: str) -> list[str]` | VERIFIED | 72 lines, substantive; uses `get_classifier_model()`, JSON fence stripping present |
| `modules/fiqh/retriever.py` | `retrieve_fiqh_documents(query: str) -> list[dict]` | VERIFIED | 169 lines, substantive; all 4 functions defined: `retrieve_fiqh_documents`, `_rrf_merge`, `_retrieve_for_sub_query`, `_get_bm25_encoder` |
| `agents/state/chat_state.py` | `fiqh_category` field on ChatState | VERIFIED | `fiqh_category: str` at line 52; `fiqh_category=""` in `create_initial_state()` at line 157; `is_fiqh` unchanged |
| `tests/test_fiqh_classifier.py` | Unit tests with mocked LLM | VERIFIED | 6 test functions, 13 pytest nodes (parametrize expands to 8 cases); all pass |
| `tests/test_fiqh_decomposer.py` | Unit tests with mocked LLM | VERIFIED | 8 test functions; all pass |
| `tests/test_fiqh_retriever.py` | Unit tests for RRF merge and retrieval with mocked Pinecone | VERIFIED | 10 test functions; all pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `modules/fiqh/classifier.py` | `core.chat_models.get_classifier_model()` | direct import call | WIRED | `from core import chat_models`; `chat_models.get_classifier_model()` called in `classify_fiqh_query` |
| `agents/state/chat_state.py` | `fiqh_category` | TypedDict field + create_initial_state default | WIRED | Field declared at line 52; initialized at line 157 in `create_initial_state()` |
| `modules/fiqh/decomposer.py` | `core.chat_models.get_classifier_model()` | direct import call | WIRED | `from core import chat_models`; `chat_models.get_classifier_model()` called in `decompose_query` |
| `tests/test_fiqh_classifier.py` | `modules/fiqh/classifier.classify_fiqh_query` | `unittest.mock.patch` | WIRED | `patch("modules.fiqh.classifier.chat_models.get_classifier_model", ...)` in every test |
| `modules/fiqh/retriever.py` | `modules/fiqh/decomposer.decompose_query` | import call at top of `retrieve_fiqh_documents` | WIRED | `from modules.fiqh.decomposer import decompose_query`; called at line 157 |
| `modules/fiqh/retriever.py` | `core.vectorstore._get_sparse_vectorstore` | raw index query for BOTH dense and sparse | WIRED | `from core.vectorstore import _get_sparse_vectorstore`; used at lines 108 and 121 |
| `modules/fiqh/retriever.py` | `data/fiqh_bm25_encoder.json` | `BM25Encoder().load(BM25_ENCODER_PATH)` | WIRED | `BM25_ENCODER_PATH` resolved via `Path(__file__).resolve()`; loaded in `_get_bm25_encoder()` |

---

### Data-Flow Trace (Level 4)

The fiqh modules are retrieval/classification utilities — not UI-rendering components. They do not render dynamic data to a user interface. Data flow is verified through the unit test suite with mocked external dependencies (LLM, Pinecone). Level 4 data-flow tracing is not applicable here.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All fiqh modules importable together | `python -c "from modules.fiqh.classifier import classify_fiqh_query, VALID_CATEGORIES; from modules.fiqh.decomposer import decompose_query; from modules.fiqh.retriever import retrieve_fiqh_documents, _rrf_merge; print('ok')"` | Prints "ok", exits 0 | PASS |
| ChatState backward compatibility | `python -c "from agents.state.chat_state import create_initial_state; s = create_initial_state('q', 's'); assert s['fiqh_category'] == ''; assert s['is_fiqh'] is None; assert s['classification_checked'] == False; print('ok')"` | Prints "ok", exits 0 | PASS |
| VALID_CATEGORIES has exactly 6 entries | `python -c "from modules.fiqh.classifier import VALID_CATEGORIES; print(len(VALID_CATEGORIES))"` | Prints "6" | PASS |
| All 31 Phase 2 tests pass | `pytest tests/test_fiqh_classifier.py tests/test_fiqh_decomposer.py tests/test_fiqh_retriever.py -v` | 31 passed in 3.08s | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CLAS-01 | 02-01-PLAN | System classifies queries into exactly 6 categories | SATISFIED | `VALID_CATEGORIES` set with 6 strings; `classify_fiqh_query` returns exactly one |
| CLAS-02 | 02-01-PLAN | OUT_OF_SCOPE_FIQH queries politely rejected before retrieval | SATISFIED | Function returns `OUT_OF_SCOPE_FIQH` as safe fallback; calling code (Phase 4) will handle rejection messaging |
| CLAS-03 | 02-01-PLAN | UNETHICAL queries immediately rejected | SATISFIED | `UNETHICAL` is a valid return value; downstream routing (Phase 4) handles the rejection |
| CLAS-04 | 02-01-PLAN | Classification uses gpt-4o-mini for cost efficiency | SATISFIED | `classify_fiqh_query` calls `get_classifier_model()` which maps to `SMALL_LLM` |
| CLAS-05 | 02-01-PLAN | Negative rejection accuracy >95% | NEEDS HUMAN | Cannot verify accuracy targets statically; requires live testing with a benchmark dataset |
| QPRO-01 | 02-02-PLAN | Complex queries decomposed into 1-4 keyword-rich sub-queries | SATISFIED | `decompose_query` returns `list[str]` capped at 4, falls back to `[query]` |
| QPRO-02 | 02-02-PLAN | Sub-queries include domain-specific fiqh terminology | SATISFIED | System prompt mandates Arabic/Persian transliterated terms; examples demonstrate terminology inclusion |
| QPRO-03 | 02-02-PLAN | Query decomposition uses gpt-4o-mini | SATISFIED | `decompose_query` calls `get_classifier_model()` (SMALL_LLM) |
| RETR-01 | 02-03-PLAN | Hybrid retrieval (dense + sparse) from dedicated fiqh indexes | SATISFIED | `_retrieve_for_sub_query` performs both dense (`vector=`) and sparse (`sparse_vector=`) queries against separate indexes |
| RETR-02 | 02-03-PLAN | Dense and sparse results merged via RRF (k=60) | SATISFIED | `_rrf_merge(dense_matches, sparse_matches, k=60, top_n=5)` called in `_retrieve_for_sub_query` |
| RETR-03 | 02-03-PLAN | Top-5 documents per sub-query retained after RRF | SATISFIED | `_rrf_merge(..., top_n=5)` explicitly limits to 5 per sub-query |
| RETR-04 | 02-03-PLAN | Retrieved documents include source metadata (book, chapter, section, ruling number) | SATISFIED | Each returned doc has `metadata` dict; Pinecone metadata schema includes `source_book`, `chapter`, `section`, `ruling_number`; tested in `test_metadata_includes_required_fields` |

**Note on CLAS-02 and CLAS-03:** These requirements concern runtime routing behavior (rejecting queries before retrieval runs). The classifier correctly returns `OUT_OF_SCOPE_FIQH` and `UNETHICAL` values. The actual rejection message and early-exit logic are a Phase 4 integration concern (`INTG-02`). The classifier's side of the contract is complete.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No anti-patterns found. All three implementation files have substantive logic with no TODO/FIXME comments, no placeholder returns, and no hardcoded empty data in rendering paths.

---

### Human Verification Required

#### 1. CLAS-05 Accuracy Target

**Test:** Run the classifier against a benchmark set of 50-100 fiqh/non-fiqh queries and measure rejection accuracy.
**Expected:** >95% correct rejection of OUT_OF_SCOPE_FIQH and UNETHICAL queries.
**Why human:** Cannot verify an accuracy percentage threshold through static code analysis. Requires a live LLM call with a labeled dataset.

#### 2. QPRO-02 Terminology Quality

**Test:** Submit 5-10 complex fiqh queries to `decompose_query` with a real OpenAI key and inspect the sub-queries returned.
**Expected:** Each sub-query contains relevant Arabic/Persian fiqh terminology naturally (not fabricated).
**Why human:** The system prompt instructs terminology inclusion, but LLM output quality is non-deterministic and requires human judgment.

#### 3. BM25 Encoder File Presence at Runtime

**Test:** Confirm `data/fiqh_bm25_encoder.json` exists in the deployed environment (created in Phase 1).
**Expected:** File exists at the path resolved by `Path(__file__).resolve().parent.parent.parent / "data" / "fiqh_bm25_encoder.json"`.
**Why human:** The file is a runtime artifact from Phase 1 ingestion. It was not checked into git and its presence depends on the Phase 1 deployment having run. Cannot verify this statically in the codebase.

---

### Gaps Summary

No gaps. All automated checks pass cleanly.

The phase delivered all three core modules (`classifier.py`, `decomposer.py`, `retriever.py`) with substantive, wired implementations. The test suite (31 tests across 3 files) validates the critical algorithmic behaviors — RRF merge correctness, fallback safety, deduplication, and 20-doc cap — without requiring live API access. ChatState was correctly extended with `fiqh_category` without breaking existing fields.

The three human-verification items are quality/accuracy thresholds and a runtime file check — none of them block the goal from being achieved.

---

_Verified: 2026-03-24_
_Verifier: Claude (gsd-verifier)_
