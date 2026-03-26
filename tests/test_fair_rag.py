"""Unit tests for modules/fiqh/fair_rag.py — all dependencies are mocked."""
from __future__ import annotations
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock, call

from modules.fiqh.sea import SEAResult, Finding


def _make_doc(chunk_id: str) -> dict:
    """Helper: create a minimal doc dict with the given chunk_id."""
    return {
        "chunk_id": chunk_id,
        "metadata": {
            "source_book": "Islamic Laws",
            "chapter": "Ch1",
            "section": "S1",
            "ruling_number": "001",
            "text_en": f"text for {chunk_id}",
        },
        "page_content": f"text for {chunk_id}",
    }


def _sufficient_sea_result() -> SEAResult:
    """Helper: create a SUFFICIENT SEAResult."""
    return SEAResult(
        findings=[
            Finding(
                description="test finding",
                confirmed=True,
                citation="exact quote from evidence",
                gap_summary="",
            )
        ],
        verdict="SUFFICIENT",
        confirmed_facts=["fact 1"],
        gaps=[],
    )


def _insufficient_sea_result() -> SEAResult:
    """Helper: create an INSUFFICIENT SEAResult."""
    return SEAResult(
        findings=[
            Finding(
                description="missing ruling",
                confirmed=False,
                citation="",
                gap_summary="ruling not found in evidence",
            )
        ],
        verdict="INSUFFICIENT",
        confirmed_facts=[],
        gaps=["gap1"],
    )


