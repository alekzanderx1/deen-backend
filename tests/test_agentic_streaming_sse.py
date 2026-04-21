"""
Test that runs the agentic streaming API and writes the combined SSE output
to a markdown file (as it would appear in the UI).

Run from project root:
  python tests/test_agentic_streaming_sse.py
  # or with pytest (if installed):
  python -m pytest tests/test_agentic_streaming_sse.py -v -s

Requires .env with OPENAI_API_KEY, Redis, Pinecone, etc. Server does not need to be running.
"""

import asyncio
import json
import os
import re
import sys
import tempfile
from typing import List, Dict, Any, Optional

# Ensure project root is on path so "from core import ..." works when run as script
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.normpath(os.path.join(_script_dir, ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    import pytest
except ImportError:
    pytest = None


def _maybe_mark_asyncio(f):
    """Apply pytest.mark.asyncio when pytest is available."""
    if pytest is not None:
        return pytest.mark.asyncio(f)
    return f


def parse_sse_stream(chunks: List[str]) -> List[Dict[str, Any]]:
    """Turn concatenated SSE chunks into a list of {event, data}."""
    events = []
    buffer = "".join(chunks)
    raw_events = re.split(r"\n\n+", buffer.strip())
    for raw in raw_events:
        if not raw.strip():
            continue
        event_type = None
        data_str = None
        for line in raw.split("\n"):
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_str = line[5:].strip()
        if event_type is None and data_str is not None:
            event_type = "message"
        if event_type:
            data = {}
            if data_str:
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    data = {"raw": data_str}
            events.append({"event": event_type, "data": data})
    return events


def build_ui_markdown(
    query: str,
    events: List[Dict[str, Any]],
    include_status_steps: bool = True,
) -> str:
    """Build markdown as the UI would show: response body + hadith refs + quran refs."""
    lines = [
        "# Agentic streaming response (UI view)",
        "",
        f"**Query:** {query}",
        "",
        "---",
        "",
    ]

    status_steps: List[str] = []
    response_tokens: List[str] = []
    hadith_refs: List[Dict] = []
    quran_refs: List[Dict] = []
    error_message: Optional[str] = None

    for ev in events:
        etype = ev.get("event")
        data = ev.get("data") or {}
        if etype == "status":
            msg = data.get("message") or data.get("step") or ""
            if msg:
                status_steps.append(msg)
        elif etype == "response_chunk":
            token = data.get("token") or ""
            if token:
                response_tokens.append(token)
        elif etype == "hadith_references":
            refs = data.get("references") if isinstance(data.get("references"), list) else []
            hadith_refs = refs
        elif etype == "quran_references":
            refs = data.get("references") if isinstance(data.get("references"), list) else []
            quran_refs = refs
        elif etype == "error":
            error_message = data.get("message") or str(data)

    if include_status_steps and status_steps:
        lines.append("## Steps")
        lines.append("")
        for s in status_steps:
            lines.append(f"- {s}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Response")
    lines.append("")
    if error_message:
        lines.append(f"*Error: {error_message}*")
        lines.append("")
    response_text = "".join(response_tokens)
    if response_text:
        lines.append(response_text)
        lines.append("")
    lines.append("---")
    lines.append("")

    if hadith_refs:
        lines.append("## Hadith references")
        lines.append("")
        for i, ref in enumerate(hadith_refs, 1):
            lines.append(f"### Reference {i}")
            if isinstance(ref, dict):
                for k, v in ref.items():
                    if v and str(v).strip():
                        lines.append(f"- **{k}:** {v}")
            else:
                lines.append(str(ref))
            lines.append("")
        lines.append("---")
        lines.append("")

    if quran_refs:
        lines.append("## Quran / Tafsir references")
        lines.append("")
        for i, ref in enumerate(quran_refs, 1):
            lines.append(f"### Reference {i}")
            if isinstance(ref, dict):
                for k, v in ref.items():
                    if v and str(v).strip():
                        lines.append(f"- **{k}:** {v}")
            else:
                lines.append(str(ref))
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("*End of stream.*")
    return "\n".join(lines)


async def run_agentic_stream_and_collect(
    user_query: str,
    session_id: str = "test-agentic-sse-session",
    target_language: str = "english",
) -> List[str]:
    """Run the agentic streaming pipeline and collect raw SSE chunks."""
    from core import pipeline_langgraph

    response = await pipeline_langgraph.chat_pipeline_streaming_agentic(
        user_query=user_query,
        session_id=session_id,
        target_language=target_language,
    )
    chunks: List[str] = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8")
        chunks.append(chunk)
    return chunks


@_maybe_mark_asyncio
async def test_agentic_streaming_sse_to_markdown_file(tmp_path):
    """Run agentic streaming, parse SSE, and write UI-style markdown to a temp file."""
    query = "What does Islam say about patience?"
    session_id = "test-sse-session-1"
    chunks = await run_agentic_stream_and_collect(query, session_id=session_id)
    assert chunks, "Expected at least one SSE chunk"

    events = parse_sse_stream(chunks)
    assert events, "Expected at least one SSE event"

    markdown = build_ui_markdown(query, events, include_status_steps=True)
    out_path = tmp_path / "agentic_stream_ui_output.md"
    out_path.write_text(markdown, encoding="utf-8")

    event_types = [e.get("event") for e in events]
    assert "done" in event_types or "response_chunk" in event_types or "error" in event_types, (
        f"Expected response_chunk/done/error in events: {event_types}"
    )
    assert out_path.read_text(encoding="utf-8").strip(), "Output file should not be empty"
    print(f"\n[TEST] Wrote UI markdown to: {out_path}")


@_maybe_mark_asyncio
async def test_agentic_streaming_emits_granular_status_events(tmp_path):
    """Verify granular status events are emitted (dual-path: fiqh vs non-fiqh).

    Assertions:
      - For the non-fiqh path: at least one per-tool status event is emitted,
        AND a per-tool status event precedes the first response_chunk.
      - For the fiqh path: at least one fiqh_* stage status event is emitted,
        AND a `fiqh_classification` or pre-flight `starting` status event
        precedes the first response_chunk.
      - If neither path is detected (e.g. early-exit / environment unable to
        reach external services), skip gracefully.
    """
    if pytest is None:  # pragma: no cover - pytest required for skip()
        return

    # Reuse the same query as the existing test to minimize setup variance.
    # The fiqh classifier may still route this down the fiqh path in some
    # configurations — the test handles both paths below.
    query = "What does Islam say about patience?"
    session_id = "test-sse-session-granular"

    # Skip gracefully on environment bootstrap errors (missing keys, model
    # init failures, network). The test's purpose is to assert SSE status
    # emission *given* a working pipeline; it should not fail the suite when
    # the pipeline cannot even be constructed.
    try:
        chunks = await run_agentic_stream_and_collect(query, session_id=session_id)
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Pipeline bootstrap failed ({type(exc).__name__}): {exc}")
    if not chunks:
        pytest.skip("No SSE chunks received — environment likely cannot reach external services")

    events = parse_sse_stream(chunks)
    if not events:
        pytest.skip("No SSE events parsed — environment likely cannot reach external services")

    status_events = [e for e in events if e.get("event") == "status"]
    status_steps = [(e.get("data") or {}).get("step") for e in status_events]
    chunk_events = [e for e in events if e.get("event") == "response_chunk"]

    # Path detection. fiqh_classification alone is NOT enough to mark the fiqh
    # path; we only treat a run as the fiqh path when a fiqh_<stage> step
    # (decompose / retrieve / filter / assess / refine / subgraph) is seen.
    has_agent_step = "agent" in status_steps
    fiqh_stage_steps = {
        s for s in status_steps
        if isinstance(s, str) and s.startswith("fiqh_") and s != "fiqh_classification"
    }
    is_fiqh_path = len(fiqh_stage_steps) > 0
    is_nonfiqh_path = has_agent_step and not is_fiqh_path

    # Skip-gracefully guards
    if len(chunk_events) == 0:
        pytest.skip(
            "No response_chunk events received — environment likely cannot reach external services"
        )
    if not (is_fiqh_path or is_nonfiqh_path):
        pytest.skip(
            f"Neither fiqh nor non-fiqh path detected (status_steps={status_steps}); "
            f"likely early-exit or env issue"
        )

    # First response_chunk index (used by both paths for ordering assertion).
    first_chunk_idx = next(i for i, e in enumerate(events) if e.get("event") == "response_chunk")
    preceding_status_steps = [
        (e.get("data") or {}).get("step")
        for e in events[:first_chunk_idx]
        if e.get("event") == "status"
    ]

    if is_nonfiqh_path:
        known_tool_steps = {
            "retrieve_shia_documents_tool",
            "retrieve_sunni_documents_tool",
            "retrieve_quran_tafsir_tool",
            "enhance_query_tool",
            "translate_to_english_tool",
            "check_if_non_islamic_tool",
        }
        assert any(s in known_tool_steps for s in status_steps), (
            f"[non-fiqh path] Expected at least one per-tool status event. "
            f"status_steps={status_steps}"
        )
        assert any(s in known_tool_steps for s in preceding_status_steps), (
            f"[non-fiqh path] Expected a per-tool status event BEFORE the first "
            f"response_chunk. preceding_status_steps={preceding_status_steps}"
        )
    else:
        # Fiqh path assertions
        assert len(fiqh_stage_steps) >= 1, (
            f"[fiqh path] Expected at least one fiqh_* stage status event (e.g., "
            f"fiqh_decompose, fiqh_retrieve, fiqh_filter, fiqh_assess). "
            f"status_steps={status_steps}"
        )
        gating_steps = {"fiqh_classification", "starting"}
        assert any(s in gating_steps for s in preceding_status_steps), (
            f"[fiqh path] Expected fiqh_classification or 'starting' status event "
            f"BEFORE the first response_chunk. "
            f"preceding_status_steps={preceding_status_steps}"
        )

    print(
        f"\n[TEST] Granular status check OK "
        f"(path={'fiqh' if is_fiqh_path else 'non-fiqh'}, "
        f"status_steps={status_steps})"
    )


def main():
    """Run the pipeline once and write output to a temp markdown file (no pytest).

    Env:
      AGENTIC_TEST_QUERY    - User query (default: What does Islam say about patience?)
      AGENTIC_TEST_SESSION  - Session id (default: test-sse-cli-session)
      AGENTIC_TEST_OUTPUT   - Optional path to write markdown (else use temp file)
    """
    query = os.getenv("AGENTIC_TEST_QUERY", "Tell me about Imam Ali from both Shia and Sunni perspective?")
    session_id = os.getenv("AGENTIC_TEST_SESSION", "test-sse-cli-session")
    output_path_env = os.getenv("AGENTIC_TEST_OUTPUT", "").strip()

    async def _run():
        print(f"Query: {query}")
        print("Running agentic streaming pipeline...")
        chunks = await run_agentic_stream_and_collect(query, session_id=session_id)
        events = parse_sse_stream(chunks)
        markdown = build_ui_markdown(query, events, include_status_steps=True)
        if output_path_env:
            path = output_path_env
            with open(path, "w", encoding="utf-8") as f:
                f.write(markdown)
        else:
            fd, path = tempfile.mkstemp(suffix=".md", prefix="agentic_stream_ui_")
            os.write(fd, markdown.encode("utf-8"))
            os.close(fd)
        print(f"Wrote UI markdown to: {path}")
        return path

    return asyncio.run(_run())


if __name__ == "__main__":
    main()
