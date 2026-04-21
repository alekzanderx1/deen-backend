"""Unit tests for modules/fiqh/classifier.py — all LLM calls are mocked."""
from __future__ import annotations
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock
from modules.fiqh.classifier import classify_fiqh_query, VALID_CATEGORIES, FiqhCategory


def _mock_classifier_model(category_str: str) -> MagicMock:
    """Helper: mock that simulates with_structured_output returning FiqhCategory."""
    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_model.with_structured_output.return_value = mock_structured
    mock_structured.invoke.return_value = FiqhCategory(category=category_str)
    return mock_model


class TestValidCategories:
    def test_valid_categories_contains_exactly_6_entries(self):
        assert len(VALID_CATEGORIES) == 6

    def test_valid_categories_contains_expected_strings(self):
        expected = {"VALID_OBVIOUS", "VALID_SMALL", "VALID_LARGE",
                    "VALID_REASONER", "OUT_OF_SCOPE_FIQH", "UNETHICAL"}
        assert VALID_CATEGORIES == expected


class TestClassifyFiqhQuery:
    @pytest.mark.parametrize("category_str,expected", [
        ("VALID_OBVIOUS", "VALID_OBVIOUS"),
        ("VALID_SMALL", "VALID_SMALL"),
        ("VALID_LARGE", "VALID_LARGE"),
        ("VALID_REASONER", "VALID_REASONER"),
        ("OUT_OF_SCOPE_FIQH", "OUT_OF_SCOPE_FIQH"),
        ("UNETHICAL", "UNETHICAL"),
    ])
    def test_returns_correct_category_for_valid_llm_output(self, category_str, expected):
        with patch("modules.fiqh.classifier.chat_models.get_classifier_model",
                   return_value=_mock_classifier_model(category_str)):
            result = classify_fiqh_query("test query")
        assert result == expected

    def test_returns_out_of_scope_on_exception(self):
        mock_model = MagicMock()
        mock_structured = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        mock_structured.invoke.side_effect = Exception("validation error")
        with patch("modules.fiqh.classifier.chat_models.get_classifier_model",
                   return_value=mock_model):
            result = classify_fiqh_query("test query")
        assert result == "OUT_OF_SCOPE_FIQH"

    def test_never_raises(self):
        mock_model = MagicMock()
        mock_structured = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        mock_structured.invoke.side_effect = RuntimeError("network failure")
        with patch("modules.fiqh.classifier.chat_models.get_classifier_model",
                   return_value=mock_model):
            result = classify_fiqh_query("any query")
        assert result in VALID_CATEGORIES
