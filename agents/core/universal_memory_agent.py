import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session
import json
from enum import Enum

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.models.user_memory_models import UserMemoryProfile
from agents.prompts.memory_prompts import chat_memory_analysis_prompt
from core.chat_models import get_generator_model
from .memory_consolidator import MemoryConsolidator
from services.memory_service import MemoryService
from services.consolidation_service import ConsolidationService
from core.logging_config import get_memory_logger

logger = get_memory_logger(level=logging.DEBUG)

class InteractionType(str, Enum):
    """All possible user interaction types that can trigger memory updates"""
    CHAT = "chat"
    HIKMAH_ELABORATION = "hikmah_elaboration"
    LESSON_COMPLETION = "lesson_completion"
    QUIZ_RESULT = "quiz_result"
    USER_FEEDBACK = "user_feedback"
    LEARNING_PATH_PROGRESS = "learning_path_progress"
    ASSESSMENT = "assessment"
    QUESTIONNAIRE = "questionnaire"
    CONTENT_RATING = "content_rating"
    STUDY_SESSION = "study_session"

class UniversalMemoryAgent:
    """
    Universal Memory Agent that can analyze ANY type of user interaction
    and extract meaningful insights for long-term memory storage.
    
    This agent is interaction-agnostic and can handle:
    - Chat conversations
    - Lesson completions  
    - Quiz results
    - Hikmah elaboration requests
    - User feedback
    - Learning assessments
    - And any future interaction types
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_generator_model()
        self.memory_service = MemoryService(db)
        self.consolidation_service = ConsolidationService(db)
        self.consolidator = MemoryConsolidator(self.consolidation_service)
    
    async def analyze_interaction(self, 
                                user_id: str,
                                interaction_type: InteractionType,
                                interaction_data: Dict[str, Any],
                                session_id: Optional[str] = None,
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Universal method to analyze ANY user interaction and update memory.
        
        Args:
            user_id: Unique user identifier
            interaction_type: Type of interaction (chat, lesson_completion, quiz, etc.)
            interaction_data: The actual interaction data (flexible structure)
            session_id: Optional session identifier
            context: Optional additional context
        
        Returns:
            Dict with analysis results and memory updates
            
        Example Usage:
        
        # Chat interaction
        await agent.analyze_interaction(
            user_id="user123",
            interaction_type=InteractionType.CHAT,
            interaction_data={
                "user_query": "What is Imamate?",
                "ai_response": "Imamate is the belief that...",
                "chat_history": [...]
            }
        )
        
        # Lesson completion
        await agent.analyze_interaction(
            user_id="user123", 
            interaction_type=InteractionType.LESSON_COMPLETION,
            interaction_data={
                "lesson_id": "prayer-basics-001",
                "lesson_title": "Introduction to Prayer",
                "lesson_topics": ["prayer", "wudu", "qibla"],
                "completion_time_minutes": 15,
                "user_engagement_score": 0.85,
                "lesson_summary": "This lesson covers the basics of Shia prayer..."
            }
        )
        
        # Quiz result
        await agent.analyze_interaction(
            user_id="user123",
            interaction_type=InteractionType.QUIZ_RESULT,
            interaction_data={
                "quiz_id": "imamate-quiz-001",
                "lesson_id": "imamate-basics",
                "score": 0.75,
                "total_questions": 10,
                "correct_answers": 7,
                "topics_tested": ["imamate", "twelve_imams", "succession"],
                "incorrect_topics": ["imam_mahdi", "occultation"],
                "time_taken_minutes": 8
            }
        )
        """
        
        # Prepare event payloads
        event_data = {
            "interaction_type": interaction_type.value,
            "interaction_data": interaction_data,
            "session_id": session_id,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        trigger_context = {
            "method": "universal_analysis", 
            "agent": "UniversalMemoryAgent",
            "interaction_type": interaction_type.value
        }
        
        # Get or create user memory profile
        memory_profile = await self._get_or_create_memory_profile(user_id)
        # Create a pending event record
        memory_event = self.memory_service.create_event(
            profile_id=memory_profile.id,
            event_type=interaction_type.value,
            event_data=event_data,
            trigger_context=trigger_context,
            processing_status="pending",
        )
        logger.info(
            "Analyzing interaction",
            extra={
                "user_id": user_id,
                "interaction_type": interaction_type.value,
                "session_id": session_id,
            },
        )
        
        try:
            # Analyze using interaction-specific logic
            analysis_result = await self._analyze_universal_interaction(
                memory_profile, interaction_type, interaction_data, context or {}
            )
            logger.info(
                "LLM analysis complete",
                extra={
                    "user_id": user_id,
                    "interaction_type": interaction_type.value,
                    "should_update_memory": analysis_result.get("should_update_memory", False),
                    "proposed_notes": len(analysis_result.get("new_notes", []) or []),
                },
            )
            
            # Update memory if analysis indicates we should
            if analysis_result.get("should_update_memory", False):
                # Check for duplicates before adding
                filtered_notes = await self.consolidator.check_for_duplicates_before_adding(
                    memory_profile, analysis_result["new_notes"]
                )
                logger.info(
                    "Deduplication results",
                    extra={
                        "user_id": user_id,
                        "interaction_type": interaction_type.value,
                        "proposed_notes": len(analysis_result.get("new_notes", []) or []),
                        "kept_notes": len(filtered_notes or []),
                    },
                )
                
                notes_added = []
                if filtered_notes:
                    self.memory_service.add_notes(memory_profile, filtered_notes)
                    notes_added = filtered_notes
                    
                    # Check if consolidation should be triggered
                    if await self.consolidator.should_trigger_consolidation(memory_profile):
                        logger.info("Triggering memory consolidation", extra={"user_id": user_id})
                        consolidation_result = await self.consolidator.consolidate_user_memory(
                            memory_profile, "automatic"
                        )
                        logger.debug("Consolidation result", extra={"user_id": user_id, "result": consolidation_result})
                else:
                    logger.info("All new notes were duplicates, none added", extra={"user_id": user_id})
                
                # Update the memory event with results
                self.memory_service.update_event_status(
                    memory_event,
                    status="processed",
                    reasoning=analysis_result["reasoning"],
                    notes_added=notes_added,
                )
            else:
                logger.info(
                    "No memory update needed",
                    extra={
                        "user_id": user_id,
                        "interaction_type": interaction_type.value,
                        "reasoning": analysis_result.get("reasoning", ""),
                    },
                )
                self.memory_service.update_event_status(
                    memory_event,
                    status="processed",
                    reasoning=analysis_result.get("reasoning", "No memory update needed"),
                    notes_added=[],
                )
            
            # Commit the full interaction atomically
            self.memory_service.commit()
            logger.info(
                "Memory event processed",
                extra={
                    "user_id": user_id,
                    "event_id": memory_event.id,
                    "interaction_type": interaction_type.value,
                    "notes_added": len(analysis_result.get("new_notes", []) or []),
                },
            )
            
            return {
                "memory_updated": analysis_result.get("should_update_memory", False),
                "reasoning": analysis_result.get("reasoning", ""),
                "notes_added": filtered_notes if analysis_result.get("should_update_memory", False) else [],
                "event_id": memory_event.id,
                "interaction_type": interaction_type.value
            }
            
        except Exception as e:
            # Handle errors gracefully
            self.memory_service.rollback()
            # Recreate a failure event to ensure the error is logged cleanly
            failure_event = self.memory_service.create_event(
                profile_id=memory_profile.id,
                event_type=interaction_type.value,
                event_data=event_data,
                trigger_context=trigger_context,
                processing_status="failed",
            )
            self.memory_service.update_event_status(
                failure_event,
                status="failed",
                reasoning=f"Error during analysis: {str(e)}",
                notes_added=[],
            )
            self.memory_service.commit()
            
            return {
                "memory_updated": False,
                "error": str(e),
                "event_id": failure_event.id,
                "interaction_type": interaction_type.value
            }
    
    async def _analyze_universal_interaction(self, memory_profile: UserMemoryProfile,
                                           interaction_type: InteractionType,
                                           interaction_data: Dict[str, Any],
                                           context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze any type of interaction using specialized prompts"""
        
        # Get interaction-specific prompt
        prompt_template = self._get_prompt_for_interaction_type(interaction_type)
        
        # Prepare existing memory summary for context
        existing_memory = self._format_memory_for_context(memory_profile)
        
        # Format interaction data for analysis
        formatted_interaction = self._format_interaction_data(interaction_type, interaction_data)
        
        # Create prompt input
        prompt_input = {
            "existing_memory_summary": existing_memory,
            "interaction_type": interaction_type.value,
            "interaction_data": formatted_interaction,
            "context": json.dumps(context, indent=2)
        }
        
        # Get LLM analysis
        response = await self.llm.ainvoke(
            prompt_template.format_messages(**prompt_input)
        )
        
        # Parse the JSON response
        try:
            response_content = response.content
            
            # Debug: Print the raw response
            logger.debug("Raw LLM response", extra={"snippet": response_content[:200]})
            
            # Try to extract JSON from response if it contains other text
            if '```json' in response_content:
                start = response_content.find('```json') + 7
                end = response_content.find('```', start)
                response_content = response_content[start:end].strip()
            elif '{' in response_content:
                start = response_content.find('{')
                end = response_content.rfind('}') + 1
                response_content = response_content[start:end]
            
            analysis_result = json.loads(response_content)
            return analysis_result
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing failed", extra={"error": str(e)})
            logger.debug("Full response content", extra={"content": response.content[:500]})
            # Fallback if JSON parsing fails
            return {
                "should_update_memory": False,
                "reasoning": f"Failed to parse LLM response: {str(e)}",
                "new_notes": []
            }
    
    def _get_prompt_for_interaction_type(self, interaction_type: InteractionType):
        """Get the appropriate prompt template for the interaction type"""
        
        # For now, we'll use a universal prompt, but this can be specialized later
        return self._create_universal_prompt()
    
    def _create_universal_prompt(self):
        """Create a universal prompt that can handle any interaction type"""
        
        from langchain.prompts import ChatPromptTemplate
        
        system_prompt = """You are an intelligent memory agent for a Twelver Shia Islamic education platform. Your role is to analyze ANY type of user interaction and decide what important information to remember about the user for future personalization.

CORE RESPONSIBILITIES:
1. Analyze the user interaction (regardless of type) and extract meaningful insights
2. Create precise, informative notes that will help personalize their learning experience  
3. Ensure all suggestions and observations align with Twelver Shia Islamic perspective
4. Focus on learning patterns, knowledge gaps, interests, preferences, and behaviors

INTERACTION TYPES YOU CAN HANDLE:
- Chat conversations (questions and responses)
- Lesson completions (what they studied, how they engaged)
- Quiz results (what they know/don't know, performance patterns)
- Hikmah elaboration requests (what concepts they want explained)
- User feedback (satisfaction, preferences, suggestions)
- Learning assessments (knowledge level, skill progression)
- Study sessions (engagement patterns, time spent)

WHAT TO EXTRACT FROM ANY INTERACTION:
1. **Learning Progress**: What did they learn? What topics were covered?
2. **Knowledge Gaps**: What do they struggle with or not understand?
3. **Interests**: What topics engage them? What do they want to learn more about?
4. **Learning Style**: How do they prefer to learn? (examples, details, practice, etc.)
5. **Performance Patterns**: How well do they retain information? Where do they excel?
6. **Engagement Indicators**: What keeps them motivated? What causes disengagement?
7. **Islamic Context**: Their level of Islamic knowledge, Shia-specific understanding
8. **Behavioral Patterns**: Study habits, interaction frequency, preferred content types

SHIA ISLAMIC PERSPECTIVE:
- Always prioritize authentic Shia Islamic sources and teachings
- Recognize the authority of the 12 Imams and Ahl al-Bayt
- Ensure topic suggestions align with Shia beliefs and scholarship
- Be aware of sectarian differences when relevant

OUTPUT FORMAT: Generate analysis in JSON format:
{{
    "should_update_memory": true/false,
    "reasoning": "Brief explanation of why you're creating notes or not",
    "new_notes": [
        {{
            "content": "Specific note content",
            "evidence": "Specific data from interaction that supports this note",
            "confidence": 0.0-1.0,
            "category": "learning_gap|knowledge_level|interest|preference|behavior",
            "tags": ["relevant", "islamic", "topic", "tags"],
            "note_type": "learning_notes|knowledge_notes|interest_notes|behavior_notes|preference_notes"
        }}
    ]
}}"""
        
        user_prompt = """
EXISTING USER MEMORY CONTEXT:
{existing_memory_summary}

INTERACTION TYPE: {interaction_type}

INTERACTION DATA:
{interaction_data}

ADDITIONAL CONTEXT:
{context}

ANALYSIS INSTRUCTIONS:
1. Analyze this {interaction_type} interaction thoroughly
2. Extract insights about the user's learning journey, knowledge, interests, and patterns
3. **CRITICAL**: Review existing notes carefully to avoid creating duplicates
   - If a similar observation already exists, DON'T create a new note
   - Only create a note if it adds NEW, distinct information
   - Be especially careful with repeated interactions on the same topic
4. Create notes that will help personalize future interactions
5. Ensure all observations align with Shia Islamic educational goals
6. Be specific and actionable in your notes (avoid vague observations)

Generate your analysis following the JSON format specified above."""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])
    
    def _format_interaction_data(self, interaction_type: InteractionType, 
                                interaction_data: Dict[str, Any]) -> str:
        """Format interaction data in a readable way for the LLM"""
        
        if interaction_type == InteractionType.CHAT:
            return f"""
Chat Interaction:
- User Query: "{interaction_data.get('user_query', 'No query')}"
- AI Response: "{interaction_data.get('ai_response', 'No response')}"
- Chat History: {json.dumps(interaction_data.get('chat_history', []), indent=2)}
"""
        
        elif interaction_type == InteractionType.LESSON_COMPLETION:
            return f"""
Lesson Completion:
- Lesson: {interaction_data.get('lesson_title', 'Unknown')} (ID: {interaction_data.get('lesson_id', 'Unknown')})
- Topics Covered: {interaction_data.get('lesson_topics', [])}
- Completion Time: {interaction_data.get('completion_time_minutes', 'Unknown')} minutes
- Engagement Score: {interaction_data.get('user_engagement_score', 'Unknown')}
- Lesson Summary: {interaction_data.get('lesson_summary', 'No summary')}
"""
        
        elif interaction_type == InteractionType.QUIZ_RESULT:
            return f"""
Quiz Result:
- Quiz: {interaction_data.get('quiz_id', 'Unknown')} (Lesson: {interaction_data.get('lesson_id', 'Unknown')})
- Score: {interaction_data.get('score', 0)} ({interaction_data.get('correct_answers', 0)}/{interaction_data.get('total_questions', 0)} correct)
- Topics Tested: {interaction_data.get('topics_tested', [])}
- Topics Struggled With: {interaction_data.get('incorrect_topics', [])}
- Time Taken: {interaction_data.get('time_taken_minutes', 'Unknown')} minutes
"""
        
        elif interaction_type == InteractionType.HIKMAH_ELABORATION:
            # For hikmah elaboration, the selected_text is the key signal
            # Don't include full context_text as it's too verbose (800+ chars)
            return f"""
Hikmah Elaboration Request:
- User Selected This for Elaboration: "{interaction_data.get('selected_text', 'No text')}"
- From Lesson: "{interaction_data.get('lesson_name', 'Unknown')}"
- In Hikmah Tree: "{interaction_data.get('hikmah_tree_name', 'Unknown')}"

ANALYSIS GUIDELINES FOR ELABORATION REQUESTS:
1. The selected text is what the user wants to understand better
2. If they request elaboration on the SAME concept again, DON'T create duplicate notes
3. Only create a new note if this reveals NEW information about their learning:
   - First time asking about this concept? → Note the interest/learning gap
   - Repeated requests on same concept? → Skip (already noted)
   - Different aspect of same topic? → Consider if it's truly different
4. Focus on WHAT they're struggling with, not just that they asked
5. Be specific: Instead of "User interested in X", say "User needs clarification on X's role in Y"
"""
        
        else:
            # Generic formatting for any other interaction type
            return json.dumps(interaction_data, indent=2)
    
    # Reuse existing methods from MemoryAgent
    async def _get_or_create_memory_profile(self, user_id: str) -> UserMemoryProfile:
        """Get existing memory profile or create a new one"""
        return self.memory_service.get_or_create_profile(user_id)
    
    def _format_memory_for_context(self, memory_profile: UserMemoryProfile) -> str:
        """Format existing memory into a concise summary for LLM context"""
        
        memory_summary = []
        
        # Count notes by type
        note_counts = {
            "learning": len(memory_profile.learning_notes or []),
            "knowledge": len(memory_profile.knowledge_notes or []),
            "interests": len(memory_profile.interest_notes or []),
            "behavior": len(memory_profile.behavior_notes or []),
            "preferences": len(memory_profile.preference_notes or [])
        }
        
        memory_summary.append(f"Total interactions: {memory_profile.total_interactions}")
        memory_summary.append(f"Note counts: {note_counts}")
        
        # Add recent notes from each category (max 3 per category to control context size)
        for note_type, notes in [
            ("Learning", memory_profile.learning_notes or []),
            ("Knowledge", memory_profile.knowledge_notes or []),
            ("Interests", memory_profile.interest_notes or []),
            ("Behavior", memory_profile.behavior_notes or []),
            ("Preferences", memory_profile.preference_notes or [])
        ]:
            if notes:
                recent_notes = sorted(notes, key=lambda x: x.get("created_at", ""), reverse=True)[:3]
                memory_summary.append(f"\nRecent {note_type} Notes:")
                for note in recent_notes:
                    memory_summary.append(f"- {note.get('content', 'No content')}")
        
        return "\n".join(memory_summary) if memory_summary else "No existing memory for this user."
    
    async def _update_user_memory(self, memory_profile: UserMemoryProfile, new_notes: List[Dict[str, Any]]) -> None:
        """Backwards-compatible wrapper to add notes via the memory service"""
        self.memory_service.add_notes(memory_profile, new_notes)
    
    # Convenience methods for specific interaction types
    async def analyze_chat(self, user_id: str, user_query: str, ai_response: str = None,
                          chat_history: List[Dict[str, str]] = None, session_id: str = None) -> Dict[str, Any]:
        """Convenience method for chat interactions"""
        return await self.analyze_interaction(
            user_id=user_id,
            interaction_type=InteractionType.CHAT,
            interaction_data={
                "user_query": user_query,
                "ai_response": ai_response,
                "chat_history": chat_history or []
            },
            session_id=session_id
        )
    
    async def analyze_lesson_completion(self, user_id: str, lesson_id: str, lesson_title: str,
                                      lesson_topics: List[str], completion_time_minutes: int,
                                      engagement_score: float = None, lesson_summary: str = None) -> Dict[str, Any]:
        """Convenience method for lesson completions"""
        return await self.analyze_interaction(
            user_id=user_id,
            interaction_type=InteractionType.LESSON_COMPLETION,
            interaction_data={
                "lesson_id": lesson_id,
                "lesson_title": lesson_title,
                "lesson_topics": lesson_topics,
                "completion_time_minutes": completion_time_minutes,
                "user_engagement_score": engagement_score,
                "lesson_summary": lesson_summary
            }
        )
    
    async def analyze_quiz_result(self, user_id: str, quiz_id: str, score: float,
                                total_questions: int, correct_answers: int,
                                topics_tested: List[str], incorrect_topics: List[str] = None,
                                time_taken_minutes: int = None) -> Dict[str, Any]:
        """Convenience method for quiz results"""
        return await self.analyze_interaction(
            user_id=user_id,
            interaction_type=InteractionType.QUIZ_RESULT,
            interaction_data={
                "quiz_id": quiz_id,
                "score": score,
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "topics_tested": topics_tested,
                "incorrect_topics": incorrect_topics or [],
                "time_taken_minutes": time_taken_minutes
            }
        )
    
    async def analyze_hikmah_elaboration(self, user_id: str, selected_text: str,
                                       hikmah_tree_name: str, lesson_name: str,
                                       context_text: str = None) -> Dict[str, Any]:
        """Convenience method for hikmah elaboration requests"""
        return await self.analyze_interaction(
            user_id=user_id,
            interaction_type=InteractionType.HIKMAH_ELABORATION,
            interaction_data={
                "selected_text": selected_text,
                "hikmah_tree_name": hikmah_tree_name,
                "lesson_name": lesson_name,
                "context_text": context_text
            }
        )
