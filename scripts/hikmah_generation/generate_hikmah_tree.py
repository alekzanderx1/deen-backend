"""
Hikmah Tree Lesson Generator Agent

Generates structured Hikmah Tree lessons from raw markdown input files using
a LangGraph sequential pipeline. Each phase is an explicit node that calls
the LLM and/or retrieval functions, updating state directly for reliability.

Usage:
    python scripts/hikmah_generation/generate_hikmah_tree.py

Place input markdown files in scripts/hikmah_generation/input/ before running.
Output goes to scripts/hikmah_generation/output/
"""

import concurrent.futures
import json
import re
import sys
import math
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, TypedDict

# ---------------------------------------------------------------------------
# Project path bootstrap (same pattern as scripts/generate_primers.py)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from modules.retrieval.retriever import retrieve_shia_documents, retrieve_quran_documents

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
INPUT_DIR = SCRIPT_DIR / "input"
OUTPUT_DIR = SCRIPT_DIR / "output"
INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Prompt constants
# ---------------------------------------------------------------------------

CONTENT_SPLIT_SYSTEM = """You are a curriculum designer for a Twelver Shia Islamic education platform.

Your task is to analyze the provided source text and create a structured course outline that will be used to generate educational lessons.

Rules:
- Create {target_lessons} lessons (minimum 4).
- Each lesson should have 2-4 pages of content.
- Each page should contain roughly 300-600 words of substantive educational content.
- Lessons must flow logically, building on each other.
- Preserve ALL Arabic text, Quranic verses, and hadith quotes EXACTLY as they appear in the source -- do not translate, transliterate, or modify them.
- Paraphrase the source material in your own words to avoid plagiarism, but do NOT change the meaning.
- Feel free to reorder topics across lessons if it improves the learning flow.
- Each lesson should have a clear thematic focus.
- Each page needs a descriptive title and a list of 2-4 key topics covered (these will be used to fetch additional references later).

You MUST output ONLY valid JSON with no additional text, using this exact structure:
{{
  "lessons": [
    {{
      "lesson_number": 1,
      "title": "Lesson Title Here",
      "pages": [
        {{
          "page_number": 1,
          "title": "Page Title Here",
          "content": "Full markdown content for this page...",
          "key_topics": ["topic1", "topic2"]
        }}
      ]
    }}
  ]
}}"""

PAGE_ENRICHMENT_SYSTEM = """You are a highly educated Twelver Shia Scholar writing educational content for an Islamic learning platform.

You are given:
1. A draft page of lesson content
2. Retrieved Shia hadith references (may be empty)
3. Retrieved Quran tafsir references (may be empty)

Your task is to enrich the page content by naturally incorporating relevant references where they strengthen the educational material.

IMPORTANT RULES:
- ONLY use references that are genuinely relevant to the page topic. Do NOT force references into the content.
- Preserve ALL existing Arabic text and Quranic verses EXACTLY as written -- do not modify, translate, or remove them.
- Make quoted hadith and Quranic references **bold and italic** and place them on a new line so they stand out.
- Include full citation details for every reference used: hadith number, book name, chapter, author, volume, surah/verse number, tafsir source as applicable.
- Do NOT fabricate any citations. If no relevant references are available, proceed with just the draft content.
- Paraphrase the draft content where possible to avoid plagiarism, without changing the meaning.
- Maintain proper markdown formatting: use headings (##, ###), paragraphs, bullet points, and blank lines between paragraphs.
- Keep the Twelver Shia perspective throughout.
- Target 300-600 words per page.
- When presenting hadith citations, start the reference on a new line and make it bold and italic.
- For Tafsir citations, cite the Surah name, verse range, Tafsir collection, author, and volume.
- Explain ambiguous terms or alternate names (e.g., Abu Turab for Imam Ali) so newcomers can follow.

Output the enriched page content as clean markdown (no JSON wrapper, no code fences)."""

