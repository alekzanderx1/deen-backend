"""
modules/fiqh/retriever.py

Hybrid fiqh retrieval with inline Reciprocal Rank Fusion (RRF).
Public interface: retrieve_fiqh_documents(query) -> list[dict]

Architecture:
  1. Decompose query into 1-4 sub-queries (via decomposer)
  2. For each sub-query: dense query + sparse query against dedicated fiqh indexes
  3. Merge with RRF (k=60), retain top-5 per sub-query
  4. Deduplicate across sub-queries, return up to 20 unique docs
"""
from __future__ import annotations

import logging
import traceback
from pathlib import Path

from pinecone_text.sparse import BM25Encoder

from core.config import DEEN_FIQH_DENSE_INDEX_NAME, DEEN_FIQH_SPARSE_INDEX_NAME
from core.vectorstore import _get_sparse_vectorstore
from modules.embedding.embedder import getDenseEmbedder
from modules.fiqh.decomposer import decompose_query

logger = logging.getLogger(__name__)

# Resolve BM25 encoder path relative to this file — works regardless of process cwd
BM25_ENCODER_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "fiqh_bm25_encoder.json"

# Module-level lazy singleton — loaded once on first call
_bm25_encoder: BM25Encoder | None = None


def _get_bm25_encoder() -> BM25Encoder:
    """Load BM25Encoder from disk on first call, then cache."""
    global _bm25_encoder
    if _bm25_encoder is None:
        enc = BM25Encoder()
        enc.load(str(BM25_ENCODER_PATH))
        _bm25_encoder = enc
    return _bm25_encoder


def _rrf_merge(
    dense_matches: list,
    sparse_matches: list,
    k: int = 60,
    top_n: int = 5,
) -> list[dict]:
    """
    Merge dense and sparse Pinecone match objects using Reciprocal Rank Fusion.

    RRF score for each document = sum of 1/(k + rank) across result lists.
    Rank is 0-based position in the list (already sorted by relevance).

    Args:
        dense_matches: Pinecone match objects from dense index query (list of match objects)
        sparse_matches: Pinecone match objects from sparse index query (list of match objects)
        k: RRF smoothing constant (default 60, standard value from literature)
        top_n: Number of top documents to return after merge

    Returns:
        list[dict]: Up to top_n documents in RRF-ranked order, each with
                    chunk_id, metadata, and page_content.
    """
    scores: dict[str, float] = {}
    metadata_store: dict[str, dict] = {}
    content_store: dict[str, str] = {}

    # Dense pass — rank by position (dense_matches already sorted descending by score)
    for rank, match in enumerate(dense_matches):
        chunk_id = match.id
        md = match.metadata or {}
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
        metadata_store[chunk_id] = md
        content_store[chunk_id] = md.get("text_en", "")

    # Sparse pass — rank by position (sparse_matches already sorted descending by score)
    for rank, match in enumerate(sparse_matches):
        chunk_id = match.id
        md = match.metadata or {}
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
        if chunk_id not in metadata_store:
            metadata_store[chunk_id] = md
        if chunk_id not in content_store:
            content_store[chunk_id] = md.get("text_en", "")

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)[:top_n]
    return [
        {
            "chunk_id": cid,
            "metadata": metadata_store[cid],
            "page_content": content_store[cid],
        }
        for cid in sorted_ids
    ]


def _retrieve_for_sub_query(sub_query: str) -> list[dict]:
    """
    Dense + sparse retrieval + RRF merge for a single sub-query.
    Returns up to 5 documents. Returns [] on any error.
    """
    try:
        # Dense retrieval via raw Pinecone index (same pattern as retrieve_quran_documents)
        dense_vec = getDenseEmbedder().embed_query(sub_query)
        dense_index = _get_sparse_vectorstore(DEEN_FIQH_DENSE_INDEX_NAME)
        dense_response = dense_index.query(
            vector=dense_vec,
            top_k=20,
            include_metadata=True,
            namespace="ns1",
        )
        dense_matches = dense_response.matches if hasattr(dense_response, "matches") else \
                        dense_response.get("matches", [])

        # Sparse retrieval — MUST use sparse_vector= (not vector=) for sparse-type index
        encoder = _get_bm25_encoder()
        sparse_vec = encoder.encode_queries(sub_query)
        sparse_index = _get_sparse_vectorstore(DEEN_FIQH_SPARSE_INDEX_NAME)
        sparse_response = sparse_index.query(
            sparse_vector=sparse_vec,
            top_k=20,
            include_metadata=True,
            namespace="ns1",
        )
        sparse_matches = sparse_response.matches if hasattr(sparse_response, "matches") else \
                         sparse_response.get("matches", [])

        return _rrf_merge(dense_matches, sparse_matches, k=60, top_n=5)

    except Exception as e:
        logger.error("[FIQH_RETRIEVER] sub-query retrieval error: %s\n%s", e, traceback.format_exc())
        return []


def retrieve_fiqh_documents(query: str) -> list[dict]:
    """
    Public interface for Phase 3 evidence assessment.

    Decomposes the query into sub-queries, retrieves top-5 per sub-query via
    hybrid dense+sparse search with RRF merging, deduplicates by chunk_id.

    Args:
        query: Original fiqh query string

    Returns:
        list[dict]: Up to 20 unique documents, each with:
            - chunk_id (str): Pinecone vector ID (e.g. "ruling_0712_chunk0")
            - metadata (dict): source_book, chapter, section, ruling_number, topic_tags, text_en
            - page_content (str): The ruling text (same as metadata["text_en"])

        Returns [] on total failure. Never raises.
    """
    try:
        sub_queries = decompose_query(query)
        seen: set[str] = set()
        result: list[dict] = []
        for sq in sub_queries:
            for doc in _retrieve_for_sub_query(sq):
                if doc["chunk_id"] not in seen:
                    seen.add(doc["chunk_id"])
                    result.append(doc)
        return result[:20]
    except Exception as e:
        logger.error("[FIQH_RETRIEVER] retrieve_fiqh_documents error: %s", e)
        return []
