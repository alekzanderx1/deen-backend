from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import json
import uuid

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.models.user_memory_models import UserMemoryProfile, MemoryEvent
from agents.prompts.memory_prompts import chat_memory_analysis_prompt
from core.chat_models import get_generator_model
from .memory_consolidator import MemoryConsolidator

class MemoryAgent:
    """
    Specialized agent for analyzing user interactions and updating long-term memory.
    
    This agent focuses on a single responsibility: deciding what to remember about users
    based on their interactions, particularly chat conversations.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_generator_model()
        self.consolidator = MemoryConsolidator(db)
    
    async def analyze_chat_interaction(self, user_id: str, session_id: str,
                                     user_query: str, ai_response: str = None,
                                     chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Main method to analyze a chat interaction and update user memory if needed.
        
        Args:
            user_id: Unique user identifier
            session_id: Chat session ID  
            user_query: What the user asked
            ai_response: The AI's response to the user (if any)
            chat_history: Recent chat history for context (list of {"role": "user/assistant", "content": "..."})
        
        Returns:
            Dict with analysis results and any memory updates made
        """
        
        # Get or create user memory profile
        memory_profile = await self._get_or_create_memory_profile(user_id)
        
        # Create memory event record
        event_data = {
            "user_query": user_query,
            "ai_response": ai_response,
            "chat_history": chat_history or [],
            "session_id": session_id
        }
        
        memory_event = MemoryEvent(
            user_memory_profile_id=memory_profile.id,
            event_type="chat_interaction",
            event_data=event_data,
            trigger_context={"method": "chat_analysis", "agent": "MemoryAgent"}
        )
        
        try:
            # Analyze the interaction using LLM
            analysis_result = await self._analyze_interaction_with_llm(
                memory_profile, user_query, ai_response, chat_history or []
            )
            
            # Update memory if analysis indicates we should
            if analysis_result.get("should_update_memory", False):
                # Check for duplicates before adding
                filtered_notes = await self.consolidator.check_for_duplicates_before_adding(
                    memory_profile, analysis_result["new_notes"]
                )
                
                if filtered_notes:
                    await self._update_user_memory(memory_profile, filtered_notes)
                    
                    # Check if consolidation should be triggered
                    if await self.consolidator.should_trigger_consolidation(memory_profile):
                        print("🧠 Triggering memory consolidation...")
                        consolidation_result = await self.consolidator.consolidate_user_memory(
                            memory_profile, "automatic"
                        )
                        print(f"Consolidation result: {consolidation_result}")
                else:
                    print("🔄 All new notes were duplicates, none added")
                
                # Update the memory event with results
                memory_event.notes_added = analysis_result["new_notes"]
                memory_event.processing_reasoning = analysis_result["reasoning"]
                memory_event.processing_status = "processed"
                memory_event.processed_at = datetime.utcnow()
            else:
                memory_event.processing_reasoning = analysis_result.get("reasoning", "No memory update needed")
                memory_event.processing_status = "processed"
                memory_event.processed_at = datetime.utcnow()
            
            # Save the memory event
            self.db.add(memory_event)
            self.db.commit()
            
            return {
                "memory_updated": analysis_result.get("should_update_memory", False),
                "reasoning": analysis_result.get("reasoning", ""),
                "notes_added": analysis_result.get("new_notes", []),
                "event_id": memory_event.id
            }
            
        except Exception as e:
            # Handle errors gracefully
            memory_event.processing_status = "failed"
            memory_event.processing_reasoning = f"Error during analysis: {str(e)}"
            memory_event.processed_at = datetime.utcnow()
            self.db.add(memory_event)
            self.db.commit()
            
            return {
                "memory_updated": False,
                "error": str(e),
                "event_id": memory_event.id
            }
    
    async def _get_or_create_memory_profile(self, user_id: str) -> UserMemoryProfile:
        """Get existing memory profile or create a new one"""
        
        profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        
        if not profile:
            profile = UserMemoryProfile(
                user_id=user_id,
                learning_notes=[],
                interest_notes=[],
                knowledge_notes=[],
                behavior_notes=[],
                preference_notes=[]
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        
        return profile
    
    async def _analyze_interaction_with_llm(self, memory_profile: UserMemoryProfile,
                                           user_query: str, ai_response: str,
                                           chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Use LLM to analyze the interaction and decide what to remember"""
        
        # Prepare existing memory summary for context
        existing_memory = self._format_memory_for_context(memory_profile)
        
        # Format chat history for context
        chat_history_text = self._format_chat_history(chat_history)
        
        # Format the prompt
        prompt_input = {
            "existing_memory_summary": existing_memory,
            "user_query": user_query,
            "ai_response": ai_response or "No response generated",
            "chat_history": chat_history_text,
            "session_context": "Chat interaction analysis"
        }
        
        # Get LLM analysis
        response = await self.llm.ainvoke(
            chat_memory_analysis_prompt.format_messages(**prompt_input)
        )
        
        # Parse the JSON response
        try:
            analysis_result = json.loads(response.content)
            return analysis_result
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "should_update_memory": False,
                "reasoning": "Failed to parse LLM response",
                "new_notes": []
            }
    
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
        """Update the user's memory profile with new notes"""
        
        # Add timestamps and IDs to new notes
        for note in new_notes:
            note["id"] = str(uuid.uuid4())
            note["created_at"] = datetime.utcnow().isoformat()
        
        # Add notes to appropriate categories
        for note in new_notes:
            note_type = note.get("note_type", "learning_notes")
            
            if note_type == "learning_notes":
                memory_profile.learning_notes = (memory_profile.learning_notes or []) + [note]
            elif note_type == "knowledge_notes":
                memory_profile.knowledge_notes = (memory_profile.knowledge_notes or []) + [note]
            elif note_type == "interest_notes":
                memory_profile.interest_notes = (memory_profile.interest_notes or []) + [note]
            elif note_type == "behavior_notes":
                memory_profile.behavior_notes = (memory_profile.behavior_notes or []) + [note]
            elif note_type == "preference_notes":
                memory_profile.preference_notes = (memory_profile.preference_notes or []) + [note]
        
        # Update metadata
        memory_profile.total_interactions += 1
        memory_profile.last_significant_update = datetime.utcnow()
        memory_profile.updated_at = datetime.utcnow()
        
        # Check if we need consolidation (simple rule for now)
        total_notes = sum([
            len(memory_profile.learning_notes or []),
            len(memory_profile.knowledge_notes or []),
            len(memory_profile.interest_notes or []),
            len(memory_profile.behavior_notes or []),
            len(memory_profile.preference_notes or [])
        ])
        
        if total_notes > 50:  # Arbitrary threshold
            # Flag for consolidation (we'll implement this later)
            memory_profile.memory_version += 1
        
        self.db.commit()
    
    async def get_user_memory_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of user's memory for other agents to use"""
        
        memory_profile = await self._get_or_create_memory_profile(user_id)
        
        return {
            "user_id": user_id,
            "total_interactions": memory_profile.total_interactions,
            "last_updated": memory_profile.updated_at.isoformat() if memory_profile.updated_at else None,
            "memory_counts": {
                "learning": len(memory_profile.learning_notes or []),
                "knowledge": len(memory_profile.knowledge_notes or []),
                "interests": len(memory_profile.interest_notes or []),
                "behavior": len(memory_profile.behavior_notes or []),
                "preferences": len(memory_profile.preference_notes or [])
            },
            "recent_notes": {
                "learning": (memory_profile.learning_notes or [])[-3:],
                "knowledge": (memory_profile.knowledge_notes or [])[-3:],
                "interests": (memory_profile.interest_notes or [])[-3:],
                "behavior": (memory_profile.behavior_notes or [])[-3:],
                "preferences": (memory_profile.preference_notes or [])[-3:]
            }
        }
    
    async def get_user_interests(self, user_id: str) -> List[str]:
        """Get list of user's interests for content recommendation"""
        
        memory_profile = await self._get_or_create_memory_profile(user_id)
        
        interests = []
        for note in (memory_profile.interest_notes or []):
            if note.get("tags"):
                interests.extend(note["tags"])
        
        # Return unique interests
        return list(set(interests))
    
    async def get_knowledge_gaps(self, user_id: str) -> List[str]:
        """Get list of user's knowledge gaps for targeted learning"""
        
        memory_profile = await self._get_or_create_memory_profile(user_id)
        
        gaps = []
        for note in (memory_profile.knowledge_notes or []):
            if note.get("category") == "learning_gap" and note.get("tags"):
                gaps.extend(note["tags"])
        
        return list(set(gaps))
    
    def _format_chat_history(self, chat_history: List[Dict[str, str]]) -> str:
        """Format chat history for LLM context"""
        
        if not chat_history:
            return "No previous chat history available."
        
        formatted_history = []
        for message in chat_history[-5:]:  # Only include last 5 messages for context
            role = message.get("role", "unknown")
            content = message.get("content", "")
            formatted_history.append(f"{role.title()}: {content}")
        
        return "\n".join(formatted_history)
    
    async def manually_consolidate_memory(self, user_id: str) -> Dict[str, Any]:
        """Manually trigger memory consolidation for a user"""
        
        memory_profile = await self._get_or_create_memory_profile(user_id)
        return await self.consolidator.consolidate_user_memory(memory_profile, "manual")
    
    async def get_consolidation_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get consolidation analytics for a user"""
        
        return await self.consolidator.get_consolidation_analytics(user_id)
