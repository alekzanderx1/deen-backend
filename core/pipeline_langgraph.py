"""
LangGraph-based agentic pipeline for chat.

This replaces the hardcoded pipeline with an intelligent agent
that decides which tools to use and when.
"""

import json
from typing import AsyncGenerator, Optional

from fastapi.responses import StreamingResponse

from agents.config.agent_config import AgentConfig, DEFAULT_AGENT_CONFIG
from agents.core.chat_agent import ChatAgent
from core import utils


# Human-readable status messages for each agent node
NODE_STATUS_MESSAGES = {
    "fiqh_classification": "Checking query classification...",
    "agent": "Agent thinking...",
    "tools": "Looking for information...",
    "generate_response": "Generating response...",
    "check_early_exit": "Processing...",
    # Fiqh FAIR-RAG pipeline nodes
    "fiqh_subgraph": "Processing fiqh query...",
    "generate_fiqh_response": "Generating fiqh answer...",
    # Fiqh sub-graph stage status (emitted explicitly after fiqh_subgraph event)
    "fiqh_decompose": "Decomposing fiqh query...",
    "fiqh_retrieve": "Retrieving fiqh documents...",
    "fiqh_filter": "Filtering evidence...",
    "fiqh_assess": "Assessing evidence sufficiency...",
    "fiqh_refine": "Refining query...",
}

# Human-readable status messages for each tool call
TOOL_STATUS_MESSAGES = {
    "check_if_non_islamic_tool": "Checking if query is within scope...",
    "translate_to_english_tool": "Translating query...",
    "enhance_query_tool": "Enhancing query for better results...",
    "retrieve_shia_documents_tool": "Retrieving Shia documents...",
    "retrieve_sunni_documents_tool": "Retrieving Sunni documents...",
    "retrieve_quran_tafsir_tool": "Retrieving Quran & Tafsir...",
}


# Categories that trigger the FAIR-RAG fiqh path
VALID_FIQH_CATEGORIES = {"VALID_OBVIOUS", "VALID_SMALL", "VALID_LARGE", "VALID_REASONER"}


def sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def chat_pipeline_streaming_agentic(
    user_query: str,
    session_id: str,
    target_language: str = "english",
    config: Optional[AgentConfig] = None
) -> StreamingResponse:
    """
    Agentic chat pipeline using LangGraph with proper SSE protocol.

    SSE Event types emitted:
      - status:            {"step": str, "message": str}   -- per node / tool call
      - response_chunk:    {"token": str}                  -- per LLM token
      - response_end:      {}                              -- after last token
      - hadith_references: [...]                           -- hadith docs JSON
      - quran_references:  [...]                           -- quran/tafsir docs JSON
      - error:             {"message": str}                -- on any error
      - done:              {}                              -- final event
    """
    print(f"[AGENTIC PIPELINE] Starting for query: {user_query[:100]}")

    agent_config = config or DEFAULT_AGENT_CONFIG
    agent = ChatAgent(agent_config)

    async def response_generator() -> AsyncGenerator[str, None]:
        assistant_text = ""
        history_written = False

        try:
            final_state = None
            emitted_tool_call_ids = set()

            async for event in agent.astream(
                user_query=user_query,
                session_id=session_id,
                target_language=target_language,
                config=agent_config.to_dict(),
                streaming_mode=True
            ):
                for node_name, node_state in event.items():
                    print(f"[AGENTIC PIPELINE] Node: {node_name}")
                    final_state = node_state

                    # Emit a status event for each node
                    node_msg = NODE_STATUS_MESSAGES.get(node_name)
                    if node_msg:
                        yield sse_event("status", {"step": node_name, "message": node_msg})

                    # Emit status events for any tool calls the agent made
                    messages = node_state.get("messages", []) if isinstance(node_state, dict) else []
                    for msg in messages:
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for index, tc in enumerate(msg.tool_calls):
                                tool_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                                tool_call_id = None
                                if isinstance(tc, dict):
                                    tool_call_id = tc.get("id")
                                else:
                                    tool_call_id = getattr(tc, "id", None)
                                if not tool_call_id:
                                    tool_call_id = f"{node_name}:{index}:{tool_name}"

                                if tool_name and tool_call_id not in emitted_tool_call_ids:
                                    emitted_tool_call_ids.add(tool_call_id)
                                    tool_msg = TOOL_STATUS_MESSAGES.get(tool_name, f"Running {tool_name}...")
                                    yield sse_event("status", {"step": tool_name, "message": tool_msg})

            if final_state is None:
                yield sse_event("error", {"message": "No response generated."})
                yield sse_event("done", {})
                return

            runtime_session_id = final_state.get("runtime_session_id", session_id)

            # --- Early exit (fiqh / non-Islamic) ---
            if final_state.get("early_exit_message"):
                assistant_text = final_state["early_exit_message"]
                yield sse_event("response_chunk", {"token": assistant_text})
                yield sse_event("response_end", {})
                from services import chat_persistence_service

                chat_persistence_service.append_turn_to_runtime_history(
                    runtime_session_id=runtime_session_id,
                    user_query=user_query,
                    assistant_text=assistant_text,
                )
                history_written = True
                yield sse_event("done", {})
                return

            # --- Fiqh FAIR-RAG streaming path ---
            if final_state.get("fiqh_category") in VALID_FIQH_CATEGORIES:
                from modules.fiqh.generator import (
                    _prompt as fiqh_prompt,
                    _format_evidence,
                    _build_references_section,
                    INSUFFICIENT_WARNING,
                    FATWA_DISCLAIMER,
                )
                from core import chat_models
                from core.utils import format_fiqh_references_as_json

                # Emit per-stage status events for the fiqh pipeline stages
                # (sub-graph runs as a black box; we emit pre-canned stage messages)
                fiqh_stages = [
                    ("fiqh_decompose", "Decomposing fiqh query..."),
                    ("fiqh_retrieve", "Retrieving fiqh documents..."),
                    ("fiqh_filter", "Filtering evidence..."),
                    ("fiqh_assess", "Assessing evidence sufficiency..."),
                ]
                for stage_step, stage_msg in fiqh_stages:
                    yield sse_event("status", {"step": stage_step, "message": stage_msg})

                yield sse_event("status", {"step": "generate_fiqh_response", "message": "Generating fiqh answer..."})

                fiqh_docs = final_state.get("fiqh_filtered_docs", [])
                sea_result = final_state.get("fiqh_sea_result")
                is_sufficient = getattr(sea_result, "verdict", "INSUFFICIENT") == "SUFFICIENT"

                if not fiqh_docs:
                    # No evidence retrieved — emit fallback message
                    fallback = (
                        "I was unable to retrieve relevant rulings for this question. "
                        "Please consult Sistani's official resources at sistani.org "
                        "or contact his office directly." + FATWA_DISCLAIMER
                    )
                    assistant_text = fallback
                    yield sse_event("response_chunk", {"token": fallback})
                    yield sse_event("response_end", {})
                else:
                    # Stream fiqh answer token-by-token using fiqh-specific prompt (D-06)
                    model = chat_models.get_generator_model()
                    chain = fiqh_prompt | model
                    response_tokens = []
                    for chunk in chain.stream({
                        "query": user_query,
                        "evidence": _format_evidence(fiqh_docs),
                    }):
                        token = getattr(chunk, "content", str(chunk) if chunk is not None else "")
                        if token:
                            response_tokens.append(token)
                            yield sse_event("response_chunk", {"token": token})

                    answer_text = "".join(response_tokens).strip()

                    # Post-process: append ## Sources, optional insufficient warning, fatwa disclaimer
                    references_section = _build_references_section(answer_text, fiqh_docs)
                    if references_section:
                        yield sse_event("response_chunk", {"token": references_section})

                    if not is_sufficient:
                        yield sse_event("response_chunk", {"token": INSUFFICIENT_WARNING})
                        answer_text += INSUFFICIENT_WARNING

                    yield sse_event("response_chunk", {"token": FATWA_DISCLAIMER})
                    answer_text += FATWA_DISCLAIMER
                    if references_section:
                        answer_text += references_section

                    assistant_text = answer_text
                    yield sse_event("response_end", {})

                # Persist fiqh answer to conversation history
                if assistant_text and not history_written:
                    from services import chat_persistence_service
                    chat_persistence_service.append_turn_to_runtime_history(
                        runtime_session_id=runtime_session_id,
                        user_query=user_query,
                        assistant_text=assistant_text,
                    )
                    history_written = True

                # Emit fiqh_references SSE event (D-14, INTG-05)
                if fiqh_docs:
                    fiqh_json = format_fiqh_references_as_json(fiqh_docs)
                    yield sse_event("fiqh_references", {"references": fiqh_json})

            # --- Existing hadith/non-fiqh streaming path ---
            else:
                hadith_docs = final_state.get("retrieved_docs", [])
                quran_docs = final_state.get("quran_docs", [])
                all_docs = hadith_docs + quran_docs

                if all_docs or final_state.get("final_response"):
                    if final_state.get("final_response"):
                        assistant_text = final_state["final_response"]
                        yield sse_event("response_chunk", {"token": assistant_text})
                        yield sse_event("response_end", {})
                    else:
                        from core import chat_models, prompt_templates
                        from core.memory import make_history

                        yield sse_event("status", {"step": "generate_response", "message": "Generating response..."})

                        references = utils.compact_format_references(all_docs)
                        chat_model = chat_models.get_generator_model()
                        prompt = prompt_templates.generator_prompt_template
                        chain = prompt | chat_model
                        history_messages = make_history(runtime_session_id).messages

                        response_tokens = []
                        for chunk in chain.stream(
                            {
                                "target_language": target_language,
                                "query": user_query,
                                "references": references,
                                "chat_history": history_messages,
                            },
                        ):
                            token = getattr(chunk, "content", str(chunk) if chunk is not None else "")
                            if token:
                                response_tokens.append(token)
                                yield sse_event("response_chunk", {"token": token})

                        assistant_text = "".join(response_tokens).strip()
                        yield sse_event("response_end", {})
                else:
                    errors = final_state.get("errors", []) if isinstance(final_state, dict) else []
                    if any("quran_tafsir retrieval error" in error for error in errors):
                        assistant_text = "I couldn't access the Quran and Tafsir sources I needed just now, so I can't answer this reliably."
                    elif any("retrieval error" in error for error in errors):
                        assistant_text = "I couldn't access enough source material to answer this reliably right now."
                    else:
                        assistant_text = "I apologize, but I couldn't retrieve enough information to answer your question."
                    yield sse_event("response_chunk", {"token": assistant_text})
                    yield sse_event("response_end", {})

                if assistant_text and not history_written:
                    from services import chat_persistence_service

                    chat_persistence_service.append_turn_to_runtime_history(
                        runtime_session_id=runtime_session_id,
                        user_query=user_query,
                        assistant_text=assistant_text,
                    )
                    history_written = True

                if hadith_docs:
                    hadith_json = utils.format_references_as_json(hadith_docs)
                    yield sse_event("hadith_references", {"references": hadith_json})

                if quran_docs:
                    quran_json = utils.format_quran_references_as_json(quran_docs)
                    yield sse_event("quran_references", {"references": quran_json})

            yield sse_event("done", {})

        except Exception as e:
            print(f"[AGENTIC PIPELINE] Error: {e}")
            import traceback
            traceback.print_exc()
            if assistant_text and not history_written:
                try:
                    from services import chat_persistence_service

                    chat_persistence_service.append_turn_to_runtime_history(
                        runtime_session_id=final_state.get("runtime_session_id", session_id) if final_state else session_id,
                        user_query=user_query,
                        assistant_text=assistant_text,
                    )
                except Exception as memory_exc:
                    print(f"[AGENTIC PIPELINE] Failed to append runtime history after error: {memory_exc}")
            yield sse_event("error", {"message": str(e)})
            yield sse_event("done", {})

    return StreamingResponse(response_generator(), media_type="text/event-stream")


