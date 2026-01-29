"""
LangGraph-based agentic chat agent for Islamic education.

This agent autonomously decides which tools to use and when,
replacing the hardcoded pipeline with intelligent decision-making.
"""

from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from agents.state.chat_state import ChatState
from agents.config.agent_config import AgentConfig, DEFAULT_AGENT_CONFIG
from agents.prompts.agent_prompts import (
    AGENT_SYSTEM_PROMPT,
    EARLY_EXIT_NON_ISLAMIC,
    EARLY_EXIT_FIQH
)
from agents.tools import (
    check_if_non_islamic_tool,
    check_if_fiqh_tool,
    translate_to_english_tool,
    enhance_query_tool,
    retrieve_shia_documents_tool,
    retrieve_sunni_documents_tool,
    retrieve_combined_documents_tool
)
from core.config import OPENAI_API_KEY
from core import utils


class ChatAgent:
    """
    LangGraph-based agentic chat system for Islamic education.
    
    The agent autonomously decides:
    - Whether to classify the query
    - Whether to translate
    - Whether to enhance the query
    - Which documents to retrieve
    - When to generate the final response
    """
    
    def __init__(self, config: AgentConfig = None):
        """
        Initialize the chat agent.
        
        Args:
            config: Configuration for the agent (uses defaults if not provided)
        """
        self.config = config or DEFAULT_AGENT_CONFIG
        
        # Initialize the LLM with tool binding
        self.llm = self._create_llm_with_tools()
        
        # Build the graph
        self.graph = self._build_graph()
        
        # Compile the graph with checkpointing
        self.checkpointer = MemorySaver()
        self.compiled_graph = self.graph.compile(checkpointer=self.checkpointer)
    
    def _create_llm_with_tools(self):
        """Create LLM with tools bound."""
        tools = [
            check_if_non_islamic_tool,
            check_if_fiqh_tool,
            translate_to_english_tool,
            enhance_query_tool,
            retrieve_shia_documents_tool,
            retrieve_sunni_documents_tool,
            retrieve_combined_documents_tool
        ]
        
        llm = init_chat_model(
            model=self.config.model.agent_model,
            openai_api_key=OPENAI_API_KEY,
            temperature=self.config.model.temperature,
            max_tokens=self.config.model.max_tokens
        )
        
        return llm.bind_tools(tools)
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph."""
        
        # Create the graph
        workflow = StateGraph(ChatState)
        
        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tool_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("check_early_exit", self._check_early_exit_node)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges from agent
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "generate": "generate_response",
                "exit": "check_early_exit",
                "end": END
            }
        )
        
        # Tools go back to agent
        workflow.add_edge("tools", "agent")
        
        # Generate response ends
        workflow.add_edge("generate_response", END)
        
        # Check early exit ends
        workflow.add_edge("check_early_exit", END)
        
        return workflow
    
    def _agent_node(self, state: ChatState) -> ChatState:
        """
        Agent node - makes decisions about which tools to call.
        """
        print(f"[AGENT NODE] Iteration {state['iterations']}")
        
        # Increment iterations
        state["iterations"] += 1
        
        # Check max iterations
        if state["iterations"] > self.config.max_iterations:
            print(f"[AGENT NODE] Max iterations reached ({self.config.max_iterations})")
            state["should_end"] = True
            state["errors"].append(f"Max iterations ({self.config.max_iterations}) reached")
            return state
        
        # Build messages for the agent
        messages = state["messages"].copy()
        
        # Add system prompt if this is the first iteration
        if state["iterations"] == 1:
            messages.insert(0, SystemMessage(content=AGENT_SYSTEM_PROMPT))
            
            # Add the user query
            user_message = f"User query: {state['user_query']}"
            if state['target_language'] != "english":
                user_message += f"\nUser's preferred language: {state['target_language']}"
            
            messages.append(HumanMessage(content=user_message))
        
        # Add context about what has been done so far
        if state["iterations"] > 1:
            context_parts = []
            
            if state.get("is_non_islamic") is not None:
                context_parts.append(f"Classification: is_non_islamic={state['is_non_islamic']}")
            
            if state.get("is_fiqh") is not None:
                context_parts.append(f"Classification: is_fiqh={state['is_fiqh']}")
            
            if state.get("enhanced_query"):
                context_parts.append(f"Query enhanced: {state['enhanced_query']}")
            
            if state.get("retrieved_docs"):
                context_parts.append(f"Documents retrieved: {len(state['retrieved_docs'])} docs")
            
            if context_parts:
                context_msg = "Current state:\n" + "\n".join(context_parts)
                messages.append(HumanMessage(content=context_msg))
        
        # Invoke the agent
        try:
            response = self.llm.invoke(messages)
            state["messages"].append(response)
            
            print(f"[AGENT NODE] Agent response: {response.content if hasattr(response, 'content') else 'tool calls'}")
            
        except Exception as e:
            print(f"[AGENT NODE] Error: {e}")
            state["errors"].append(f"Agent error: {str(e)}")
            state["should_end"] = True
        
        return state
    
    def _tool_node(self, state: ChatState) -> ChatState:
        """
        Tool execution node - executes the tools selected by the agent.
        """
        print("[TOOL NODE] Executing tools")
        
        # Get the last message (should have tool calls)
        last_message = state["messages"][-1]
        
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            print("[TOOL NODE] No tool calls found")
            return state
        
        # Create tool node and execute
        tool_node = ToolNode([
            check_if_non_islamic_tool,
            check_if_fiqh_tool,
            translate_to_english_tool,
            enhance_query_tool,
            retrieve_shia_documents_tool,
            retrieve_sunni_documents_tool,
            retrieve_combined_documents_tool
        ])
        
        # Execute tools
        result = tool_node.invoke(state)
        
        # Update state based on tool results
        for message in result.get("messages", []):
            if hasattr(message, "name"):
                tool_name = message.name
                content = message.content
                
                print(f"[TOOL NODE] Tool {tool_name} result: {content[:200] if isinstance(content, str) else content}")
                
                # Update state based on tool results
                if tool_name == "check_if_non_islamic_tool":
                    try:
                        import json
                        result_data = json.loads(content) if isinstance(content, str) else content
                        state["is_non_islamic"] = result_data.get("is_non_islamic", False)
                        state["classification_checked"] = True
                    except:
                        pass
                
                elif tool_name == "check_if_fiqh_tool":
                    try:
                        import json
                        result_data = json.loads(content) if isinstance(content, str) else content
                        state["is_fiqh"] = result_data.get("is_fiqh", False)
                        state["classification_checked"] = True
                    except:
                        pass
                
                elif tool_name == "enhance_query_tool":
                    try:
                        import json
                        result_data = json.loads(content) if isinstance(content, str) else content
                        state["enhanced_query"] = result_data.get("enhanced_query", state["user_query"])
                        state["query_enhanced"] = True
                    except:
                        pass
                
                elif tool_name in ["retrieve_shia_documents_tool", "retrieve_sunni_documents_tool", "retrieve_combined_documents_tool"]:
                    try:
                        import json
                        result_data = json.loads(content) if isinstance(content, str) else content
                        docs = result_data.get("documents", [])
                        state["retrieved_docs"].extend(docs)
                        
                        if "shia_count" in result_data:
                            state["shia_docs_count"] = result_data["shia_count"]
                        if "sunni_count" in result_data:
                            state["sunni_docs_count"] = result_data["sunni_count"]
                        if result_data.get("source") == "shia":
                            state["shia_docs_count"] = result_data.get("count", 0)
                        if result_data.get("source") == "sunni":
                            state["sunni_docs_count"] = result_data.get("count", 0)
                        
                        state["retrieval_completed"] = True
                    except Exception as e:
                        print(f"[TOOL NODE] Error processing retrieval result: {e}")
        
        # Merge tool messages from result into state and return state
        # This preserves our state updates while keeping the tool response messages
        state["messages"] = result.get("messages", state["messages"])
        return state
    
    def _generate_response_node(self, state: ChatState) -> ChatState:
        """
        Generate the final response based on retrieved documents.
        """
        print("[GENERATE RESPONSE NODE] Generating final response")
        
        # Format references
        references = utils.compact_format_references(state["retrieved_docs"])
        
        # Create generation prompt
        generation_messages = [
            SystemMessage(content=AGENT_SYSTEM_PROMPT),
            HumanMessage(content=f"""User query: {state['user_query']}

