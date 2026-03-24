"""
modules/fiqh/fair_rag.py

FAIR-RAG coordinator for the Islamic Laws question-answering pipeline.

Implements the max-3-iteration retrieve -> filter -> assess -> refine loop.
This is the Phase 4 integration point — Phase 4 imports and calls run_fair_rag(query).

Public interface: run_fair_rag(query: str) -> str
"""
from __future__ import annotations
import logging

from modules.fiqh.filter import filter_evidence
from modules.fiqh.generator import generate_answer
from modules.fiqh.refiner import refine_query
from modules.fiqh.retriever import retrieve_fiqh_documents
from modules.fiqh.sea import SEAResult, assess_evidence

logger = logging.getLogger(__name__)


def run_fair_rag(query: str) -> str:
    """
    Orchestrates the FAIR-RAG iterative retrieve-filter-assess-refine loop.

    Loop (max 3 iterations):
      1. Retrieve docs for current_query
      2. Merge new docs into accumulator (deduplicate by chunk_id)
      3. Filter accumulated docs (inclusive)
      4. Assess evidence (SEA) against original query
      5. If SUFFICIENT or iteration >= 3: generate_answer and return
      6. Else: refine query, update current_query, continue

    Phase 4 integration point: import and call this function from a Phase 4 graph node.
    Never raises — returns error fallback string on any exception.

    Args:
        query: Original fiqh query string

    Returns:
        str: Complete answer with citations, sources, fatwa disclaimer.
             Returns safe error message on total failure.
    """
    try:
        all_docs: list[dict] = []
        prior_queries: list[str] = [query]
        sea_result: SEAResult | None = None
        filtered_docs: list[dict] = []
        current_query = query

        for iteration in range(1, 4):  # iterations 1, 2, 3 — max 3
            logger.info("[FAIR_RAG] Iteration %d — query: %s", iteration, current_query[:80])

            # Retrieve docs for current query
            new_docs = retrieve_fiqh_documents(current_query)

            # Accumulate unique docs by chunk_id (Pitfall 6: must accumulate, not replace)
            seen_ids = {d["chunk_id"] for d in all_docs}
            for doc in new_docs:
                if doc.get("chunk_id") not in seen_ids:
                    all_docs.append(doc)
                    seen_ids.add(doc["chunk_id"])

            # Filter accumulated docs (inclusive — fail open)
            filtered_docs = filter_evidence(query, all_docs)

            # Assess evidence against original query
            sea_result = assess_evidence(query, filtered_docs)
            logger.info(
                "[FAIR_RAG] Iteration %d verdict: %s — %d findings, %d gaps",
                iteration,
                sea_result.verdict,
                len(sea_result.findings),
                len(sea_result.gaps),
            )

            # Early exit on sufficiency or max iterations
            if sea_result.verdict == "SUFFICIENT" or iteration >= 3:
                break

            # Refine query for next iteration
            refinement_queries = refine_query(query, sea_result, prior_queries)
            prior_queries.extend(refinement_queries)
            current_query = " ".join(refinement_queries)

        is_sufficient = sea_result is not None and sea_result.verdict == "SUFFICIENT"
        docs_for_generation = filtered_docs if filtered_docs else all_docs
        fallback_sea = SEAResult(
            findings=[],
            verdict="INSUFFICIENT",
            confirmed_facts=[],
            gaps=[query],
        )

        return generate_answer(
            query=query,
            docs=docs_for_generation,
            sea_result=sea_result if sea_result is not None else fallback_sea,
            is_sufficient=is_sufficient,
        )

    except Exception as e:
        logger.error("[FAIR_RAG] run_fair_rag error: %s", e)
        return (
            "I was unable to retrieve relevant rulings for this question. "
            "Please consult Sistani's official resources at sistani.org "
            "or contact his office directly.\n\n---\n"
            "Note: This is based on Ayatollah Sistani's published rulings. "
            "For a definitive ruling, consult a qualified jurist or Sistani's official office."
        )