MCQ_GENERATION_SYSTEM = """You are creating multiple-choice quiz questions for a Twelver Shia Islamic education platform.

Given the full content of a lesson (all pages combined), generate 3-4 MCQs that test comprehension of the key concepts taught in the lesson.

Rules:
- Mix difficulties: include at least 1 easy, 1 medium, and ideally 1 hard question.
- Each question MUST have exactly 4 options labeled A, B, C, D.
- Correct answers should test understanding and application, not rote memorization.
- Wrong options should be plausible but clearly incorrect to someone who studied the lesson.
- Questions should cover different parts/topics of the lesson, not all the same concept.
- Do not create trick questions or questions about trivial details.
- If the lesson content does not lend itself well to quiz questions, generate only 3 questions.

You MUST output ONLY valid JSON with no additional text:
{{
  "mcqs": [
    {{
      "question": "The question text here?",
      "options": ["A) Option one", "B) Option two", "C) Option three", "D) Option four"],
      "correct_answer": "B",
      "difficulty": "easy"
    }}
  ]
}}"""

SUMMARY_GENERATION_SYSTEM = """You are summarizing a lesson for a Twelver Shia Islamic education platform.

Given the full content of a lesson (all enriched pages), generate:
1. A concise 2-4 sentence summary capturing the key themes and takeaways of the lesson.
2. An estimated reading time in minutes (assume ~200 words per minute for educational content with Arabic text; round up).
3. 2-3 baseline primer bullets -- prerequisite concepts a reader should know before starting this lesson. Each bullet should be 1-2 sentences.
4. An optional glossary of 2-5 key Islamic terms used in the lesson with brief definitions.

You MUST output ONLY valid JSON with no additional text:
{{
  "summary": "2-4 sentence summary here...",
  "estimated_minutes": 15,
  "baseline_primer_bullets": ["Bullet 1 here.", "Bullet 2 here."],
  "baseline_primer_glossary": {{"term": "definition", "another_term": "definition"}}
}}"""

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def parse_json_from_llm(text: str) -> Optional[dict]:
    """Extract and parse JSON from an LLM response, handling markdown code fences."""
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code fences
    for pattern in [r'```json\s*\n(.*?)\n\s*```', r'```\s*\n(.*?)\n\s*```']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    # Last resort: find outermost {...}
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def format_shia_doc(doc: dict) -> str:
    """Format a Shia hadith document for the enrichment prompt."""
    meta = doc.get("metadata", {})
    parts = []
    for field in ("source", "book", "chapter", "hadith_number", "author", "volume"):
        val = meta.get(field)
        if val:
            parts.append(f"{field.replace('_', ' ').title()}: {val}")
    if doc.get("page_content_en"):
        parts.append(f"English Text: {doc['page_content_en']}")
    if doc.get("page_content_ar"):
        parts.append(f"Arabic Text: {doc['page_content_ar']}")
    return "\n".join(parts)


def format_quran_doc(doc: dict) -> str:
    """Format a Quran tafsir document for the enrichment prompt."""
    meta = doc.get("metadata", {})
    parts = []
    for field in ("surah_name", "surah", "chapter_number", "verses", "author", "collection", "volume"):
        val = meta.get(field)
        if val:
            parts.append(f"{field.replace('_', ' ').title()}: {val}")
    if doc.get("page_content_en"):
        parts.append(f"Tafsir: {doc['page_content_en']}")
    if doc.get("quran_translation"):
        parts.append(f"Quran Translation: {doc['quran_translation']}")
    return "\n".join(parts)


def estimate_minutes(text: str) -> int:
    """Estimate reading time in minutes (~200 words/min, minimum 1)."""
    return max(1, math.ceil(len(text.split()) / 200))


def timestamp() -> str:
    """Return current time as HH:MM:SS string."""
    return datetime.now().strftime("%H:%M:%S")


def page_key(lesson_number: int, page_number: int) -> str:
    """Canonical key for enriched_pages and page_references dicts."""
    return f"L{lesson_number}_P{page_number}"


# ---------------------------------------------------------------------------
# LLM initialization
# ---------------------------------------------------------------------------

_llm = None


def _get_llm():
    if _llm is None:
        raise RuntimeError("LLM not initialized. Call init_llm() first.")
    return _llm


def init_llm(model_choice: str):
    """Initialize the global LLM based on user selection.

    Args:
        model_choice: 'default' (LARGE_LLM from .env), 'sonnet', or 'opus'.
    """
    global _llm
    import os

    if model_choice == "default":
        from core.config import LARGE_LLM, ANTHROPIC_API_KEY
        from langchain_anthropic import ChatAnthropic
        if not LARGE_LLM:
            raise ValueError("LARGE_LLM is not set in .env")
        print(f"[{timestamp()}] Using model: {LARGE_LLM} (Anthropic)")
        _llm = ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY, max_tokens=4096)
    else:
        from core.config import ANTHROPIC_API_KEY
        from langchain_anthropic import ChatAnthropic
        if not ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set in .env\n"
                "Add it: ANTHROPIC_API_KEY=sk-ant-..."
            )
        model_id = "claude-sonnet-4-6" if model_choice == "sonnet" else "claude-opus-4-6"
        print(f"[{timestamp()}] Using model: {model_id} (Anthropic)")
        _llm = ChatAnthropic(model=model_id, api_key=ANTHROPIC_API_KEY, max_tokens=4096)