Retrieved references:
{references}

Generate a comprehensive, accurate response that directly addresses the user's question using the retrieved sources. Cite specific books, hadith numbers, and scholars when referencing the sources.""")
        ]
        
        # Generate response (non-streaming for now in the graph)
        try:
            from core.chat_models import get_generator_model
            llm = get_generator_model()
            response = llm.invoke(generation_messages)
            state["final_response"] = response.content
            state["response_generated"] = True
            print(f"[GENERATE RESPONSE NODE] Response generated: {len(response.content)} chars")
        except Exception as e:
            print(f"[GENERATE RESPONSE NODE] Error: {e}")
            state["errors"].append(f"Response generation error: {str(e)}")
            state["final_response"] = "I apologize, but I encountered an error generating the response."
        
        return state
    
    def _check_early_exit_node(self, state: ChatState) -> ChatState:
        """
        Handle early exit scenarios (non-Islamic or fiqh queries).
        """
        print("[CHECK EARLY EXIT NODE]")
        
        if state.get("is_non_islamic"):
            state["final_response"] = EARLY_EXIT_NON_ISLAMIC
            state["early_exit_message"] = EARLY_EXIT_NON_ISLAMIC
        elif state.get("is_fiqh"):
            state["final_response"] = EARLY_EXIT_FIQH
            state["early_exit_message"] = EARLY_EXIT_FIQH
        else:
            state["final_response"] = "Unable to process the query."
        
        return state
    
    def _should_continue(self, state: ChatState) -> Literal["continue", "generate", "exit", "end"]:
        """
        Decide the next step based on the current state.
        """
        # Check for early exit conditions
        if state.get("is_non_islamic") or state.get("is_fiqh"):
            print("[ROUTING] Early exit: non-Islamic or fiqh query")
            return "exit"
        
        # Check if should end
        if state.get("should_end"):
            print("[ROUTING] Should end flag set")
            return "end"
        
        # Check the last message
        last_message = state["messages"][-1] if state["messages"] else None
        
        if last_message is None:
            print("[ROUTING] No messages, ending")
            return "end"
        
        # If agent called tools, continue to tool execution
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            print(f"[ROUTING] Continue to tools: {len(last_message.tool_calls)} tool calls")
            return "continue"
        
        # If we have retrieved docs, generate response
        if state.get("retrieval_completed") and state.get("retrieved_docs"):
            print("[ROUTING] Documents retrieved, generate response")
            return "generate"
        
        # If no tool calls and no response ready, we might be done
        # This handles cases where the agent decides it's done without calling more tools
        if state["iterations"] > 1:
            print("[ROUTING] No more tool calls, ending")
            return "end"
        
        # Default: continue
        print("[ROUTING] Default: continue")
        return "continue"
    
    def invoke(self, user_query: str, session_id: str, target_language: str = "english", config: dict = None):
        """
        Invoke the agent with a user query.
        
        Args:
            user_query: The user's question
            session_id: Session identifier
            target_language: User's preferred language
            config: Optional configuration overrides
            
        Returns:
            Final state after agent execution
        """
        from agents.state.chat_state import create_initial_state
        
        # Create initial state
        initial_state = create_initial_state(
            user_query=user_query,
            session_id=session_id,
            target_language=target_language,
            config=config or self.config.to_dict()
        )
        
        # Run the graph
        final_state = self.compiled_graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": session_id}}
        )
        
        return final_state
    
    async def astream(self, user_query: str, session_id: str, target_language: str = "english", config: dict = None):
        """
        Stream the agent execution.
        
        Args:
            user_query: The user's question
            session_id: Session identifier
            target_language: User's preferred language
            config: Optional configuration overrides
            
        Yields:
            State updates as the agent runs
        """
        from agents.state.chat_state import create_initial_state
        
        # Create initial state
        initial_state = create_initial_state(
            user_query=user_query,
            session_id=session_id,
            target_language=target_language,
            config=config or self.config.to_dict()
        )
        
        # Stream the graph
        async for event in self.compiled_graph.astream(
            initial_state,
            config={"configurable": {"thread_id": session_id}}
        ):
            yield event





