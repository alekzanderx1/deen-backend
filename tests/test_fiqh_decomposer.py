"""Unit tests for modules/fiqh/decomposer.py — all LLM calls are mocked."""
from __future__ import annotations
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock
from modules.fiqh.decomposer import decompose_query


def _mock_llm_response(text: str) -> MagicMock:
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = text
    mock_model.invoke.return_value = mock_response
    return mock_model


class TestDecomposeQuery:
    def test_single_part_query_returns_list_of_one(self):
        payload = json.dumps(["wudu nullifiers sleep validity istinja"])
        with patch("modules.fiqh.decomposer.chat_models.get_classifier_model",
                   return_value=_mock_llm_response(payload)):
            result = decompose_query("Is my wudu broken if I sleep?")
        assert isinstance(result, list)
        assert len(result) == 1
        assert "wudu" in result[0].lower() or "nullifiers" in result[0].lower()

    def test_multi_part_query_returns_multiple_sub_queries(self):
        payload = json.dumps([
            "khuffayn wet socks prayer validity wudu",
            "ring jewelry obstruction wudu ghusl tahara"
        ])
        with patch("modules.fiqh.decomposer.chat_models.get_classifier_model",
                   return_value=_mock_llm_response(payload)):
            result = decompose_query("Can I pray with wet socks and do I need to remove my ring?")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_caps_at_4_sub_queries(self):
        payload = json.dumps(["q1", "q2", "q3", "q4", "q5"])  # 5 items — must be capped
        with patch("modules.fiqh.decomposer.chat_models.get_classifier_model",
                   return_value=_mock_llm_response(payload)):
            result = decompose_query("complex multi-part query")
        assert len(result) <= 4

    def test_fallback_to_original_query_on_json_parse_error(self):
        with patch("modules.fiqh.decomposer.chat_models.get_classifier_model",
                   return_value=_mock_llm_response("not valid json at all")):
            result = decompose_query("original query text")
        assert result == ["original query text"]

    def test_fallback_on_empty_list_from_llm(self):
        with patch("modules.fiqh.decomposer.chat_models.get_classifier_model",
                   return_value=_mock_llm_response("[]")):
            result = decompose_query("original query text")
        assert result == ["original query text"]

    def test_fallback_on_exception(self):
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("API failure")
        with patch("modules.fiqh.decomposer.chat_models.get_classifier_model",
                   return_value=mock_model):
            result = decompose_query("original query text")
        assert result == ["original query text"]

    def test_strips_markdown_code_fence(self):
        payload = '```json\n["wudu nullifiers ruling"]\n```'
        with patch("modules.fiqh.decomposer.chat_models.get_classifier_model",
                   return_value=_mock_llm_response(payload)):
            result = decompose_query("Is my wudu broken?")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "wudu nullifiers ruling"

    def test_never_returns_empty_list(self):
        mock_model = MagicMock()
        mock_model.invoke.side_effect = RuntimeError("crash")
        with patch("modules.fiqh.decomposer.chat_models.get_classifier_model",
                   return_value=mock_model):
            result = decompose_query("some query")
        assert len(result) >= 1