# ---------------------------------------------------------------------------
# LLM call helpers (used directly by pipeline nodes -- not bound to an agent)
# ---------------------------------------------------------------------------

def llm_split_content(source_content: str, target_lessons: int) -> dict:
    """Call the LLM to split source content into a lesson/page structure."""
    print(f"[{timestamp()}] Calling LLM to split content into {target_lessons} lessons...")
    llm = _get_llm()
    prompt = CONTENT_SPLIT_SYSTEM.format(target_lessons=target_lessons)

    for attempt in range(2):
        extra = "\n\nIMPORTANT: Output ONLY valid JSON. No other text." if attempt else ""
        response = llm.invoke([
            SystemMessage(content=prompt + extra),
            HumanMessage(content=f"Source content to split into lessons:\n\n{source_content}")
        ])
        result = parse_json_from_llm(response.content)
        if result and "lessons" in result:
            num_lessons = len(result["lessons"])
            total_pages = sum(len(l.get("pages", [])) for l in result["lessons"])
            print(f"[{timestamp()}]   Created {num_lessons} lessons, {total_pages} total pages")
            return result
        print(f"[{timestamp()}]   JSON parse failed (attempt {attempt + 1}/2)...")

    raise RuntimeError("Failed to parse lesson structure from LLM after 2 attempts.")


def llm_enrich_page(draft_content: str, page_title: str,
                     shia_refs: str, quran_refs: str) -> str:
    """Call the LLM to enrich a single page with retrieved references."""
    print(f"[{timestamp()}]   Enriching: {page_title}")
    llm = _get_llm()

    user_msg = (
        f"## Draft Content:\n{draft_content}\n\n"
        f"## Retrieved Shia Hadith References:\n{shia_refs}\n\n"
        f"## Retrieved Quran Tafsir References:\n{quran_refs}"
    )
    response = llm.invoke([
        SystemMessage(content=PAGE_ENRICHMENT_SYSTEM),
        HumanMessage(content=user_msg)
    ])
    print(f"[{timestamp()}]     Done ({len(response.content.split())} words)")
    return response.content


def llm_generate_quiz(lesson_title: str, combined_content: str) -> list:
    """Call the LLM to generate MCQs for a lesson. Returns list of MCQ dicts."""
    print(f"[{timestamp()}]   Quiz for: {lesson_title}")
    llm = _get_llm()

    for attempt in range(2):
        extra = "\n\nIMPORTANT: Output ONLY valid JSON." if attempt else ""
        response = llm.invoke([
            SystemMessage(content=MCQ_GENERATION_SYSTEM + extra),
            HumanMessage(content=f"Lesson: {lesson_title}\n\nContent:\n\n{combined_content}")
        ])
        result = parse_json_from_llm(response.content)
        if result and "mcqs" in result:
            print(f"[{timestamp()}]     {len(result['mcqs'])} questions")
            return result["mcqs"]
        print(f"[{timestamp()}]     JSON parse failed (attempt {attempt + 1}/2)...")

    print(f"[{timestamp()}]     Warning: could not generate quiz for '{lesson_title}'")
    return []


def llm_generate_summary(lesson_title: str, combined_content: str) -> dict:
    """Call the LLM to generate a lesson summary, primers, and glossary."""
    print(f"[{timestamp()}]   Summary for: {lesson_title}")
    llm = _get_llm()

    for attempt in range(2):
        extra = "\n\nIMPORTANT: Output ONLY valid JSON." if attempt else ""
        response = llm.invoke([
            SystemMessage(content=SUMMARY_GENERATION_SYSTEM + extra),
            HumanMessage(content=f"Lesson: {lesson_title}\n\nContent:\n\n{combined_content}")
        ])
        result = parse_json_from_llm(response.content)
        if result and "summary" in result:
            print(f"[{timestamp()}]     {result.get('estimated_minutes', '?')} min")
            return result
        print(f"[{timestamp()}]     JSON parse failed (attempt {attempt + 1}/2)...")

    return {
        "summary": f"Lesson covering {lesson_title}.",
        "estimated_minutes": estimate_minutes(combined_content),
        "baseline_primer_bullets": [],
        "baseline_primer_glossary": {}
    }