class TestRunFairRag:
    def test_exits_early_on_sufficient(self):
        """When SEA returns SUFFICIENT on iteration 1, retrieve is called exactly once."""
        from modules.fiqh.fair_rag import run_fair_rag

        docs = [_make_doc("chunk_1"), _make_doc("chunk_2")]
        sufficient = _sufficient_sea_result()

        with patch("modules.fiqh.fair_rag.retrieve_fiqh_documents", return_value=docs) as mock_retrieve, \
             patch("modules.fiqh.fair_rag.filter_evidence", return_value=docs), \
             patch("modules.fiqh.fair_rag.assess_evidence", return_value=sufficient), \
             patch("modules.fiqh.fair_rag.refine_query", return_value=["refined"]), \
             patch("modules.fiqh.fair_rag.generate_answer", return_value="answer text") as mock_gen:
            result = run_fair_rag("what is wudu?")

        mock_retrieve.assert_called_once()
        assert result == "answer text"

    def test_runs_max_3_iterations(self):
        """When SEA always returns INSUFFICIENT, retrieve is called exactly 3 times."""
        from modules.fiqh.fair_rag import run_fair_rag

        docs = [_make_doc("chunk_1")]
        insufficient = _insufficient_sea_result()

        with patch("modules.fiqh.fair_rag.retrieve_fiqh_documents", return_value=docs) as mock_retrieve, \
             patch("modules.fiqh.fair_rag.filter_evidence", return_value=docs), \
             patch("modules.fiqh.fair_rag.assess_evidence", return_value=insufficient), \
             patch("modules.fiqh.fair_rag.refine_query", return_value=["refined sub-query"]), \
             patch("modules.fiqh.fair_rag.generate_answer", return_value="answer") as mock_gen:
            result = run_fair_rag("what is salah?")

        assert mock_retrieve.call_count == 3

    def test_accumulates_docs_across_iterations(self):
        """Docs accumulate across iterations — filter/assess see all docs, not just latest."""
        from modules.fiqh.fair_rag import run_fair_rag

        # Iteration 1 returns chunk_1, iteration 2 returns chunk_2
        iter_docs = [[_make_doc("chunk_1")], [_make_doc("chunk_2")], []]
        retrieve_side_effect = iter(iter_docs)

        insufficient = _insufficient_sea_result()
        sufficient = _sufficient_sea_result()
        assess_side_effect = iter([insufficient, sufficient])

        filter_calls = []

        def capturing_filter(query, docs):
            filter_calls.append(list(docs))  # snapshot docs list
            return docs

        with patch("modules.fiqh.fair_rag.retrieve_fiqh_documents", side_effect=lambda q: next(retrieve_side_effect)), \
             patch("modules.fiqh.fair_rag.filter_evidence", side_effect=capturing_filter), \
             patch("modules.fiqh.fair_rag.assess_evidence", side_effect=lambda q, d: next(assess_side_effect)), \
             patch("modules.fiqh.fair_rag.refine_query", return_value=["refined"]), \
             patch("modules.fiqh.fair_rag.generate_answer", return_value="answer"):
            run_fair_rag("test query")

        # First filter call: 1 doc (chunk_1 only)
        assert len(filter_calls[0]) == 1
        assert filter_calls[0][0]["chunk_id"] == "chunk_1"

        # Second filter call: 2 docs accumulated (chunk_1 + chunk_2)
        assert len(filter_calls[1]) == 2
        chunk_ids_second = {d["chunk_id"] for d in filter_calls[1]}
        assert "chunk_1" in chunk_ids_second
        assert "chunk_2" in chunk_ids_second

    def test_deduplicates_docs_by_chunk_id(self):
        """Same chunk_id from two iterations appears only once in the accumulated set."""
        from modules.fiqh.fair_rag import run_fair_rag

        # Both iterations return docs with chunk_1 (duplicate) plus a new one
        docs_iter1 = [_make_doc("chunk_1"), _make_doc("chunk_shared")]
        docs_iter2 = [_make_doc("chunk_2"), _make_doc("chunk_shared")]  # chunk_shared is duplicate

        retrieve_calls = iter([docs_iter1, docs_iter2, []])
        insufficient = _insufficient_sea_result()
        sufficient = _sufficient_sea_result()
        assess_calls = iter([insufficient, sufficient])

        seen_doc_counts = []

        def capturing_filter(query, docs):
            seen_doc_counts.append(len(docs))
            return docs

        with patch("modules.fiqh.fair_rag.retrieve_fiqh_documents", side_effect=lambda q: next(retrieve_calls)), \
             patch("modules.fiqh.fair_rag.filter_evidence", side_effect=capturing_filter), \
             patch("modules.fiqh.fair_rag.assess_evidence", side_effect=lambda q, d: next(assess_calls)), \
             patch("modules.fiqh.fair_rag.refine_query", return_value=["refined"]), \
             patch("modules.fiqh.fair_rag.generate_answer", return_value="answer"):
            run_fair_rag("test query")

        # After iter 1: 2 docs (chunk_1, chunk_shared)
        assert seen_doc_counts[0] == 2
        # After iter 2: 3 unique docs (chunk_1, chunk_shared, chunk_2) — chunk_shared deduplicated
        assert seen_doc_counts[1] == 3

    def test_is_sufficient_true_when_sufficient(self):
        """generate_answer is called with is_sufficient=True when SEA returns SUFFICIENT."""
        from modules.fiqh.fair_rag import run_fair_rag

        docs = [_make_doc("chunk_1")]
        sufficient = _sufficient_sea_result()

        with patch("modules.fiqh.fair_rag.retrieve_fiqh_documents", return_value=docs), \
             patch("modules.fiqh.fair_rag.filter_evidence", return_value=docs), \
             patch("modules.fiqh.fair_rag.assess_evidence", return_value=sufficient), \
             patch("modules.fiqh.fair_rag.refine_query", return_value=["refined"]), \
             patch("modules.fiqh.fair_rag.generate_answer", return_value="answer") as mock_gen:
            run_fair_rag("wudu question")

        _, kwargs = mock_gen.call_args
        assert kwargs.get("is_sufficient") is True or mock_gen.call_args[0][3] is True

    def test_is_sufficient_false_when_all_insufficient(self):
        """generate_answer is called with is_sufficient=False when all 3 iterations return INSUFFICIENT."""
        from modules.fiqh.fair_rag import run_fair_rag

        docs = [_make_doc("chunk_1")]
        insufficient = _insufficient_sea_result()

        with patch("modules.fiqh.fair_rag.retrieve_fiqh_documents", return_value=docs), \
             patch("modules.fiqh.fair_rag.filter_evidence", return_value=docs), \
             patch("modules.fiqh.fair_rag.assess_evidence", return_value=insufficient), \
             patch("modules.fiqh.fair_rag.refine_query", return_value=["refined"]), \
             patch("modules.fiqh.fair_rag.generate_answer", return_value="answer") as mock_gen:
            run_fair_rag("salah question")

        # Check is_sufficient=False was passed (check both positional and keyword)
        args, kwargs = mock_gen.call_args
        is_sufficient_val = kwargs.get("is_sufficient") if "is_sufficient" in kwargs else args[3]
        assert is_sufficient_val is False

    def test_never_raises_on_exception(self):
        """When retrieve_fiqh_documents raises RuntimeError, run_fair_rag returns a string, never raises."""
        from modules.fiqh.fair_rag import run_fair_rag

        with patch("modules.fiqh.fair_rag.retrieve_fiqh_documents", side_effect=RuntimeError("network failure")):
            result = run_fair_rag("some question")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_non_empty_string(self):
        """Basic smoke test: all deps mocked, run_fair_rag returns a non-empty string."""
        from modules.fiqh.fair_rag import run_fair_rag

        docs = [_make_doc("chunk_1")]
        sufficient = _sufficient_sea_result()

        with patch("modules.fiqh.fair_rag.retrieve_fiqh_documents", return_value=docs), \
             patch("modules.fiqh.fair_rag.filter_evidence", return_value=docs), \
             patch("modules.fiqh.fair_rag.assess_evidence", return_value=sufficient), \
             patch("modules.fiqh.fair_rag.refine_query", return_value=["refined"]), \
             patch("modules.fiqh.fair_rag.generate_answer", return_value="Final answer text here"):
            result = run_fair_rag("what are the conditions for tayammum?")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_refine_query_not_called_on_final_iteration(self):
        """refine_query is NOT called when verdict=INSUFFICIENT on iteration 3 (last iteration)."""
        from modules.fiqh.fair_rag import run_fair_rag

        docs = [_make_doc("chunk_1")]
        insufficient = _insufficient_sea_result()

        # Always returns INSUFFICIENT — loop runs all 3, refine should only be called on iter 1 and 2
        with patch("modules.fiqh.fair_rag.retrieve_fiqh_documents", return_value=docs), \
             patch("modules.fiqh.fair_rag.filter_evidence", return_value=docs), \
             patch("modules.fiqh.fair_rag.assess_evidence", return_value=insufficient), \
             patch("modules.fiqh.fair_rag.refine_query", return_value=["refined"]) as mock_refine, \
             patch("modules.fiqh.fair_rag.generate_answer", return_value="answer"):
            run_fair_rag("test query")

        # refine called on iter 1 and 2 (before iter 3), but NOT on iter 3 (max reached)
        assert mock_refine.call_count == 2
