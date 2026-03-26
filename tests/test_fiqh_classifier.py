"""Unit tests for modules/fiqh/classifier.py — all LLM calls are mocked."""
from __future__ import annotations
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock
from modules.fiqh.classifier import classify_fiqh_query, VALID_CATEGORIES


def _mock_llm_response(text: str) -> MagicMock:
    """Helper: create a mock model that returns the given text as content."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = text
    mock_model.invoke.return_value = mock_response
    return mock_model


class TestValidCategories:
    def test_valid_categories_contains_exactly_6_entries(self):
        assert len(VALID_CATEGORIES) == 6

    def test_valid_categories_contains_expected_strings(self):
        expected = {"VALID_OBVIOUS", "VALID_SMALL", "VALID_LARGE",
                    "VALID_REASONER", "OUT_OF_SCOPE_FIQH", "UNETHICAL"}
        assert VALID_CATEGORIES == expected


class TestClassifyFiqhQuery:
    @pytest.mark.parametrize("llm_output,expected", [
        ("VALID_OBVIOUS", "VALID_OBVIOUS"),
        ("VALID_SMALL", "VALID_SMALL"),
        ("VALID_LARGE", "VALID_LARGE"),
        ("VALID_REASONER", "VALID_REASONER"),
        ("OUT_OF_SCOPE_FIQH", "OUT_OF_SCOPE_FIQH"),
        ("UNETHICAL", "UNETHICAL"),
        ("valid_obvious", "VALID_OBVIOUS"),   # case insensitive
        ("  VALID_SMALL  ", "VALID_SMALL"),   # whitespace trimmed
    ])
    def test_returns_correct_category_for_valid_llm_output(self, llm_output, expected):
        with patch("modules.fiqh.classifier.chat_models.get_classifier_model",
                   return_value=_mock_llm_response(llm_output)):
            result = classify_fiqh_query("test query")
        assert result == expected

    def test_returns_out_of_scope_for_unexpected_llm_output(self):
        with patch("modules.fiqh.classifier.chat_models.get_classifier_model",
                   return_value=_mock_llm_response("SOME_UNKNOWN_CATEGORY")):
            result = classify_fiqh_query("test query")
        assert result == "OUT_OF_SCOPE_FIQH"

    def test_returns_out_of_scope_on_exception(self):
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("API error")
        with patch("modules.fiqh.classifier.chat_models.get_classifier_model",
                   return_value=mock_model):
            result = classify_fiqh_query("test query")
        assert result == "OUT_OF_SCOPE_FIQH"

    def test_never_raises(self):
        mock_model = MagicMock()
        mock_model.invoke.side_effect = RuntimeError("network failure")
        with patch("modules.fiqh.classifier.chat_models.get_classifier_model",
                   return_value=mock_model):
            # Must not raise — should return safe fallback
            result = classify_fiqh_query("any query")
        assert result in VALID_CATEGORIES