def fetch_page_references(query: str) -> dict:
    """Fetch Shia hadith and Quran tafsir references for a single page query.

    Returns a dict with both raw docs (for deduplication) and formatted strings.
    """
    shia_docs, quran_docs = [], []

    try:
        shia_docs = retrieve_shia_documents(query, 5)
    except Exception as e:
        print(f"[{timestamp()}]     Warning: Shia retrieval error: {e}")

    try:
        quran_docs = retrieve_quran_documents(query, 3)
    except Exception as e:
        print(f"[{timestamp()}]     Warning: Quran retrieval error: {e}")

    return {
        "shia_docs": shia_docs,
        "quran_docs": quran_docs,
        "shia_count": len(shia_docs),
        "quran_count": len(quran_docs),
    }


def _build_formatted_refs(refs: dict) -> dict:
    """Build shia_references / quran_references formatted strings from raw docs."""
    shia_docs = refs.get("shia_docs", [])
    quran_docs = refs.get("quran_docs", [])
    return {
        **refs,
        "shia_references": ("\n\n---\n\n".join(format_shia_doc(d) for d in shia_docs)
                            if shia_docs else "No Shia hadith references found."),
        "quran_references": ("\n\n---\n\n".join(format_quran_doc(d) for d in quran_docs)
                             if quran_docs else "No Quran tafsir references found."),
    }


def _dedup_refs(lessons: list, all_refs: dict, max_reuse: int = 2) -> dict:
    """Deduplicate references across the entire Hikmah Tree.

    Two rules applied together:
    1. Within a lesson: each reference appears in only ONE page (first page wins).
    2. Globally across lessons: each reference can appear at most `max_reuse` times
       total. Once a reference hits the cap it is dropped from all subsequent pages.

    Pages are processed in lesson order, then page order within each lesson.
    """
    deduped = dict(all_refs)

    # Global usage counters: id -> number of pages it has been assigned to
    global_shia_usage: Dict[str, int] = {}
    global_quran_usage: Dict[str, int] = {}

    for lesson in lessons:
        ln = lesson["lesson_number"]
        # Track per-lesson seen sets so a ref only appears once per lesson
        lesson_seen_shia: set = set()
        lesson_seen_quran: set = set()

        for page in lesson.get("pages", []):
            key = page_key(ln, page["page_number"])
            refs = deduped.get(key, {})

            filtered_shia = []
            for d in refs.get("shia_docs", []):
                hid = d.get("hadith_id")
                if not hid:
                    continue
                # Must not have appeared earlier in this lesson AND be under global cap
                if hid not in lesson_seen_shia and global_shia_usage.get(hid, 0) < max_reuse:
                    filtered_shia.append(d)
                    lesson_seen_shia.add(hid)
                    global_shia_usage[hid] = global_shia_usage.get(hid, 0) + 1

            filtered_quran = []
            for d in refs.get("quran_docs", []):
                cid = d.get("chunk_id")
                if not cid:
                    continue
                if cid not in lesson_seen_quran and global_quran_usage.get(cid, 0) < max_reuse:
                    filtered_quran.append(d)
                    lesson_seen_quran.add(cid)
                    global_quran_usage[cid] = global_quran_usage.get(cid, 0) + 1

            deduped[key] = _build_formatted_refs({
                **refs,
                "shia_docs": filtered_shia,
                "quran_docs": filtered_quran,
                "shia_count": len(filtered_shia),
                "quran_count": len(filtered_quran),
            })

    return deduped


# ---------------------------------------------------------------------------
# LangGraph state definition
# ---------------------------------------------------------------------------

class HikmahGenState(TypedDict):
    # Input config
    source_content: str
    tree_title: str
    tree_summary: str
    tags: list
    skill_level: int
    target_lessons: int
    # Populated by pipeline nodes
    lessons_structure: Optional[dict]      # from split_node
    page_references: dict                  # page_key -> {shia_refs, quran_refs, counts}
    enriched_pages: dict                   # page_key -> enriched markdown string
    mcqs: dict                             # lesson_number -> list of MCQ dicts
    lesson_summaries: dict                 # lesson_number -> {summary, estimated_minutes, ...}
    generation_complete: bool


