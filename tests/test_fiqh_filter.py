"""Unit tests for modules/fiqh/filter.py — all LLM calls are mocked."""
from __future__ import annotations
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock
from modules.fiqh.filter import filter_evidence


def _mock_llm_response(text: str) -> MagicMock:
    """Helper: create a mock model that returns the given text as content."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = text
    mock_model.invoke.return_value = mock_response
    return mock_model


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


class TestFilterEvidence:
    def test_empty_docs_returns_empty_list(self):
        """filter_evidence with empty input returns empty list without calling LLM."""
        result = filter_evidence("wudu question", [])
        assert result == []

    def test_single_match_returns_only_matched_doc(self):
        """LLM returning '["chunk_1"]' from two docs keeps only chunk_1."""
        docs = [_make_doc("chunk_1"), _make_doc("chunk_2")]
        with patch(
            "modules.fiqh.filter.chat_models.get_generator_model",
            return_value=_mock_llm_response('["chunk_1"]'),
        ):
            result = filter_evidence("wudu question", docs)
        assert len(result) == 1
        assert result[0]["chunk_id"] == "chunk_1"

    def test_multiple_matches_returns_all_matched_in_original_order(self):
        """LLM returning both IDs returns both docs in original input order."""
        docs = [_make_doc("chunk_1"), _make_doc("chunk_2")]
        with patch(
            "modules.fiqh.filter.chat_models.get_generator_model",
            return_value=_mock_llm_response('["chunk_1", "chunk_2"]'),
        ):
            result = filter_evidence("wudu question", docs)
        assert len(result) == 2
        assert result[0]["chunk_id"] == "chunk_1"
        assert result[1]["chunk_id"] == "chunk_2"

    def test_empty_keep_list_returns_all_docs(self):
        """LLM returning '[]' (empty list) triggers fail-open: return all docs."""
        docs = [_make_doc("chunk_1"), _make_doc("chunk_2")]
        with patch(
            "modules.fiqh.filter.chat_models.get_generator_model",
            return_value=_mock_llm_response("[]"),
        ):
            result = filter_evidence("wudu question", docs)
        assert result == docs

    def test_llm_exception_returns_all_docs(self):
        """LLM raising Exception returns all input docs unchanged."""
        docs = [_make_doc("chunk_1"), _make_doc("chunk_2")]
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("API error")
        with patch(
            "modules.fiqh.filter.chat_models.get_generator_model",
            return_value=mock_model,
        ):
            result = filter_evidence("wudu question", docs)
        assert result == docs

    def test_json_parse_error_returns_all_docs(self):
        """LLM returning invalid JSON returns all input docs unchanged."""
        docs = [_make_doc("chunk_1"), _make_doc("chunk_2")]
        with patch(
            "modules.fiqh.filter.chat_models.get_generator_model",
            return_value=_mock_llm_response("not valid json at all"),
        ):
            result = filter_evidence("wudu question", docs)
        assert result == docs

    def test_markdown_fenced_json_is_parsed_correctly(self):
        """LLM returning markdown-fenced JSON is stripped and parsed correctly."""
        docs = [_make_doc("chunk_1"), _make_doc("chunk_2")]
        fenced_response = "```json\n[\"chunk_1\"]\n```"
        with patch(
            "modules.fiqh.filter.chat_models.get_generator_model",
            return_value=_mock_llm_response(fenced_response),
        ):
            result = filter_evidence("wudu question", docs)
        assert len(result) == 1
        assert result[0]["chunk_id"] == "chunk_1"

    def test_unknown_chunk_ids_are_silently_ignored(self):
        """LLM returning chunk IDs not in input docs silently ignores unknowns.

        If ALL returned IDs are unknown, fail-open returns all docs.
        """
        docs = [_make_doc("chunk_1"), _make_doc("chunk_2")]
        with patch(
            "modules.fiqh.filter.chat_models.get_generator_model",
            return_value=_mock_llm_response('["unknown_id_xyz"]'),
        ):
            result = filter_evidence("wudu question", docs)
        # All known chunk_ids were filtered out by unknown — fail open
        assert result == docs

    def test_partial_unknown_ids_keeps_known_docs(self):
        """LLM returning a mix of known and unknown IDs keeps only the known ones."""
        docs = [_make_doc("chunk_1"), _make_doc("chunk_2")]
        with patch(
            "modules.fiqh.filter.chat_models.get_generator_model",
            return_value=_mock_llm_response('["chunk_1", "unknown_id"]'),
        ):
            result = filter_evidence("wudu question", docs)
        assert len(result) == 1
        assert result[0]["chunk_id"] == "chunk_1"

    def test_never_raises(self):
        """filter_evidence must never raise under any condition."""
        docs = [_make_doc("chunk_1")]
        mock_model = MagicMock()
        mock_model.invoke.side_effect = RuntimeError("unexpected failure")
        with patch(
            "modules.fiqh.filter.chat_models.get_generator_model",
            return_value=mock_model,
        ):
            # Must not raise
            result = filter_evidence("any query", docs)
        assert result == docs
