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
from itertools import chain


async def chat_pipeline_streaming_agentic(
    user_query: str,
    session_id: str,
    target_language: str = "english",
    config: Optional[AgentConfig] = None
) -> StreamingResponse:
    """
    Agentic chat pipeline using LangGraph.
    
    The agent autonomously decides which tools to use:
    - Classification (if needed)
    - Translation (if needed)
    - Query enhancement
    - Document retrieval
    - Response generation
    
    Args:
        user_query: The user's question
        session_id: Session identifier for conversation persistence
        target_language: User's preferred language (default: "english")
        config: Optional AgentConfig for customization
        
    Returns:
        StreamingResponse with the generated response and references
    """
    print(f"[AGENTIC PIPELINE] Starting for query: {user_query[:100]}")
    
    # Use provided config or default
    agent_config = config or DEFAULT_AGENT_CONFIG
    
    # Create the agent
    agent = ChatAgent(agent_config)
    
    # Create response generator
    async def response_generator() -> AsyncGenerator[str, None]:
        """Generate streaming response from the agent."""
        
        try:
            # Stream agent execution
            final_state = None
            
            async for event in agent.astream(
                user_query=user_query,
                session_id=session_id,
                target_language=target_language,
                config=agent_config.to_dict()
            ):
                # Track the final state
                # Each event is a dict with node names as keys
                for node_name, node_state in event.items():
                    print(f"[AGENTIC PIPELINE] Node: {node_name}")
                    final_state = node_state
                    
                    # Optionally stream intermediate steps
                    if agent_config.stream_intermediate_steps:
                        if node_name == "tools":
                            yield f"data: [TOOL_EXECUTION]\n\n"
                        elif node_name == "agent":
                            yield f"data: [AGENT_THINKING]\n\n"
            
            # Check if we have a final response
            if final_state is None:
                yield "I apologize, but I couldn't process your query."
                return
            
            # Handle early exit messages
            if final_state.get("early_exit_message"):
                yield final_state["early_exit_message"]
                return
            
            # Check for final response
            if final_state.get("final_response"):
                # If target language is not English, we'd translate here
                # For now, we yield the English response
                yield final_state["final_response"]
            else:
                # No final response generated - might need to generate it ourselves
                # This happens if the agent completes without calling generate_response
                if final_state.get("retrieval_completed") and final_state.get("retrieved_docs"):
                    # Generate response using the traditional generator
                    from core.memory import with_redis_history
                    from core import chat_models, prompt_templates
                    
                    references = utils.compact_format_references(final_state["retrieved_docs"])
                    chat_model = chat_models.get_generator_model()
                    prompt = prompt_templates.generator_prompt_template
                    chain = prompt | chat_model
                    chain_with_history = with_redis_history(chain)
                    
                    # Stream the response
                    for chunk in chain_with_history.stream(
                        {
                            "target_language": target_language,
                            "query": user_query,
                            "references": references
                        },
                        config={"configurable": {"session_id": session_id}},
                    ):
                        yield getattr(chunk, "content", str(chunk) if chunk is not None else "")
                    
                    # Trim history
                    from core.memory import make_history, trim_history
                    hist = make_history(session_id)
                    trim_history(hist)
                else:
                    yield "I apologize, but I couldn't retrieve enough information to answer your question."
            
            # Add references at the end
            if final_state.get("retrieved_docs"):
                references_json = utils.format_references_as_json(final_state["retrieved_docs"])
                yield '\n\n\n[REFERENCES]\n\n\n'
                yield json.dumps(references_json)
        
        except Exception as e:
            print(f"[AGENTIC PIPELINE] Error: {e}")
            import traceback
            traceback.print_exc()
            yield f"An error occurred: {str(e)}"
    
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
    
    # Use provided config or default
    agent_config = config or DEFAULT_AGENT_CONFIG
    
    # Create the agent
    agent = ChatAgent(agent_config)
    
    # Run the agent
    final_state = agent.invoke(
        user_query=user_query,
        session_id=session_id,
        target_language=target_language,
        config=agent_config.to_dict()
    )
    
    # Build response
    response_data = {
        "response": final_state.get("final_response", "Unable to generate response"),
        "retrieved_docs": final_state.get("retrieved_docs", []),
        "metadata": {
            "iterations": final_state.get("iterations", 0),
            "classification_checked": final_state.get("classification_checked", False),
            "query_enhanced": final_state.get("query_enhanced", False),
            "retrieval_completed": final_state.get("retrieval_completed", False),
            "shia_docs_count": final_state.get("shia_docs_count", 0),
            "sunni_docs_count": final_state.get("sunni_docs_count", 0),
            "errors": final_state.get("errors", [])
        }
    }
    
    return response_data