# ---------------------------------------------------------------------------
# Sequential pipeline nodes
# ---------------------------------------------------------------------------

def split_node(state: HikmahGenState) -> dict:
    """Phase 1: Split source content into a lesson/page structure."""
    print(f"\n[{timestamp()}] ── Phase 1/5: Content split ──────────────────────────")
    structure = llm_split_content(state["source_content"], state["target_lessons"])
    return {"lessons_structure": structure}


def retrieve_node(state: HikmahGenState) -> dict:
    """Phase 2: Fetch references for every page in parallel."""
    print(f"\n[{timestamp()}] ── Phase 2/5: Reference retrieval ──────────────────────")
    lessons = state["lessons_structure"]["lessons"]

    # Build a flat list of (key, query) for all pages
    page_queries: List[tuple] = []
    for lesson in lessons:
        ln = lesson["lesson_number"]
        for page in lesson.get("pages", []):
            pn = page["page_number"]
            topics = " ".join(page.get("key_topics", []))
            query = f"{page['title']} {topics}".strip()
            page_queries.append((page_key(ln, pn), query))

    total = len(page_queries)
    print(f"[{timestamp()}]   Fetching references for {total} pages (parallel)...")

    all_refs: dict = {}

    def fetch_one(kq: tuple) -> tuple:
        key, query = kq
        print(f"[{timestamp()}]   [{key}] {query[:70]}...")
        refs = fetch_page_references(query)
        return key, refs

    # Use ThreadPoolExecutor for parallel retrieval (max 4 concurrent)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_one, kq): kq for kq in page_queries}
        for future in concurrent.futures.as_completed(futures):
            try:
                key, refs = future.result()
                all_refs[key] = refs
            except Exception as e:
                kq = futures[future]
                print(f"[{timestamp()}]   Error fetching [{kq[0]}]: {e}")
                all_refs[kq[0]] = {"shia_docs": [], "quran_docs": [],
                                    "shia_references": "Error retrieving.",
                                    "quran_references": "Error retrieving."}

    total_shia = sum(r.get("shia_count", 0) for r in all_refs.values())
    total_quran = sum(r.get("quran_count", 0) for r in all_refs.values())
    print(f"[{timestamp()}]   Fetched: {total_shia} hadith + {total_quran} tafsir docs across {total} pages")

    # Deduplicate: unique per lesson-page, max 2 uses globally across all lessons
    print(f"[{timestamp()}]   Deduplicating references (max 2 uses per reference globally)...")
    all_refs = _dedup_refs(lessons, all_refs, max_reuse=2)

    dedup_shia = sum(r.get("shia_count", 0) for r in all_refs.values())
    dedup_quran = sum(r.get("quran_count", 0) for r in all_refs.values())
    print(f"[{timestamp()}]   After dedup: {dedup_shia} hadith + {dedup_quran} tafsir docs")
    return {"page_references": all_refs}


def enrich_node(state: HikmahGenState) -> dict:
    """Phase 3: Enrich each page with its fetched references."""
    print(f"\n[{timestamp()}] ── Phase 3/5: Page enrichment ───────────────────────────")
    lessons = state["lessons_structure"]["lessons"]
    refs = state["page_references"]
    enriched: dict = {}

    for lesson in lessons:
        ln = lesson["lesson_number"]
        lesson_title = lesson.get("title", f"Lesson {ln}")
        pages = lesson.get("pages", [])
        print(f"[{timestamp()}]   Lesson {ln}: {lesson_title} ({len(pages)} pages)")

        for page in pages:
            pn = page["page_number"]
            key = page_key(ln, pn)
            page_refs = refs.get(key, {})

            enriched_md = llm_enrich_page(
                draft_content=page.get("content", ""),
                page_title=page.get("title", ""),
                shia_refs=page_refs.get("shia_references", "No references found."),
                quran_refs=page_refs.get("quran_references", "No references found."),
            )
            enriched[key] = enriched_md

    print(f"[{timestamp()}]   Enriched {len(enriched)} pages total")
    return {"enriched_pages": enriched}


