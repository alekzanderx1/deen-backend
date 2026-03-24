"""
Ingest Sistani's Islamic Laws (4th edition) into dedicated Pinecone fiqh indexes.

Usage:
    python scripts/ingest_fiqh.py                    # Full ingestion
    python scripts/ingest_fiqh.py --dry-run          # Parse only, no upload
    python scripts/ingest_fiqh.py --pdf-path /custom/path.pdf
"""
from __future__ import annotations

import argparse
import logging
import re
import ssl
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to sys.path (required for local imports)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import fitz  # pymupdf
import nltk
import tiktoken
from langchain_text_splitters import TokenTextSplitter

from core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Constants
# ------------------------------------------------------------------ #

PDF_PATH = str(
    project_root / "documentation" / "fiqh_related_docs" / "english-islamic-laws-4th-edition.pdf"
)
BM25_ENCODER_PATH = str(project_root / "data" / "fiqh_bm25_encoder.json")
SOURCE_BOOK = "Islamic Laws 4th Edition"

RULING_PATTERN = re.compile(r"(Ruling\s+(\d+)\.)")
CHAPTER_PATTERN = re.compile(
    r"CHAPTER\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE)",
    re.IGNORECASE,
)
# Section heading: digit(s) + period + space + non-whitespace character
SECTION_PATTERN = re.compile(r"^\d+\.\s+\S[^\n]*", re.MULTILINE)

MIN_CHUNK_TOKENS = 20
MAX_CHUNK_TOKENS = 400
TARGET_CHUNK_TOKENS = 350
UPSERT_BATCH_SIZE = 100

ENCODING = tiktoken.get_encoding("cl100k_base")

CHAPTER_TOPIC_MAP: dict[str, str] = {
    "ONE": "taqlid",
    "TWO": "tahara",
    "THREE": "salah",
    "FOUR": "fasting",
    "FIVE": "khums",
    "SIX": "zakat",
    "SEVEN": "hajj",
    "EIGHT": "trade",
    "NINE": "marriage",
    "TEN": "divorce",
    "ELEVEN": "inheritance",
    "TWELVE": "miscellaneous",
}


# ------------------------------------------------------------------ #
# Parsing functions
# ------------------------------------------------------------------ #

def parse_pdf(pdf_path: str) -> str:
    """Extract full text from PDF, joining all pages with newlines."""
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    full_text = "\n".join(pages)
    logger.info("Extracted %d pages from %s", len(pages), pdf_path)
    return full_text


def assign_topic_tag(chapter: str) -> str:
    """Map chapter ordinal word to canonical topic tag.

    Args:
        chapter: Chapter string, e.g. "CHAPTER TWO" or empty string.

    Returns:
        Canonical topic tag, e.g. "tahara", or "general" if not found.
    """
    for key, tag in CHAPTER_TOPIC_MAP.items():
        if key.lower() in chapter.lower():
            return tag
    return "general"


