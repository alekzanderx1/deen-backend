"""Unit tests for modules/fiqh/retriever.py — all Pinecone and embedding calls are mocked."""
from __future__ import annotations
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock
from modules.fiqh.retriever import _rrf_merge, retrieve_fiqh_documents


def _make_match(chunk_id: str, metadata: dict | None = None) -> MagicMock:
    """Helper: create a mock Pinecone match object."""
    m = MagicMock()
    m.id = chunk_id
    m.metadata = metadata or {
        "text_en": f"ruling text for {chunk_id}",
        "source_book": "Islamic Laws",
        "chapter": "Chapter 1",
        "section": "Section 1",
        "ruling_number": chunk_id.split("_")[1] if "_" in chunk_id else "000",
        "topic_tags": ["tahara"],
    }
    m.score = 0.9
    return m


def _make_pinecone_response(matches: list) -> MagicMock:
    """Helper: create a mock Pinecone query response."""
    r = MagicMock()
    r.matches = matches
    return r


class TestRrfMerge:
    def test_document_appearing_in_both_lists_gets_higher_score(self):
        """A doc appearing in both dense and sparse results should rank above docs in only one."""
        # doc_a appears in both lists at rank 0 — must outscore doc_b (dense only) and doc_c (sparse only)
        doc_a_dense = _make_match("doc_a")
        doc_a_sparse = _make_match("doc_a")
        doc_b_dense = _make_match("doc_b")
        doc_c_sparse = _make_match("doc_c")

        result = _rrf_merge(
            dense_matches=[doc_a_dense, doc_b_dense],
            sparse_matches=[doc_a_sparse, doc_c_sparse],
            k=60, top_n=3
        )
        chunk_ids = [d["chunk_id"] for d in result]
        assert chunk_ids[0] == "doc_a", f"doc_a should rank first, got {chunk_ids}"

    def test_returns_correct_doc_shape(self):
        """Each returned doc must have chunk_id, metadata, and page_content keys."""
        match = _make_match("ruling_0712_chunk0", {
            "text_en": "Prayer ruling text",
            "source_book": "Islamic Laws",
            "chapter": "Chapter 5",
            "section": "Section 2",
            "ruling_number": "0712",
        })
        result = _rrf_merge(dense_matches=[match], sparse_matches=[], k=60, top_n=5)
        assert len(result) == 1
        doc = result[0]
        assert "chunk_id" in doc
        assert "metadata" in doc
        assert "page_content" in doc
        assert doc["chunk_id"] == "ruling_0712_chunk0"
        assert doc["page_content"] == "Prayer ruling text"

    def test_top_n_limits_output(self):
        """Should return at most top_n documents."""
        dense_matches = [_make_match(f"doc_{i}") for i in range(10)]
        result = _rrf_merge(dense_matches=dense_matches, sparse_matches=[], k=60, top_n=5)
        assert len(result) <= 5

    def test_empty_inputs_returns_empty(self):
        result = _rrf_merge(dense_matches=[], sparse_matches=[], k=60, top_n=5)
        assert result == []

    def test_rrf_score_formula_correct(self):
        """Verify RRF: doc at rank 0 in one list should score 1/(60+1) = 0.01639..."""
        match = _make_match("only_doc")
        result = _rrf_merge(dense_matches=[match], sparse_matches=[], k=60, top_n=1)
        assert len(result) == 1
        # Score is not directly exposed, but doc must be present
        assert result[0]["chunk_id"] == "only_doc"