def chat_pipeline_agentic(
    user_query: str,
    session_id: str,
    target_language: str = "english",
    config: Optional[AgentConfig] = None
) -> dict:
    """
    Non-streaming agentic chat pipeline.

    Args:
        user_query: The user's question
        session_id: Session identifier
        target_language: User's preferred language
        config: Optional AgentConfig for customization

    Returns:
        Dictionary with response and metadata
    """
    print(f"[AGENTIC PIPELINE NON-STREAM] Starting for query: {user_query[:100]}")

    agent_config = config or DEFAULT_AGENT_CONFIG
    agent = ChatAgent(agent_config)

    final_state = agent.invoke(
        user_query=user_query,
        session_id=session_id,
        target_language=target_language,
        config=agent_config.to_dict()
    )

    response_data = {
        "response": final_state.get("final_response", "Unable to generate response"),
        "retrieved_docs": final_state.get("retrieved_docs", []),
        "quran_docs": final_state.get("quran_docs", []),
        "metadata": {
            "iterations": final_state.get("iterations", 0),
            "classification_checked": final_state.get("classification_checked", False),
            "query_enhanced": final_state.get("query_enhanced", False),
            "retrieval_completed": final_state.get("retrieval_completed", False),
            "shia_docs_count": final_state.get("shia_docs_count", 0),
            "sunni_docs_count": final_state.get("sunni_docs_count", 0),
            "quran_docs_count": final_state.get("quran_docs_count", 0),
            "errors": final_state.get("errors", [])
        }
    }

    return response_data