def chunk_rulings(full_text: str) -> list[dict[str, Any]]:
    """Split text into ruling-boundary chunks with chapter/section/topic metadata.

    Each returned dict has keys:
        id, text, source_book, chapter, section, ruling_number, topic_tags

    Phantom cross-reference fragments (< MIN_CHUNK_TOKENS tokens) are filtered
    out. Rulings exceeding MAX_CHUNK_TOKENS are split at paragraph boundaries
    via TokenTextSplitter.

    Args:
        full_text: Raw full-document text extracted from the PDF.

    Returns:
        List of chunk dicts suitable for Pinecone upsert metadata.
    """
    # ---- Step 1: Build chapter position map by scanning once ----
    chapter_positions: list[tuple[int, str]] = []
    for m in CHAPTER_PATTERN.finditer(full_text):
        chapter_positions.append((m.start(), m.group(0)))

    # ---- Step 2: Build section position map ----
    section_positions: list[tuple[int, str]] = []
    for m in SECTION_PATTERN.finditer(full_text):
        line = m.group(0).strip()
        # Only treat short lines as section headings (not ruling body text)
        if len(line) < 80:
            section_positions.append((m.start(), line))

    # ---- Step 3: Secondary splitter for oversized rulings ----
    splitter = TokenTextSplitter(
        encoding_name="cl100k_base",
        chunk_size=TARGET_CHUNK_TOKENS,
        chunk_overlap=0,
    )

    # ---- Step 4: Split full text on ruling boundaries ----
    parts = RULING_PATTERN.split(full_text)
    # parts layout after split:
    #   parts[0]           — preamble (before first ruling)
    #   parts[1]           — "Ruling N." (full match group 1)
    #   parts[2]           — "N"         (ruling number, group 2)
    #   parts[3]           — body text up to next ruling
    #   parts[4]           — "Ruling M."
    #   parts[5]           — "M"
    #   parts[6]           — body text
    #   ...
    # So valid ruling triples start at index 1, stride 3.

    chunks: list[dict[str, Any]] = []
    # Track character offset as we walk through parts
    position_offset: int = len(parts[0]) if parts else 0
    last_ruling_number: int = 0
    # Track seen ruling numbers to skip duplicate matches (cross-references in footnotes/appendices)
    seen_ruling_numbers: set[int] = set()

    i = 1  # skip preamble at parts[0]
    while i + 2 < len(parts):
        ruling_header: str = parts[i]       # e.g. "Ruling 712."
        ruling_num_str: str = parts[i + 1]  # e.g. "712"
        body: str = parts[i + 2]            # ruling body text (until next ruling or EOF)
        i += 3

        ruling_number = int(ruling_num_str)

        # Skip duplicate ruling numbers — only process first occurrence of each ruling.
        # The PDF contains inline cross-references like "see Ruling 712." which the regex
        # matches; these always appear after the real ruling and produce duplicate entries.
        if ruling_number in seen_ruling_numbers:
            position_offset += len(ruling_header) + len(ruling_num_str) + len(body)
            continue
        seen_ruling_numbers.add(ruling_number)

        last_ruling_number = ruling_number
        ruling_text = f"{ruling_header} {body.strip()}"

        # Determine character position of this ruling in the original text
        current_pos = position_offset
        position_offset += len(ruling_header) + len(ruling_num_str) + len(body)

        # Look up the latest chapter/section that started at or before current_pos
        chapter = ""
        for pos, chap in chapter_positions:
            if pos <= current_pos:
                chapter = chap

        section = ""
        for pos, sec in section_positions:
            if pos <= current_pos:
                section = sec

        topic_tag = assign_topic_tag(chapter)

        # Determine sub-chunks
        token_count = len(ENCODING.encode(ruling_text))
        if token_count <= MAX_CHUNK_TOKENS:
            sub_texts = [ruling_text]
        else:
            sub_texts = splitter.split_text(ruling_text)

        for chunk_idx, sub_text in enumerate(sub_texts):
            if len(ENCODING.encode(sub_text)) < MIN_CHUNK_TOKENS:
                continue  # Filter phantom cross-reference fragments
            chunks.append(
                {
                    "id": f"fiqh-{ruling_number}-{chunk_idx}",
                    "text": sub_text,
                    "source_book": SOURCE_BOOK,
                    "chapter": chapter,
                    "section": section,
                    "ruling_number": ruling_number,
                    "topic_tags": [topic_tag],
                }
            )

    logger.info(
        "Produced %d chunks from %d rulings", len(chunks), last_ruling_number
    )
    return chunks


# ------------------------------------------------------------------ #
# Ingestion stub (implemented in plan 03)
# ------------------------------------------------------------------ #

def _run_ingestion(chunks: list[dict[str, Any]]) -> None:
    """Embed and upsert all chunks into Pinecone fiqh indexes.

    Implemented in plan 03. Calling this in plan 02 raises NotImplementedError.
    """
    raise NotImplementedError("Embedding and Pinecone upsert implemented in plan 03")


# ------------------------------------------------------------------ #
# CLI entry point
# ------------------------------------------------------------------ #

def main() -> None:
    """Parse CLI arguments and run the ingestion pipeline."""
    parser = argparse.ArgumentParser(
        description="Ingest Sistani Islamic Laws into Pinecone fiqh indexes"
    )
    parser.add_argument(
        "--pdf-path",
        default=PDF_PATH,
        help="Path to the Islamic Laws PDF (default: documentation/fiqh_related_docs/english-islamic-laws-4th-edition.pdf)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse only; do not embed or upload",
    )
    args = parser.parse_args()

    logger.info("Loading PDF from %s", args.pdf_path)
    full_text = parse_pdf(args.pdf_path)

    logger.info("Chunking text at ruling boundaries...")
    chunks = chunk_rulings(full_text)
    logger.info("Total chunks: %d", len(chunks))

    if args.dry_run:
        logger.info("--- DRY RUN: first 5 chunks ---")
        for chunk in chunks[:5]:
            logger.info(
                "  id=%s ruling=%d chapter=%r section=%r tokens=%d",
                chunk["id"],
                chunk["ruling_number"],
                chunk["chapter"],
                chunk["section"],
                len(ENCODING.encode(chunk["text"])),
            )
        logger.info("Dry run complete. No data uploaded.")
        return

    # Embedding and upsert (implemented in plan 03)
    _run_ingestion(chunks)


if __name__ == "__main__":
    main()
