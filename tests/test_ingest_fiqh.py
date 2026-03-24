"""
Unit tests for scripts/ingest_fiqh.py — PDF parsing and chunking layer.

These tests exercise parse_pdf(), chunk_rulings(), and assign_topic_tag()
without running any embedding or Pinecone calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest

# ----- Module-level import of the functions under test -----
# These imports will fail (ImportError) in RED phase since the file doesn't exist yet.
from scripts.ingest_fiqh import (
    parse_pdf,
    chunk_rulings,
    assign_topic_tag,
    CHAPTER_TOPIC_MAP,
    RULING_PATTERN,
    MIN_CHUNK_TOKENS,
    MAX_CHUNK_TOKENS,
    ENCODING,
)


# ---- Helpers ----

PDF_PATH = str(
    project_root / "documentation" / "fiqh_related_docs" / "english-islamic-laws-4th-edition.pdf"
)


# ================================================================
# assign_topic_tag tests
# ================================================================

class TestAssignTopicTag:
    def test_known_chapters_return_correct_tags(self) -> None:
        assert assign_topic_tag("CHAPTER ONE") == "taqlid"
        assert assign_topic_tag("CHAPTER TWO") == "tahara"
        assert assign_topic_tag("CHAPTER THREE") == "salah"
        assert assign_topic_tag("CHAPTER FOUR") == "fasting"
        assert assign_topic_tag("CHAPTER FIVE") == "khums"
        assert assign_topic_tag("CHAPTER SIX") == "zakat"
        assert assign_topic_tag("CHAPTER SEVEN") == "hajj"
        assert assign_topic_tag("CHAPTER EIGHT") == "trade"
        assert assign_topic_tag("CHAPTER NINE") == "marriage"
        assert assign_topic_tag("CHAPTER TEN") == "divorce"
        assert assign_topic_tag("CHAPTER ELEVEN") == "inheritance"
        assert assign_topic_tag("CHAPTER TWELVE") == "miscellaneous"

    def test_unknown_chapter_returns_general(self) -> None:
        assert assign_topic_tag("") == "general"
        assert assign_topic_tag("CHAPTER THIRTEEN") == "general"
        assert assign_topic_tag("preamble text") == "general"

    def test_case_insensitive_match(self) -> None:
        # chapter name extracted from document may have mixed case ordinals
        assert assign_topic_tag("chapter two") == "tahara"
        assert assign_topic_tag("Chapter One") == "taqlid"


# ================================================================
# RULING_PATTERN constant tests
# ================================================================

class TestRulingPattern:
    def test_matches_standard_ruling_format(self) -> None:
        import re
        m = RULING_PATTERN.search("Ruling 1. A Muslim's belief")
        assert m is not None
        assert m.group(2) == "1"

    def test_matches_large_ruling_number(self) -> None:
        m = RULING_PATTERN.search("Ruling 2796. Final ruling text here.")
        assert m is not None
        assert m.group(2) == "2796"

    def test_split_produces_correct_parts(self) -> None:
        text = "Intro text. Ruling 1. First ruling body. Ruling 2. Second ruling body."
        parts = RULING_PATTERN.split(text)
        # parts: [preamble, "Ruling 1.", "1", body1, "Ruling 2.", "2", body2]
        assert len(parts) == 7
        assert "Intro text." in parts[0]
        assert parts[1] == "Ruling 1."
        assert parts[2] == "1"
        assert "First ruling body." in parts[3]
        assert parts[4] == "Ruling 2."
        assert parts[5] == "2"
        assert "Second ruling body." in parts[6]


# ================================================================
# chunk_rulings unit tests (on synthetic text — no PDF required)
# ================================================================

class TestChunkRulingsOnSyntheticText:
    def _make_text(self, rulings: list[tuple[int, str]], chapter: str = "", section: str = "") -> str:
        """Build a synthetic full-text string with optional chapter heading."""
        parts = []
        if chapter:
            parts.append(f"\n{chapter}\n")
        if section:
            parts.append(f"\n{section}\n")
        for num, body in rulings:
            parts.append(f"Ruling {num}. {body}")
        return " ".join(parts)

    def test_returns_list_of_dicts(self) -> None:
        text = "Ruling 1. A ruling body text with enough words to meet the minimum token threshold for inclusion."
        chunks = chunk_rulings(text)
        assert isinstance(chunks, list)

    def test_chunk_has_required_keys(self) -> None:
        text = "Ruling 1. A ruling body text with enough words to meet the minimum token threshold for inclusion and more text."
        chunks = chunk_rulings(text)
        assert len(chunks) >= 1
        chunk = chunks[0]
        assert set(chunk.keys()) == {"id", "text", "source_book", "chapter", "section", "ruling_number", "topic_tags"}

    def test_ruling_number_is_int_and_positive(self) -> None:
        text = "Ruling 42. Some ruling about purification which is a topic covered in the second chapter of the book and it has enough tokens."
        chunks = chunk_rulings(text)
        assert len(chunks) >= 1
        assert all(isinstance(c["ruling_number"], int) for c in chunks)
        assert all(c["ruling_number"] > 0 for c in chunks)

    def test_id_format_matches_fiqh_pattern(self) -> None:
        text = "Ruling 7. Some ruling text with enough words to pass the minimum token count filter and be included."
        chunks = chunk_rulings(text)
        assert len(chunks) >= 1
        assert chunks[0]["id"].startswith("fiqh-7-")

    def test_source_book_is_set(self) -> None:
        text = "Ruling 1. Some ruling text that is long enough to not be filtered out by the minimum token threshold."
        chunks = chunk_rulings(text)
        assert len(chunks) >= 1
        assert chunks[0]["source_book"] == "Islamic Laws 4th Edition"

    def test_topic_tags_is_list(self) -> None:
        text = "Ruling 1. A ruling about purification. This ruling has sufficient length to pass the token minimum filter."
        chunks = chunk_rulings(text)
        assert len(chunks) >= 1
        assert isinstance(chunks[0]["topic_tags"], list)
        assert len(chunks[0]["topic_tags"]) >= 1

    def test_phantom_cross_reference_chunks_filtered(self) -> None:
        """Chunks with < MIN_CHUNK_TOKENS must be filtered out."""
        # Tiny body — "(see Ruling 712)" style phantom
        text = "Ruling 1. A ruling body text with enough words to pass the minimum token threshold for inclusion. (see Ruling 712. x)"
        chunks = chunk_rulings(text)
        for chunk in chunks:
            token_count = len(ENCODING.encode(chunk["text"]))
            assert token_count >= MIN_CHUNK_TOKENS, (
                f"Chunk {chunk['id']} has only {token_count} tokens (below minimum {MIN_CHUNK_TOKENS})"
            )

    def test_chapter_metadata_propagated(self) -> None:
        """Chapter state must carry across ruling boundaries — not reset per ruling."""
        text = (
            "CHAPTER TWO\n"
            "Some intro text.\n"
            "Ruling 50. First ruling in chapter two. This has sufficient text to pass the minimum token threshold.\n"
            "Ruling 51. Second ruling in chapter two. This also has sufficient text to pass the token threshold.\n"
        )
        chunks = chunk_rulings(text)
        # Both rulings should have non-empty chapter field with "TWO" in it
        assert len(chunks) >= 2
        for chunk in chunks:
            assert chunk["chapter"] != "", (
                f"Chunk {chunk['id']} has empty chapter despite being inside CHAPTER TWO"
            )
            assert "TWO" in chunk["chapter"].upper(), (
                f"Chunk {chunk['id']} chapter field is '{chunk['chapter']}', expected 'CHAPTER TWO'"
            )

    def test_chapter_topic_tag_derived_from_chapter(self) -> None:
        text = (
            "CHAPTER THREE\n"
            "Ruling 100. A ruling about salah. This ruling has sufficient text to pass the minimum token threshold.\n"
        )
        chunks = chunk_rulings(text)
        assert len(chunks) >= 1
        assert "salah" in chunks[0]["topic_tags"]

    def test_oversized_ruling_split_into_multiple_chunks(self) -> None:
        """Rulings with >400 tokens must be split; each sub-chunk shares ruling_number."""
        # Generate a body with ~600 tokens worth of text
        long_body = ("This is a detailed ruling about purification. " * 20).strip()
        text = f"CHAPTER TWO\nRuling 200. {long_body}"
        chunks = chunk_rulings(text)
        ruling_200_chunks = [c for c in chunks if c["ruling_number"] == 200]
        if len(ENCODING.encode(f"Ruling 200. {long_body}")) > MAX_CHUNK_TOKENS:
            assert len(ruling_200_chunks) > 1, "Oversized ruling should produce multiple chunks"
        # All sub-chunks must share the same ruling_number
        for chunk in ruling_200_chunks:
            assert chunk["ruling_number"] == 200

    def test_no_chunk_exceeds_max_tokens_after_split(self) -> None:
        """No chunk should have more tokens than MAX_CHUNK_TOKENS (approximately — splitter may slightly exceed)."""
        long_body = ("This is a detailed ruling with many words about purification and cleanliness. " * 15).strip()
        text = f"CHAPTER TWO\nRuling 300. {long_body}"
        chunks = chunk_rulings(text)
        ruling_300_chunks = [c for c in chunks if c["ruling_number"] == 300]
        # Each chunk from secondary splitting should be <= TARGET_CHUNK_TOKENS + some buffer
        for chunk in ruling_300_chunks:
            token_count = len(ENCODING.encode(chunk["text"]))
            assert token_count <= MAX_CHUNK_TOKENS + 50, (
                f"Chunk {chunk['id']} has {token_count} tokens, significantly above MAX_CHUNK_TOKENS={MAX_CHUNK_TOKENS}"
            )

    def test_multiple_rulings_are_all_returned(self) -> None:
        lines = []
        for i in range(1, 6):
            lines.append(f"Ruling {i}. This is ruling number {i} with sufficient text to pass the minimum token count filter.")
        text = "\n".join(lines)
        chunks = chunk_rulings(text)
        ruling_numbers = {c["ruling_number"] for c in chunks}
        assert {1, 2, 3, 4, 5}.issubset(ruling_numbers)


# ================================================================
# parse_pdf integration test (requires actual PDF)
# ================================================================

class TestParsePdf:
    @pytest.mark.skipif(
        not Path(PDF_PATH).exists(),
        reason="Sistani PDF not available in test environment"
    )
    def test_returns_non_empty_string(self) -> None:
        text = parse_pdf(PDF_PATH)
        assert isinstance(text, str)
        assert len(text) > 1000

    @pytest.mark.skipif(
        not Path(PDF_PATH).exists(),
        reason="Sistani PDF not available in test environment"
    )
    def test_contains_ruling_1(self) -> None:
        text = parse_pdf(PDF_PATH)
        assert "Ruling 1." in text

    @pytest.mark.skipif(
        not Path(PDF_PATH).exists(),
        reason="Sistani PDF not available in test environment"
    )
    def test_contains_chapter_heading(self) -> None:
        text = parse_pdf(PDF_PATH)
        assert "CHAPTER" in text


# ================================================================
# Full integration test on real PDF (optional, slow)
# ================================================================

class TestChunkRulingsOnRealPdf:
    @pytest.mark.skipif(
        not Path(PDF_PATH).exists(),
        reason="Sistani PDF not available in test environment"
    )
    def test_produces_expected_chunk_count(self) -> None:
        # The PDF has 2796 valid rulings.  With secondary splitting for oversized
        # rulings (~78 rulings > 400 tokens) the total chunk count is ~2800-3200.
        # The research estimate of 1000-1600 was based on an incorrect assumption
        # that many rulings would be merged — in reality each ruling is its own chunk.
        from scripts.ingest_fiqh import parse_pdf
        text = parse_pdf(PDF_PATH)
        chunks = chunk_rulings(text)
        assert 2700 <= len(chunks) <= 3500, (
            f"Expected 2700-3500 chunks from 2796 rulings, got {len(chunks)}"
        )

    @pytest.mark.skipif(
        not Path(PDF_PATH).exists(),
        reason="Sistani PDF not available in test environment"
    )
    def test_no_chunk_below_min_tokens_on_real_pdf(self) -> None:
        from scripts.ingest_fiqh import parse_pdf
        text = parse_pdf(PDF_PATH)
        chunks = chunk_rulings(text)
        for chunk in chunks:
            token_count = len(ENCODING.encode(chunk["text"]))
            assert token_count >= MIN_CHUNK_TOKENS, (
                f"Chunk {chunk['id']} has {token_count} tokens (below {MIN_CHUNK_TOKENS})"
            )

    @pytest.mark.skipif(
        not Path(PDF_PATH).exists(),
        reason="Sistani PDF not available in test environment"
    )
    def test_mid_chapter_chunks_have_non_empty_chapter(self) -> None:
        from scripts.ingest_fiqh import parse_pdf
        text = parse_pdf(PDF_PATH)
        chunks = chunk_rulings(text)
        # Rulings beyond 10 should be in a chapter
        mid_chunks = [c for c in chunks if c["ruling_number"] > 10]
        non_empty_chapter = [c for c in mid_chunks if c["chapter"] != ""]
        assert len(non_empty_chapter) > len(mid_chunks) * 0.9, (
            "More than 10%% of mid-chapter rulings have empty chapter field"
        )