def quiz_node(state: HikmahGenState) -> dict:
    """Phase 4: Generate MCQ quizzes for each lesson."""
    print(f"\n[{timestamp()}] ── Phase 4/5: Quiz generation ───────────────────────────")
    lessons = state["lessons_structure"]["lessons"]
    enriched = state["enriched_pages"]
    all_mcqs: dict = {}

    for lesson in lessons:
        ln = lesson["lesson_number"]
        lesson_title = lesson.get("title", f"Lesson {ln}")
        combined = "\n\n---\n\n".join(
            enriched.get(page_key(ln, page["page_number"]), page.get("content", ""))
            for page in lesson.get("pages", [])
        )
        all_mcqs[ln] = llm_generate_quiz(lesson_title, combined)

    total_q = sum(len(q) for q in all_mcqs.values())
    print(f"[{timestamp()}]   {total_q} questions across {len(all_mcqs)} lessons")
    return {"mcqs": all_mcqs}


def summary_node(state: HikmahGenState) -> dict:
    """Phase 5: Generate summary, primers, and glossary for each lesson."""
    print(f"\n[{timestamp()}] ── Phase 5/5: Summary generation ──────────────────────")
    lessons = state["lessons_structure"]["lessons"]
    enriched = state["enriched_pages"]
    all_summaries: dict = {}

    for lesson in lessons:
        ln = lesson["lesson_number"]
        lesson_title = lesson.get("title", f"Lesson {ln}")
        combined = "\n\n---\n\n".join(
            enriched.get(page_key(ln, page["page_number"]), page.get("content", ""))
            for page in lesson.get("pages", [])
        )
        all_summaries[ln] = llm_generate_summary(lesson_title, combined)

    print(f"[{timestamp()}]   Summaries complete for {len(all_summaries)} lessons")
    return {"lesson_summaries": all_summaries, "generation_complete": True}


