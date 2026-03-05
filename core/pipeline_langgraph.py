"""
LangGraph-based agentic pipeline for chat.

This replaces the hardcoded pipeline with an intelligent agent
that decides which tools to use and when.
"""

from typing import Optional, AsyncGenerator
from fastapi.responses import StreamingResponse
from agents.core.chat_agent import ChatAgent
from agents.config.agent_config import AgentConfig, DEFAULT_AGENT_CONFIG
from core import utils
import json


# Human-readable status messages for each agent node
NODE_STATUS_MESSAGES = {
    "fiqh_classification": "Checking query classification...",
    "agent": "Agent thinking...",
    "tools": "Looking for information...",
    "generate_response": "Generating response...",
    "check_early_exit": "Processing...",
}

# Human-readable status messages for each tool call
TOOL_STATUS_MESSAGES = {
    "check_if_non_islamic_tool": "Checking if query is within scope...",
    "check_if_fiqh_tool": "Checking query classification...",
    "translate_to_english_tool": "Translating query...",
    "enhance_query_tool": "Enhancing query for better results...",
    "retrieve_shia_documents_tool": "Retrieving Shia documents...",
    "retrieve_sunni_documents_tool": "Retrieving Sunni documents...",
    "retrieve_combined_documents_tool": "Retrieving documents from all sources...",
    "retrieve_quran_tafsir_tool": "Retrieving Quran & Tafsir...",
}


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
        try:
            final_state = None
            emitted_tool_statuses = set()

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
                            for tc in msg.tool_calls:
                                tool_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                                if tool_name and tool_name not in emitted_tool_statuses:
                                    emitted_tool_statuses.add(tool_name)
                                    tool_msg = TOOL_STATUS_MESSAGES.get(tool_name, f"Running {tool_name}...")
                                    yield sse_event("status", {"step": tool_name, "message": tool_msg})

            if final_state is None:
                yield sse_event("error", {"message": "No response generated."})
                yield sse_event("done", {})
                return

            # --- Early exit (fiqh / non-Islamic) ---
            if final_state.get("early_exit_message"):
                yield sse_event("response_chunk", {"token": final_state["early_exit_message"]})
                yield sse_event("response_end", {})
                yield sse_event("done", {})
                return

            # --- Stream LLM response token-by-token ---
            hadith_docs = final_state.get("retrieved_docs", [])
            quran_docs = final_state.get("quran_docs", [])
            all_docs = hadith_docs + quran_docs

            if all_docs or final_state.get("final_response"):
                if final_state.get("final_response"):
                    # Non-streaming path returned a pre-built response (shouldn't happen
                    # with streaming_mode=True, but handle gracefully)
                    yield sse_event("response_chunk", {"token": final_state["final_response"]})
                    yield sse_event("response_end", {})
                else:
                    # Stream the response token-by-token
                    from core.memory import with_redis_history, make_history, trim_history
                    from core import chat_models, prompt_templates

                    yield sse_event("status", {"step": "generate_response", "message": "Generating response..."})

                    references = utils.compact_format_references(all_docs)
                    chat_model = chat_models.get_generator_model()
                    prompt = prompt_templates.generator_prompt_template
                    chain = prompt | chat_model
                    chain_with_history = with_redis_history(chain)

                    for chunk in chain_with_history.stream(
                        {
                            "target_language": target_language,
                            "query": user_query,
                            "references": references,
                        },
                        config={"configurable": {"session_id": session_id}},
                    ):
                        token = getattr(chunk, "content", str(chunk) if chunk is not None else "")
                        if token:
                            yield sse_event("response_chunk", {"token": token})

                    hist = make_history(session_id)
                    trim_history(hist)

                    yield sse_event("response_end", {})
            else:
                fallback = "I apologize, but I couldn't retrieve enough information to answer your question."
                yield sse_event("response_chunk", {"token": fallback})
                yield sse_event("response_end", {})

            # --- Separate reference events ---
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
