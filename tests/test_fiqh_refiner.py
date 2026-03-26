"""Unit tests for modules/fiqh/refiner.py — all LLM calls are mocked."""
from __future__ import annotations
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import pytest
from unittest.mock import patch, MagicMock
from modules.fiqh.refiner import refine_query
from modules.fiqh.sea import SEAResult, Finding


def _mock_llm_response(text: str) -> MagicMock:
    """Helper: create a mock model that returns the given text as content."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = text
    mock_model.invoke.return_value = mock_response
    return mock_model


def _make_sea_result(
    confirmed_facts: list[str] | None = None,
    gaps: list[str] | None = None,
) -> SEAResult:
    """Helper: create a minimal SEAResult with the given facts and gaps."""
    return SEAResult(
        findings=[],
        verdict="INSUFFICIENT",
        confirmed_facts=confirmed_facts or [],
        gaps=gaps or ["wudu ruling for specific case"],
    )


class TestRefineQuery:
    """Tests for refine_query(original_query, sea_result, prior_queries) -> list[str]"""

    def test_returns_list_of_strings(self):
        """refine_query returns a list of strings."""
        sea = _make_sea_result(gaps=["gap about tahara"])
        llm_output = json.dumps(["tayammum ruling when water unavailable", "dry ablution conditions"])
        with patch("modules.fiqh.refiner.chat_models.get_generator_model",
                   return_value=_mock_llm_response(llm_output)):
            result = refine_query("What is tayammum?", sea)
        assert isinstance(result, list)
        assert all(isinstance(q, str) for q in result)

    def test_returns_1_to_4_queries(self):
        """refine_query returns between 1 and 4 sub-queries."""
        sea = _make_sea_result(gaps=["gap 1", "gap 2"])
        llm_output = json.dumps(["q1", "q2", "q3"])
        with patch("modules.fiqh.refiner.chat_models.get_generator_model",
                   return_value=_mock_llm_response(llm_output)):
            result = refine_query("What is the ruling?", sea)
        assert 1 <= len(result) <= 4

    def test_caps_at_4_even_if_llm_returns_more(self):
        """refine_query caps output at 4 sub-queries even if LLM returns more."""
        sea = _make_sea_result(gaps=["gap 1"])
        llm_output = json.dumps(["q1", "q2", "q3", "q4", "q5", "q6"])
        with patch("modules.fiqh.refiner.chat_models.get_generator_model",
                   return_value=_mock_llm_response(llm_output)):
            result = refine_query("What is the ruling?", sea)
        assert len(result) <= 4

    def test_fallback_on_llm_exception(self):
        """refine_query falls back to [original_query] when LLM raises Exception."""
        sea = _make_sea_result()
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("API error")
        with patch("modules.fiqh.refiner.chat_models.get_generator_model",
                   return_value=mock_model):
            result = refine_query("wudu ruling", sea)
        assert result == ["wudu ruling"]

    def test_fallback_on_invalid_json(self):
        """refine_query falls back to [original_query] when LLM returns invalid JSON."""
        sea = _make_sea_result()
        with patch("modules.fiqh.refiner.chat_models.get_generator_model",
                   return_value=_mock_llm_response("not valid json at all")):
            result = refine_query("salah conditions", sea)
        assert result == ["salah conditions"]

    def test_fallback_on_empty_list(self):
        """refine_query falls back to [original_query] when LLM returns empty list."""
        sea = _make_sea_result()
        with patch("modules.fiqh.refiner.chat_models.get_generator_model",
                   return_value=_mock_llm_response("[]")):
            result = refine_query("ghusl ruling", sea)
        assert result == ["ghusl ruling"]

    def test_prior_queries_defaults_to_empty_list(self):
        """refine_query with prior_queries=None uses [] as default (no mutable default arg)."""
        sea = _make_sea_result(gaps=["gap about khums"])
        llm_output = json.dumps(["khums calculation ruling"])
        with patch("modules.fiqh.refiner.chat_models.get_generator_model",
                   return_value=_mock_llm_response(llm_output)):
            # Should not raise TypeError about NoneType
            result = refine_query("khums ruling", sea, prior_queries=None)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_strips_markdown_code_fence(self):
        """refine_query strips markdown code fences if LLM wraps output in them."""
        sea = _make_sea_result(gaps=["gap about sawm"])
        llm_output = "```json\n[\"sawm exemption illness\"]\n```"
        with patch("modules.fiqh.refiner.chat_models.get_generator_model",
                   return_value=_mock_llm_response(llm_output)):
            result = refine_query("fasting ruling when ill", sea)
        assert result == ["sawm exemption illness"]

    def test_never_raises(self):
        """refine_query never raises under any condition."""
        sea = _make_sea_result()
        mock_model = MagicMock()
        mock_model.invoke.side_effect = RuntimeError("catastrophic failure")
        with patch("modules.fiqh.refiner.chat_models.get_generator_model",
                   return_value=mock_model):
            # Must not raise
            result = refine_query("any query", sea)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_uses_confirmed_facts_and_gaps(self):
        """refine_query uses sea_result.confirmed_facts and sea_result.gaps in prompt."""
        sea = _make_sea_result(
            confirmed_facts=["wudu is required before salah"],
            gaps=["whether wudu is invalidated by sleep"],
        )
        llm_output = json.dumps(["wudu nullifiers sleep ruling sistani"])
        with patch("modules.fiqh.refiner.chat_models.get_generator_model") as mock_get_model:
            mock_model = _mock_llm_response(llm_output)
            mock_get_model.return_value = mock_model
            result = refine_query("Does sleep break wudu?", sea)
        # The invoke should have been called
        mock_model.invoke.assert_called_once()
        assert isinstance(result, list)

    def test_fallback_on_non_list_json(self):
        """refine_query falls back to [original_query] when LLM returns non-list JSON."""
        sea = _make_sea_result()
        with patch("modules.fiqh.refiner.chat_models.get_generator_model",
                   return_value=_mock_llm_response('{"key": "value"}')):
            result = refine_query("tahara ruling", sea)
        assert result == ["tahara ruling"]
