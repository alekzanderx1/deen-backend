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
from pinecone import Pinecone, ServerlessSpec
from pinecone.db_data.dataclasses import Vector
from pinecone_text.sparse import BM25Encoder

from core.config import (
    DEEN_DENSE_INDEX_NAME,
    DEEN_FIQH_DENSE_INDEX_NAME,
    DEEN_FIQH_SPARSE_INDEX_NAME,
    PINECONE_API_KEY,
)
from core.logging_config import setup_logging
from modules.embedding.embedder import getDenseEmbedder

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

    Full ingestion pipeline:
    1. Download NLTK data
    2. Create Pinecone indexes (idempotent)
    3. Fit BM25 encoder on all chunk texts and persist
    4. Embed all chunks (dense) in sub-batches of 32
    5. Encode all chunks (sparse) with BM25
    6. Upsert to dense index in batches of UPSERT_BATCH_SIZE
    7. Upsert to sparse index in batches of UPSERT_BATCH_SIZE
    """
    # --- Guard env vars ---
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY is not set in .env")
    if not DEEN_FIQH_DENSE_INDEX_NAME:
        raise ValueError("DEEN_FIQH_DENSE_INDEX_NAME is not set in .env")
    if not DEEN_FIQH_SPARSE_INDEX_NAME:
        raise ValueError("DEEN_FIQH_SPARSE_INDEX_NAME is not set in .env")

    # --- Step 1: NLTK data (required by BM25Encoder) ---
    logger.info("Downloading NLTK data...")
    ssl._create_default_https_context = ssl._create_unverified_context  # macOS workaround
    nltk.download("stopwords", quiet=True)
    nltk.download("punkt_tab", quiet=True)

    # --- Step 2: Pinecone index creation (idempotent) ---
    logger.info("Initialising Pinecone client...")
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Discover cloud/region from existing index to satisfy D-09
    existing_names = [i.name for i in pc.list_indexes()]
    if DEEN_DENSE_INDEX_NAME and DEEN_DENSE_INDEX_NAME in existing_names:
        existing_spec = pc.describe_index(DEEN_DENSE_INDEX_NAME).spec.serverless
        cloud = existing_spec.cloud
        region = existing_spec.region
        logger.info(
            "Using cloud=%s region=%s (from existing %s index)",
            cloud,
            region,
            DEEN_DENSE_INDEX_NAME,
        )
    else:
        cloud, region = "aws", "us-east-1"
        logger.warning(
            "Could not read existing index spec; defaulting to cloud=%s region=%s",
            cloud,
            region,
        )

    if DEEN_FIQH_DENSE_INDEX_NAME not in existing_names:
        logger.info(
            "Creating dense fiqh index: %s (768 dims, cosine)", DEEN_FIQH_DENSE_INDEX_NAME
        )
        pc.create_index(
            name=DEEN_FIQH_DENSE_INDEX_NAME,
            dimension=768,
            metric="cosine",
            vector_type="dense",
            spec=ServerlessSpec(cloud=cloud, region=region),
        )
        logger.info("Waiting for dense index to become ready...")
        time.sleep(10)  # Pinecone serverless provisioning delay (Pitfall 7)
    else:
        logger.info("Dense fiqh index already exists: %s", DEEN_FIQH_DENSE_INDEX_NAME)

    if DEEN_FIQH_SPARSE_INDEX_NAME not in existing_names:
        logger.info(
            "Creating sparse fiqh index: %s (dotproduct)", DEEN_FIQH_SPARSE_INDEX_NAME
        )
        pc.create_index(
            name=DEEN_FIQH_SPARSE_INDEX_NAME,
            metric="dotproduct",
            vector_type="sparse",  # NO dimension parameter (Pitfall 2)
            spec=ServerlessSpec(cloud=cloud, region=region),
        )
        logger.info("Waiting for sparse index to become ready...")
        time.sleep(10)
    else:
        logger.info("Sparse fiqh index already exists: %s", DEEN_FIQH_SPARSE_INDEX_NAME)

    # --- Step 3: Fit BM25 encoder on full corpus and persist ---
    chunk_texts: list[str] = [c["text"] for c in chunks]
    logger.info("Fitting BM25 encoder on %d chunk texts...", len(chunk_texts))
    encoder = BM25Encoder()
    encoder.fit(chunk_texts)  # Must fit before encode (Pitfall 3)

    encoder_path = BM25_ENCODER_PATH
    Path(encoder_path).parent.mkdir(parents=True, exist_ok=True)
    encoder.dump(encoder_path)
    logger.info("BM25 encoder persisted to %s", encoder_path)

    # --- Step 4: Dense embedding in sub-batches of 32 (Pitfall 6) ---
    logger.info("Loading dense embedder (all-mpnet-base-v2)...")
    embedder = getDenseEmbedder()
    dense_vecs: list[list[float]] = []
    embed_batch_size = 32
    for i in range(0, len(chunks), embed_batch_size):
        batch_texts = chunk_texts[i : i + embed_batch_size]
        batch_vecs = embedder.embed_documents(batch_texts)
        dense_vecs.extend(batch_vecs)
        logger.info(
            "Embedded %d/%d chunks", min(i + embed_batch_size, len(chunks)), len(chunks)
        )

    # --- Step 5: Sparse encoding (BM25) ---
    logger.info("Encoding sparse vectors with BM25...")
    sparse_vecs = encoder.encode_documents(chunk_texts)  # list of {"indices": [...], "values": [...]}

    # --- Step 6: Dense upsert in batches of UPSERT_BATCH_SIZE ---
    dense_idx = pc.Index(DEEN_FIQH_DENSE_INDEX_NAME)
    total = len(chunks)
    for batch_start in range(0, total, UPSERT_BATCH_SIZE):
        batch_chunks = chunks[batch_start : batch_start + UPSERT_BATCH_SIZE]
        batch_dense = dense_vecs[batch_start : batch_start + UPSERT_BATCH_SIZE]
        vectors = [
            Vector(
                id=chunk["id"],
                values=dense_vec,
                metadata={
                    "text_en": chunk["text"],
                    "source_book": chunk["source_book"],
                    "chapter": chunk["chapter"],
                    "section": chunk["section"],
                    "ruling_number": chunk["ruling_number"],
                    "topic_tags": chunk["topic_tags"],
                },
            )
            for chunk, dense_vec in zip(batch_chunks, batch_dense)
        ]
        dense_idx.upsert(vectors=vectors, namespace="ns1")
        uploaded = min(batch_start + UPSERT_BATCH_SIZE, total)
        logger.info("Uploaded %d/%d chunks to dense index", uploaded, total)

    # --- Step 7: Sparse upsert in batches of UPSERT_BATCH_SIZE ---
    sparse_idx = pc.Index(DEEN_FIQH_SPARSE_INDEX_NAME)
    for batch_start in range(0, total, UPSERT_BATCH_SIZE):
        batch_chunks = chunks[batch_start : batch_start + UPSERT_BATCH_SIZE]
        batch_sparse = sparse_vecs[batch_start : batch_start + UPSERT_BATCH_SIZE]
        vectors_sparse = [
            {
                "id": chunk["id"],
                "sparse_values": {
                    "indices": sv["indices"],
                    "values": sv["values"],
                },
                "metadata": {
                    "text_en": chunk["text"],
                    "source_book": chunk["source_book"],
                    "chapter": chunk["chapter"],
                    "section": chunk["section"],
                    "ruling_number": chunk["ruling_number"],
                    "topic_tags": chunk["topic_tags"],
                },
            }
            for chunk, sv in zip(batch_chunks, batch_sparse)
        ]
        sparse_idx.upsert(vectors=vectors_sparse, namespace="ns1")
        uploaded = min(batch_start + UPSERT_BATCH_SIZE, total)
        logger.info("Uploaded %d/%d chunks to sparse index", uploaded, total)

    logger.info("Ingestion complete. %d chunks in both fiqh indexes.", total)


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
    parser.add_argument(
        "--encoder-only",
        action="store_true",
        help="Fit and save the BM25 encoder only; skip Pinecone indexing",
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

    if args.encoder_only:
        import ssl as _ssl
        import nltk
        _ssl._create_default_https_context = _ssl._create_unverified_context
        nltk.download("stopwords", quiet=True)
        nltk.download("punkt_tab", quiet=True)
        chunk_texts = [c["text"] for c in chunks]
        logger.info("Fitting BM25 encoder on %d chunks...", len(chunk_texts))
        encoder = BM25Encoder()
        encoder.fit(chunk_texts)
        Path(BM25_ENCODER_PATH).parent.mkdir(parents=True, exist_ok=True)
        encoder.dump(BM25_ENCODER_PATH)
        logger.info("BM25 encoder saved to %s", BM25_ENCODER_PATH)
        return

    # Embedding and upsert (implemented in plan 03)
    _run_ingestion(chunks)


if __name__ == "__main__":
    main()