def create_pipeline():
    """Build the sequential LangGraph pipeline."""
    workflow = StateGraph(HikmahGenState)
    workflow.add_node("split", split_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("enrich", enrich_node)
    workflow.add_node("quiz", quiz_node)
    workflow.add_node("summary", summary_node)

    workflow.set_entry_point("split")
    workflow.add_edge("split", "retrieve")
    workflow.add_edge("retrieve", "enrich")
    workflow.add_edge("enrich", "quiz")
    workflow.add_edge("quiz", "summary")
    workflow.add_edge("summary", END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------

def assemble_review_markdown(tree_title: str, tree_summary: str, tags: list,
                              skill_level: int, final_state: dict) -> str:
    """Assemble the single review markdown file from pipeline state."""
    lines = []
    structure = final_state.get("lessons_structure", {})
    lessons = structure.get("lessons", [])
    enriched = final_state.get("enriched_pages", {})
    summaries = final_state.get("lesson_summaries", {})
    all_mcqs = final_state.get("mcqs", {})

    total_pages = sum(len(l.get("pages", [])) for l in lessons)
    total_minutes = sum(s.get("estimated_minutes", 10) for s in summaries.values())

    lines += [
        f"# {tree_title}", "",
        f"**Summary:** {tree_summary}",
        f"**Estimated Time:** {total_minutes} minutes | **Lessons:** {len(lessons)} | "
        f"**Pages:** {total_pages} | **Skill Level:** {skill_level}/10",
        f"**Tags:** {', '.join(tags)}" if tags else "",
        "",
    ]

    for lesson in lessons:
        ln = lesson["lesson_number"]
        lesson_title = lesson.get("title", f"Lesson {ln}")
        s = summaries.get(ln, {})
        primers = s.get("baseline_primer_bullets", [])
        glossary = s.get("baseline_primer_glossary", {})

        lines += ["---", "", f"## Lesson {ln}: {lesson_title}", ""]
        if s.get("summary"):
            lines += [f"**Summary:** {s['summary']}", ""]
        if s.get("estimated_minutes"):
            lines += [f"**Estimated Time:** {s['estimated_minutes']} minutes", ""]
        if primers:
            lines.append("**Prerequisites:**")
            lines += [f"- {b}" for b in primers]
            lines.append("")
        if glossary:
            lines.append("**Key Terms:**")
            lines += [f"- **{k}**: {v}" for k, v in glossary.items()]
            lines.append("")

        for page in lesson.get("pages", []):
            pn = page["page_number"]
            key = page_key(ln, pn)
            page_title = page.get("title", f"Page {pn}")
            content = enriched.get(key, page.get("content", ""))
            lines += [f"### Page {pn}: {page_title}", "", content, ""]

        mcqs = all_mcqs.get(ln, [])
        if mcqs:
            lines += ["### Quiz", ""]
            for qi, mcq in enumerate(mcqs, 1):
                diff = mcq.get("difficulty", "medium").capitalize()
                lines.append(f"{qi}. [{diff}] {mcq.get('question', '')}")
                for opt in mcq.get("options", []):
                    lines.append(f"   - {opt}")
                lines.append(f"   - **Answer: {mcq.get('correct_answer', '?')}**")
                lines.append("")

    return "\n".join(lines)


def assemble_db_json(tree_title: str, tree_summary: str, tags: list,
                      skill_level: int, final_state: dict) -> dict:
    """Assemble the database-ready JSON from pipeline state."""
    structure = final_state.get("lessons_structure", {})
    lessons = structure.get("lessons", [])
    enriched = final_state.get("enriched_pages", {})
    summaries = final_state.get("lesson_summaries", {})
    all_mcqs = final_state.get("mcqs", {})

    total_pages = sum(len(l.get("pages", [])) for l in lessons)
    total_minutes = sum(s.get("estimated_minutes", 10) for s in summaries.values())

    db_data = {
        "hikmah_tree": {
            "title": tree_title,
            "summary": tree_summary,
            "tags": tags,
            "skill_level": skill_level,
            "meta": {
                "total_lessons": len(lessons),
                "total_pages": total_pages,
                "estimated_minutes": total_minutes,
                "perspective": "Twelver Shia Islam",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        "lessons": []
    }

    for lesson in lessons:
        ln = lesson["lesson_number"]
        lesson_title = lesson.get("title", f"Lesson {ln}")
        s = summaries.get(ln, {})

        lesson_obj = {
            "slug": slugify(lesson_title),
            "title": lesson_title,
            "summary": s.get("summary", ""),
            "tags": tags,
            "status": "draft",
            "language_code": "en",
            "estimated_minutes": s.get("estimated_minutes", 10),
            "order_position": ln,
            "baseline_primer_bullets": s.get("baseline_primer_bullets", []),
            "baseline_primer_glossary": s.get("baseline_primer_glossary", {}),
            "content": [],
        }

        for page in lesson.get("pages", []):
            pn = page["page_number"]
            key = page_key(ln, pn)
            content_md = enriched.get(key, page.get("content", ""))
            lesson_obj["content"].append({
                "order_position": pn,
                "title": page.get("title", f"Page {pn}"),
                "content_type": "text",
                "content_body": content_md,
                "content_json": None,
                "media_urls": None,
                "est_minutes": estimate_minutes(content_md),
            })

        mcqs = all_mcqs.get(ln, [])
        if mcqs:
            lesson_obj["content"].append({
                "order_position": 99,
                "title": "Quiz",
                "content_type": "quiz",
                "content_body": None,
                "content_json": {"mcqs": mcqs},
                "media_urls": None,
                "est_minutes": max(1, len(mcqs) * 2),
            })

        db_data["lessons"].append(lesson_obj)

    return db_data


# ---------------------------------------------------------------------------
# Interactive config
# ---------------------------------------------------------------------------

def get_interactive_config() -> dict:
    """Collect run configuration interactively from the user."""
    print("\n" + "=" * 60)
    print("  Hikmah Tree Lesson Generator")
    print("=" * 60 + "\n")

    input_files = sorted(INPUT_DIR.glob("*.md"))
    if not input_files:
        print(f"ERROR: No markdown files found in {INPUT_DIR}")
        print("Place your .md source files there and run again.")
        sys.exit(1)

    print(f"Found {len(input_files)} input file(s):")
    for f in input_files:
        print(f"  - {f.name} ({f.stat().st_size / 1024:.1f} KB)")
    print()

    if input("Use these files? (Y/n): ").strip().lower() == 'n':
        print("Exiting. Adjust input files and try again.")
        sys.exit(0)

    print()
    tree_title = input("Enter the Hikmah Tree title: ").strip()
    if not tree_title:
        print("ERROR: Title is required.")
        sys.exit(1)

    tree_summary = input("Enter a brief summary of the source content: ").strip()
    if not tree_summary:
        tree_summary = f"A course on {tree_title} from the Twelver Shia perspective."

    tags_raw = input("Enter tags (comma-separated, e.g. divine-justice,theology): ").strip()
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    skill_raw = input("Skill level (1-10, default 5): ").strip()
    skill_level = max(1, min(10, int(skill_raw))) if skill_raw.isdigit() else 5

    lessons_raw = input("Target number of lessons (default 5, minimum 4): ").strip()
    target_lessons = max(4, int(lessons_raw)) if lessons_raw.isdigit() else 5

    # Model selection
    print("\nModel selection:")
    print("  1) Default  -- LARGE_LLM from .env (Anthropic)")
    print("  2) Sonnet   -- claude-sonnet-4-6 (requires ANTHROPIC_API_KEY)")
    print("  3) Opus     -- claude-opus-4-6   (requires ANTHROPIC_API_KEY)")
    model_input = input("Choose model (1/2/3, default 1): ").strip()
    model_choice = {"1": "default", "2": "sonnet", "3": "opus"}.get(model_input, "default")

    # Read and concatenate input files
    source_content = ""
    for f in input_files:
        source_content += f"\n\n--- Source: {f.name} ---\n\n{f.read_text(encoding='utf-8')}"

    print(f"\nLoaded {len(input_files)} file(s), {len(source_content):,} characters")
    print(f"Config: {tree_title} | skill {skill_level} | {target_lessons} lessons | model: {model_choice}")
    print()

    return {
        "tree_title": tree_title,
        "tree_summary": tree_summary,
        "tags": tags,
        "skill_level": skill_level,
        "target_lessons": target_lessons,
        "source_content": source_content,
        "model_choice": model_choice,
    }


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

def run_generation(config: dict):
    """Run the sequential LangGraph pipeline and write output files."""
    print(f"\n[{timestamp()}] Building pipeline...")
    graph = create_pipeline()

    initial_state: HikmahGenState = {
        "source_content": config["source_content"],
        "tree_title": config["tree_title"],
        "tree_summary": config["tree_summary"],
        "tags": config["tags"],
        "skill_level": config["skill_level"],
        "target_lessons": config["target_lessons"],
        "lessons_structure": None,
        "page_references": {},
        "enriched_pages": {},
        "mcqs": {},
        "lesson_summaries": {},
        "generation_complete": False,
    }

    print(f"[{timestamp()}] Running pipeline (this will take several minutes)...\n")
    final_state = graph.invoke(initial_state)

    if not final_state.get("generation_complete"):
        print("WARNING: Pipeline may not have completed all phases.")

    # Save intermediate state for debugging / resumption
    intermediate_path = OUTPUT_DIR / "_intermediate.json"
    intermediate_path.write_text(
        json.dumps({
            "lessons_structure": final_state.get("lessons_structure"),
            "mcqs": final_state.get("mcqs"),
            "lesson_summaries": final_state.get("lesson_summaries"),
            "enriched_pages_preview": {
                k: v[:200] + "..." for k, v in final_state.get("enriched_pages", {}).items()
            },
        }, indent=2, default=str),
        encoding="utf-8"
    )
    print(f"\n[{timestamp()}] Intermediate state saved: {intermediate_path}")

    slug = slugify(config["tree_title"])

    # Review markdown
    print(f"[{timestamp()}] Assembling review markdown...")
    review_md = assemble_review_markdown(
        config["tree_title"], config["tree_summary"],
        config["tags"], config["skill_level"], final_state
    )
    review_path = OUTPUT_DIR / f"{slug}_review.md"
    review_path.write_text(review_md, encoding="utf-8")
    print(f"[{timestamp()}] Saved: {review_path}")

    # DB JSON
    print(f"[{timestamp()}] Assembling DB JSON...")
    db_json = assemble_db_json(
        config["tree_title"], config["tree_summary"],
        config["tags"], config["skill_level"], final_state
    )
    json_path = OUTPUT_DIR / f"{slug}_db.json"
    json_path.write_text(json.dumps(db_json, indent=2, default=str), encoding="utf-8")
    print(f"[{timestamp()}] Saved: {json_path}")

    lessons = final_state.get("lessons_structure", {}).get("lessons", [])
    total_q = sum(len(q) for q in final_state.get("mcqs", {}).values())
    print(f"\n{'=' * 60}")
    print(f"  Generation complete!")
    print(f"  Lessons: {len(lessons)} | Quiz questions: {total_q}")
    print(f"  Review:  {review_path}")
    print(f"  DB JSON: {json_path}")
    print(f"{'=' * 60}\n")


def main():
    config = get_interactive_config()

    if input("Ready to generate? (Y/n): ").strip().lower() == 'n':
        print("Cancelled.")
        sys.exit(0)

    try:
        init_llm(config["model_choice"])
        run_generation(config)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
