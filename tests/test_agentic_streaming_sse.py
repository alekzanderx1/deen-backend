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
