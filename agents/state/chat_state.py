"""
State schema for the LangGraph chat agent.
Defines all the information tracked throughout the conversation flow.
"""

from typing import TypedDict, Optional, List, Dict, Any, Annotated
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class ChatState(TypedDict):
    """
    State for the agentic chat pipeline.
    
    This state is passed between nodes in the LangGraph and tracks
    all relevant information throughout the conversation flow.
    """
    
    # Core conversation data
    messages: Annotated[List[BaseMessage], add_messages]
    """Message history for the agent (uses add_messages reducer)"""
    
    user_query: str
    """Original user query"""
    
    session_id: str
    """Session identifier for conversation persistence"""
    
    target_language: str
    """User's preferred language (default: "english")"""
    
    # Translation tracking
    is_translated: bool
    """Whether the query has been translated to English"""
    
    original_language: Optional[str]
    """Original language of the query if translated"""
    
    # Classification results
    is_non_islamic: Optional[bool]
    """True if query is not about Islamic education"""
    
    is_fiqh: Optional[bool]
    """True if query asks for a fiqh ruling"""
    
    classification_checked: bool
    """Whether classification has been performed"""
    
    # Query enhancement
    enhanced_query: Optional[str]
    """Enhanced version of the query for better retrieval"""
    
    query_enhanced: bool
    """Whether query enhancement has been performed"""
    
    # Document retrieval
    retrieved_docs: List[Dict[str, Any]]
    """Retrieved documents from knowledge base"""
    
    shia_docs_count: int
    """Number of Shia documents retrieved"""
    
    sunni_docs_count: int
    """Number of Sunni documents retrieved"""
    
    retrieval_completed: bool
    """Whether document retrieval has been performed"""
    
    # Response generation
    final_response: Optional[str]
    """Final generated response to the user"""
    
    response_generated: bool
    """Whether final response has been generated"""
    
    # Configuration
    config: Dict[str, Any]
    """Configuration parameters (retrieval settings, model params, etc.)"""
    
    # Flow control
    should_end: bool
    """Whether the agent should stop (e.g., after classification rejection)"""
    
    early_exit_message: Optional[str]
    """Message to send if exiting early (e.g., non-Islamic or fiqh query)"""
    
    # Error tracking
    errors: List[str]
    """List of errors encountered during processing"""
    
    # Metadata
    iterations: int
    """Number of agent iterations (for debugging and limits)"""


def create_initial_state(
    user_query: str,
    session_id: str,
    target_language: str = "english",
    config: Optional[Dict[str, Any]] = None
) -> ChatState:
    """
    Create initial state for a new chat interaction.
    
    Args:
        user_query: The user's question
        session_id: Session identifier
        target_language: User's preferred language
        config: Optional configuration overrides
        
    Returns:
        ChatState with initial values
    """
    return ChatState(
        messages=[],
        user_query=user_query,
        session_id=session_id,
        target_language=target_language,
        is_translated=False,
        original_language=None,
        is_non_islamic=None,
        is_fiqh=None,
        classification_checked=False,
        enhanced_query=None,
        query_enhanced=False,
        retrieved_docs=[],
        shia_docs_count=0,
        sunni_docs_count=0,
        retrieval_completed=False,
        final_response=None,
        response_generated=False,
        config=config or {},
        should_end=False,
        early_exit_message=None,
        errors=[],
        iterations=0
    )





