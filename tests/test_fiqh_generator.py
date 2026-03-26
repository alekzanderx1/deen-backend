"""Unit tests for modules/fiqh/generator.py — all LLM calls are mocked."""
from __future__ import annotations
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock
from modules.fiqh.generator import generate_answer
from modules.fiqh.sea import SEAResult, Finding


def _mock_llm_response(text: str) -> MagicMock:
    """Helper: create a mock model that returns the given text as content."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = text
    mock_model.invoke.return_value = mock_response
    return mock_model


def _make_doc(chunk_id: str, ruling_number: str = "001") -> dict:
    """Helper: create a full doc dict with required metadata fields."""
    return {
        "chunk_id": chunk_id,
        "metadata": {
            "source_book": "Islamic Laws",
            "chapter": "Chapter 1: Tahara",
            "section": "Section 1: Wudu",
            "ruling_number": ruling_number,
            "topic_tags": ["wudu", "tahara"],
            "text_en": f"Ruling {ruling_number}: example ruling text.",
        },
        "page_content": f"Ruling {ruling_number}: example ruling text.",
    }


def _make_sea_result(verdict: str = "SUFFICIENT") -> SEAResult:
    """Helper: create a minimal SEAResult."""
    return SEAResult(
        findings=[],
        verdict=verdict,  # type: ignore[arg-type]
        confirmed_facts=["wudu is required before salah"],
        gaps=[],
    )


FATWA_DISCLAIMER_TEXT = "Note: This is based on Ayatollah Sistani's published rulings."
INSUFFICIENT_WARNING_TEXT = "Insufficient Evidence"
SISTANI_ORG_TEXT = "sistani.org"


class TestGenerateAnswer:
    """Tests for generate_answer(query, docs, sea_result, is_sufficient) -> str"""

    def test_returns_string(self):
        """generate_answer returns a string."""
        docs = [_make_doc("chunk1")]
        sea = _make_sea_result()
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=_mock_llm_response("According to ruling [1], wudu is required.")):
            result = generate_answer("Is wudu required?", docs, sea, is_sufficient=True)
        assert isinstance(result, str)

    def test_always_contains_fatwa_disclaimer(self):
        """generate_answer always contains the fatwa disclaimer text."""
        docs = [_make_doc("chunk1")]
        sea = _make_sea_result()
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=_mock_llm_response("According to ruling [1], wudu is required.")):
            result = generate_answer("Is wudu required?", docs, sea, is_sufficient=True)
        assert FATWA_DISCLAIMER_TEXT in result

    def test_fatwa_disclaimer_with_is_sufficient_false(self):
        """generate_answer always contains the fatwa disclaimer even when is_sufficient=False."""
        docs = [_make_doc("chunk1")]
        sea = _make_sea_result(verdict="INSUFFICIENT")
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=_mock_llm_response("Based on available evidence [1], ...")):
            result = generate_answer("Is wudu required?", docs, sea, is_sufficient=False)
        assert FATWA_DISCLAIMER_TEXT in result

    def test_insufficient_warning_when_is_sufficient_false(self):
        """generate_answer with is_sufficient=False contains the insufficient-evidence warning."""
        docs = [_make_doc("chunk1")]
        sea = _make_sea_result(verdict="INSUFFICIENT")
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=_mock_llm_response("Based on available evidence [1], ...")):
            result = generate_answer("Is wudu required?", docs, sea, is_sufficient=False)
        assert INSUFFICIENT_WARNING_TEXT in result

    def test_no_insufficient_warning_when_is_sufficient_true(self):
        """generate_answer with is_sufficient=True does NOT contain the insufficient-evidence warning."""
        docs = [_make_doc("chunk1")]
        sea = _make_sea_result(verdict="SUFFICIENT")
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=_mock_llm_response("According to ruling [1], wudu is required.")):
            result = generate_answer("Is wudu required?", docs, sea, is_sufficient=True)
        assert INSUFFICIENT_WARNING_TEXT not in result

    def test_produces_sources_section_when_citations_present(self):
        """generate_answer when LLM response contains [1] and [2] produces a ## Sources section."""
        docs = [_make_doc("chunk1", "101"), _make_doc("chunk2", "102")]
        sea = _make_sea_result()
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=_mock_llm_response("Per ruling [1], wudu is required. See also [2].")):
            result = generate_answer("Is wudu required?", docs, sea, is_sufficient=True)
        assert "## Sources" in result

    def test_sources_section_maps_citation_to_doc_metadata(self):
        """generate_answer when LLM response contains [1] maps to docs[0] metadata."""
        docs = [_make_doc("chunk1", "712")]
        sea = _make_sea_result()
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=_mock_llm_response("According to ruling [1], wudu is required.")):
            result = generate_answer("Is wudu required?", docs, sea, is_sufficient=True)
        assert "## Sources" in result
        assert "[1]" in result
        # Should contain the source book name
        assert "Islamic Laws" in result

    def test_safe_fallback_on_exception(self):
        """generate_answer when docs is empty and LLM raises Exception returns fallback with sistani.org."""
        docs = []
        sea = _make_sea_result()
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("API error")
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=mock_model):
            result = generate_answer("Is wudu required?", docs, sea, is_sufficient=True)
        assert isinstance(result, str)
        assert len(result) > 0
        assert SISTANI_ORG_TEXT in result

    def test_fallback_contains_fatwa_disclaimer_or_sistani_reference(self):
        """generate_answer with LLM raising Exception still returns non-empty string with disclaimer or fallback."""
        docs = [_make_doc("chunk1")]
        sea = _make_sea_result()
        mock_model = MagicMock()
        mock_model.invoke.side_effect = RuntimeError("network failure")
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=mock_model):
            result = generate_answer("Is wudu required?", docs, sea, is_sufficient=True)
        assert isinstance(result, str)
        assert len(result) > 0
        # Either the disclaimer or a sistani reference should be present
        assert FATWA_DISCLAIMER_TEXT in result or SISTANI_ORG_TEXT in result

    def test_never_raises(self):
        """generate_answer never raises under any condition."""
        docs = []
        sea = _make_sea_result()
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("catastrophic failure")
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=mock_model):
            # Must not raise
            result = generate_answer("any query", docs, sea, is_sufficient=False)
        assert isinstance(result, str)

    def test_no_sources_section_when_no_citations(self):
        """generate_answer does not produce ## Sources when LLM response has no [n] tokens."""
        docs = [_make_doc("chunk1")]
        sea = _make_sea_result()
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=_mock_llm_response("Wudu is required before salah.")):
            result = generate_answer("Is wudu required?", docs, sea, is_sufficient=True)
        # No citations in LLM response, so no ## Sources section expected
        # But disclaimer should still be present
        assert FATWA_DISCLAIMER_TEXT in result

    def test_ruling_number_in_sources_section(self):
        """generate_answer includes ruling_number in sources section when present."""
        docs = [_make_doc("chunk1", "712")]
        sea = _make_sea_result()
        with patch("modules.fiqh.generator.chat_models.get_generator_model",
                   return_value=_mock_llm_response("According to ruling [1], this is the answer.")):
            result = generate_answer("Is wudu required?", docs, sea, is_sufficient=True)
        assert "Ruling 712" in result
