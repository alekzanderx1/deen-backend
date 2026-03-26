# Phase 2: Routing and Retrieval - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 02-routing-and-retrieval
**Areas discussed:** Classifier isolation, Fiqh code org, Sub-query contract, RRF placement

---

## Classifier Isolation

| Option | Description | Selected |
|--------|-------------|----------|
| New fiqh_classifier.py | Add modules/fiqh/classifier.py — zero risk to existing pipeline; hadith flow still calls classifier.py | ✓ |
| Extend classifier.py | Add classify_fiqh_category() alongside existing functions in classifier.py | |

**User's choice:** New fiqh_classifier.py — isolated new file, no changes to existing classifier.py

| Option | Description | Selected |
|--------|-------------|----------|
| New fiqh_category field | Add fiqh_category: str to ChatState alongside is_fiqh: bool | ✓ |
| Replace is_fiqh with category | Remove is_fiqh, update routing logic now | |

**User's choice:** Add fiqh_category: str alongside existing is_fiqh: bool — zero breakage to current behavior

---

## Fiqh Code Org

| Option | Description | Selected |
|--------|-------------|----------|
| New modules/fiqh/ package | classifier.py, decomposer.py, retriever.py in one place — clean isolation | ✓ |
| Extend existing dirs | fiqh files spread across classification/, retrieval/, enhancement/ | |

**User's choice:** New modules/fiqh/ package — all fiqh pipeline code isolated in one directory

---

## Sub-query Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Flat deduplicated list | retrieve_fiqh_documents() returns a flat list of ~20 unique docs merged across sub-queries | ✓ |
| Per-sub-query dict | Returns {sub_query: [docs]} — preserves which docs came from which sub-query | |

**User's choice:** Flat deduplicated list — simpler interface for Phase 3's evidence filter

---

## RRF Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in modules/fiqh/retriever.py | RRF is ~10-15 lines; keeps fiqh package self-contained | ✓ |
| New modules/fiqh/reranker.py | Separate fiqh reranker file within the fiqh package | |
| Add rrf_merge() to existing reranker.py | Extend existing file (already 200+ lines, wrong algorithm/ID field) | |

**User's choice:** Inline in modules/fiqh/retriever.py — self-contained, no changes to existing reranker.py

---

## Claude's Discretion

- Exact prompt templates for the 6-category classifier and decomposer
- Maximum doc count in flat deduplicated list
- How decomposer handles single-part queries
- Pinecone namespace for fiqh queries

## Deferred Ideas

None raised during discussion.