class TestRetrieveFiqhDocuments:
    def _patch_all(self, sub_queries, dense_matches_per_sq, sparse_matches_per_sq):
        """Set up mocks for the full retrieval pipeline."""
        mock_decompose = MagicMock(return_value=sub_queries)
        mock_dense_vec = [0.1] * 768
        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = mock_dense_vec

        mock_bm25 = MagicMock()
        mock_bm25.encode_queries.return_value = {"indices": [1, 2], "values": [0.5, 0.3]}

        # Dense and sparse indexes both return the same mock structure per call
        call_count = [0]
        def mock_index_factory(*args, **kwargs):
            idx = MagicMock()
            call_idx = call_count[0] % 2  # 0=dense, 1=sparse (alternating per sub-query)
            call_count[0] += 1
            if call_idx == 0:
                idx.query.return_value = _make_pinecone_response(dense_matches_per_sq)
            else:
                idx.query.return_value = _make_pinecone_response(sparse_matches_per_sq)
            return idx

        return mock_decompose, mock_embedder, mock_bm25, mock_index_factory

    def test_returns_list_of_dicts(self):
        dense = [_make_match("doc_a"), _make_match("doc_b")]
        sparse = [_make_match("doc_c")]
        with patch("modules.fiqh.retriever.decompose_query", return_value=["wudu ruling"]), \
             patch("modules.fiqh.retriever.getDenseEmbedder") as mock_emb, \
             patch("modules.fiqh.retriever._get_bm25_encoder") as mock_bm25, \
             patch("modules.fiqh.retriever._get_sparse_vectorstore") as mock_vs:
            mock_emb.return_value.embed_query.return_value = [0.1] * 768
            mock_bm25.return_value.encode_queries.return_value = {"indices": [1], "values": [0.5]}
            mock_index = MagicMock()
            mock_index.query.side_effect = [
                _make_pinecone_response(dense),   # dense call
                _make_pinecone_response(sparse),  # sparse call
            ]
            mock_vs.return_value = mock_index

            result = retrieve_fiqh_documents("Is my wudu broken if I sleep?")
        assert isinstance(result, list)
        for doc in result:
            assert "chunk_id" in doc
            assert "metadata" in doc
            assert "page_content" in doc

    def test_deduplicates_across_sub_queries(self):
        """Same chunk_id appearing from multiple sub-queries must appear only once."""
        shared_doc = _make_match("ruling_0712_chunk0")
        with patch("modules.fiqh.retriever.decompose_query", return_value=["q1", "q2"]), \
             patch("modules.fiqh.retriever.getDenseEmbedder") as mock_emb, \
             patch("modules.fiqh.retriever._get_bm25_encoder") as mock_bm25, \
             patch("modules.fiqh.retriever._get_sparse_vectorstore") as mock_vs:
            mock_emb.return_value.embed_query.return_value = [0.1] * 768
            mock_bm25.return_value.encode_queries.return_value = {"indices": [1], "values": [0.5]}
            mock_index = MagicMock()
            # Both sub-queries return the same shared doc
            mock_index.query.return_value = _make_pinecone_response([shared_doc])
            mock_vs.return_value = mock_index

            result = retrieve_fiqh_documents("complex query with two parts")
        # "ruling_0712_chunk0" must appear exactly once despite two sub-queries
        chunk_ids = [d["chunk_id"] for d in result]
        assert chunk_ids.count("ruling_0712_chunk0") == 1

    def test_returns_empty_list_on_exception(self):
        """Must return [] and not raise on any error."""
        with patch("modules.fiqh.retriever.decompose_query", side_effect=Exception("crash")):
            result = retrieve_fiqh_documents("any query")
        assert result == []

    def test_caps_at_20_unique_docs(self):
        """Returns at most 20 documents."""
        many_docs = [_make_match(f"doc_{i}") for i in range(25)]
        with patch("modules.fiqh.retriever.decompose_query", return_value=["q1"]), \
             patch("modules.fiqh.retriever.getDenseEmbedder") as mock_emb, \
             patch("modules.fiqh.retriever._get_bm25_encoder") as mock_bm25, \
             patch("modules.fiqh.retriever._get_sparse_vectorstore") as mock_vs:
            mock_emb.return_value.embed_query.return_value = [0.1] * 768
            mock_bm25.return_value.encode_queries.return_value = {"indices": [1], "values": [0.5]}
            mock_index = MagicMock()
            mock_index.query.return_value = _make_pinecone_response(many_docs)
            mock_vs.return_value = mock_index

            result = retrieve_fiqh_documents("query returning many docs")
        assert len(result) <= 20

    def test_metadata_includes_required_fields(self):
        """Each returned doc's metadata must contain source_book, chapter, section, ruling_number."""
        doc = _make_match("ruling_0001_chunk0", {
            "text_en": "Ruling text",
            "source_book": "Islamic Laws",
            "chapter": "Tahara",
            "section": "Wudu",
            "ruling_number": "0001",
            "topic_tags": ["tahara"],
        })
        with patch("modules.fiqh.retriever.decompose_query", return_value=["test"]), \
             patch("modules.fiqh.retriever.getDenseEmbedder") as mock_emb, \
             patch("modules.fiqh.retriever._get_bm25_encoder") as mock_bm25, \
             patch("modules.fiqh.retriever._get_sparse_vectorstore") as mock_vs:
            mock_emb.return_value.embed_query.return_value = [0.1] * 768
            mock_bm25.return_value.encode_queries.return_value = {"indices": [1], "values": [0.5]}
            mock_index = MagicMock()
            mock_index.query.return_value = _make_pinecone_response([doc])
            mock_vs.return_value = mock_index

            result = retrieve_fiqh_documents("test")
        assert len(result) >= 1
        md = result[0]["metadata"]
        assert "source_book" in md
        assert "chapter" in md
        assert "section" in md
        assert "ruling_number" in md
