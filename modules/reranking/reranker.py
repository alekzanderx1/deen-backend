from collections import defaultdict
from core.config import DENSE_RESULT_WEIGHT, SPARSE_RESULT_WEIGHT
from core import utils

def rerank_documents(dense_results, sparse_results, no_of_docs):
    """
    Merges and reranks documents based on their dense and sparse scores.
    """
    print("INSIDE rerank_documents")

    # Normalize dense and sparse scores in-place
    normalize_inplace(dense_results, 1)
    normalize_inplace(sparse_results.get("matches", []), "score")

    combined_with_weighted_scores = defaultdict(lambda: {"dense_score": float(0.0), "sparse_score": float(0.0), "metadata": {}, "page_content_en": "","page_content_ar":""})

    # Add dense docs
    for doc, score in dense_results:
        page_content_english_decompressed = utils.decompress_text(getattr(doc,"page_content"))
        page_content_arabic_decompressed = utils.decompress_text(getattr(doc, "metadata").get("text_ar", ""))
        hadith_id = getattr(doc, "metadata").get("hadith_id")
        combined_with_weighted_scores[hadith_id]["dense_score"] += float(score)*float(DENSE_RESULT_WEIGHT)
        combined_with_weighted_scores[hadith_id]["metadata"] = getattr(doc, "metadata", {})
        combined_with_weighted_scores[hadith_id]["page_content_en"] = page_content_english_decompressed
        combined_with_weighted_scores[hadith_id]["page_content_ar"] = page_content_arabic_decompressed

    # Add sparse docs
    for match in sparse_results.get("matches", []):
        page_content_english_decompressed = utils.decompress_text(match.get("metadata", {}).get("text_en", ""))
        page_content_arabic_decompressed = utils.decompress_text(match.get("metadata", {}).get("text_ar", ""))
        hadith_id = match.get("metadata").get("hadith_id", None)
        combined_with_weighted_scores[hadith_id]["sparse_score"] += match.get("score", 0) * float(SPARSE_RESULT_WEIGHT)
        if not combined_with_weighted_scores[hadith_id]["metadata"]:
            combined_with_weighted_scores[hadith_id]["metadata"] = match.get("metadata")
        if not combined_with_weighted_scores[hadith_id]["page_content_en"]:
            combined_with_weighted_scores[hadith_id]["page_content_en"] = page_content_english_decompressed
        if not combined_with_weighted_scores[hadith_id]["page_content_ar"]:
            combined_with_weighted_scores[hadith_id]["page_content_ar"] = page_content_arabic_decompressed

    # Sort by combined score (dense + sparse)
    sorted_combined_docs = sorted(
        combined_with_weighted_scores.items(),
        key=lambda item: item[1]["dense_score"] + item[1]["sparse_score"],
        reverse=True
    )

    # return top no_of_docs from the sorted results
    return [
        {
            "hadith_id": hadith_id,
            "metadata": data["metadata"],
            "page_content_en": data["page_content_en"],
            "page_content_ar": data["page_content_ar"]
        }
        for hadith_id, data in sorted_combined_docs[:no_of_docs]
    ]

def normalize_inplace(items, score_key):
    """Normalize the scores in-place for a list of items (dicts or tuples)."""
    print(type(items[1]))
    scores = [item[1] if isinstance(item, tuple) else item[score_key] for item in items]
    if not scores:
        return
    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        norm = lambda _: 1.0
    else:
        norm = lambda s: (s - min_score) / (max_score - min_score)
    for i, item in enumerate(items):
        if isinstance(item, tuple):
            # For tuple (dense results) (doc, score), replace with (doc, normalized_score)
            items[i] = (item[0], norm(item[1]))
        else:
            # For dict (sparse results), normalize the score in-place
            item[score_key] = norm(item[score_key])
