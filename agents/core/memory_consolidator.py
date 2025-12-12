import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import numpy as np
import os
import sys
import threading

# Set tokenizers parallelism before importing sentence_transformers
# This prevents fork warnings when running in multi-threaded/multi-process environments
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from sentence_transformers import SentenceTransformer

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.models.user_memory_models import UserMemoryProfile
from agents.prompts.memory_prompts import memory_consolidation_prompt
from core.chat_models import get_generator_model
from services.consolidation_service import ConsolidationService
from core.logging_config import get_memory_logger

logger = get_memory_logger(level=logging.DEBUG)

class MemoryConsolidator:
    """
    Handles smart consolidation of user memory notes to prevent duplicates,
    merge similar observations, and create higher-level insights.
    """
    # Shared, thread-safe singleton embedder per process
    _shared_embedder = None
    _embedder_lock = threading.Lock()
    
    def __init__(self, consolidation_service: ConsolidationService):
        self.consolidation_service = consolidation_service
        self.llm = get_generator_model()
        # Use a lightweight sentence transformer for semantic similarity
        if MemoryConsolidator._shared_embedder is None:
            with MemoryConsolidator._embedder_lock:
                if MemoryConsolidator._shared_embedder is None:
                    MemoryConsolidator._shared_embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedder = MemoryConsolidator._shared_embedder
        
        # Consolidation thresholds
        self.SIMILARITY_THRESHOLD = 0.6  # How similar notes need to be to merge (lowered to catch more duplicates)
        self.MAX_NOTES_PER_CATEGORY = 15  # When to trigger consolidation
        self.MIN_CONFIDENCE_TO_KEEP = 0.3  # Remove notes below this confidence
    
    async def check_for_duplicates_before_adding(self, memory_profile: UserMemoryProfile, 
                                                new_notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Check if new notes are too similar to existing ones before adding them.
        Returns filtered list of notes that should actually be added.
        """
        
        filtered_notes = []
        
        for note in new_notes:
            note_content = note.get("content", "")
            note_type = note.get("note_type", "learning_notes")
            
            # Get existing notes of the same type
            existing_notes = getattr(memory_profile, note_type, []) or []
            
            # Check for semantic similarity with existing notes
            is_duplicate = await self._is_note_duplicate(note_content, existing_notes)
            
            if not is_duplicate:
                filtered_notes.append(note)
            else:
                logger.info("Skipping duplicate note", extra={"note_snippet": note_content[:50]})
        
        return filtered_notes
    
    async def _is_note_duplicate(self, new_note_content: str, existing_notes: List[Dict[str, Any]]) -> bool:
        """Check if a new note is too similar to existing notes"""
        
        if not existing_notes:
            return False
        
        # Get embeddings for the new note
        new_embedding = self.embedder.encode([new_note_content], show_progress_bar=False)
        
        # Get embeddings for existing notes
        existing_contents = [note.get("content", "") for note in existing_notes]
        if not existing_contents:
            return False
        
        existing_embeddings = self.embedder.encode(existing_contents, show_progress_bar=False)
        
        # Calculate cosine similarities
        similarities = np.dot(existing_embeddings, new_embedding.T).flatten()
        norms = np.linalg.norm(existing_embeddings, axis=1) * np.linalg.norm(new_embedding)
        cosine_similarities = similarities / norms
        
        # Check if any existing note is too similar
        max_similarity = np.max(cosine_similarities)
        return max_similarity > self.SIMILARITY_THRESHOLD
    
    async def should_trigger_consolidation(self, memory_profile: UserMemoryProfile) -> bool:
        """Determine if consolidation should be triggered"""
        
        # Count total notes
        total_notes = sum([
            len(memory_profile.learning_notes or []),
            len(memory_profile.knowledge_notes or []),
            len(memory_profile.interest_notes or []),
            len(memory_profile.behavior_notes or []),
            len(memory_profile.preference_notes or [])
        ])
        
        # Trigger consolidation if too many notes
        if total_notes > 50:
            return True
        
        # Check if any category has too many notes
        categories = {
            "learning_notes": memory_profile.learning_notes or [],
            "knowledge_notes": memory_profile.knowledge_notes or [],
            "interest_notes": memory_profile.interest_notes or [],
            "behavior_notes": memory_profile.behavior_notes or [],
            "preference_notes": memory_profile.preference_notes or []
        }
        
        for category, notes in categories.items():
            if len(notes) > self.MAX_NOTES_PER_CATEGORY:
                return True
        
        # Check if consolidation hasn't happened in a while
        last_consolidation = self.consolidation_service.get_last_consolidation(memory_profile.id)
        
        if last_consolidation:
            days_since_last = (datetime.utcnow() - last_consolidation.created_at).days
            if days_since_last > 7 and total_notes > 20:  # Weekly consolidation if active user
                return True
        else:
            # First consolidation if user has enough notes
            if total_notes > 20:
                return True
        
        return False
    
    async def consolidate_user_memory(self, memory_profile: UserMemoryProfile, 
                                    consolidation_type: str = "automatic") -> Dict[str, Any]:
        """
        Perform smart consolidation of user memory using LLM analysis
        """
        
        logger.info("Starting memory consolidation", extra={"user_id": memory_profile.user_id})
        
        # Prepare memory data for LLM analysis
        memory_data = self._prepare_memory_for_consolidation(memory_profile)
        
        # Count notes before consolidation
        notes_before = self._count_total_notes(memory_profile)
        
        try:
            # Use LLM to analyze and consolidate memory
            consolidation_result = await self._llm_consolidate_memory(memory_data, consolidation_type)
            
            # Apply the consolidation
            await self._apply_consolidation_result(memory_profile, consolidation_result)
            
            # Count notes after consolidation
            notes_after = self._count_total_notes(memory_profile)
            
            # Log the consolidation
            consolidation_log = self.consolidation_service.log_consolidation(
                profile_id=memory_profile.id,
                consolidation_type=consolidation_type,
                notes_before_count=notes_before,
                notes_after_count=notes_after,
                consolidated_notes=consolidation_result.get("consolidated_notes", []),
                removed_notes=consolidation_result.get("removed_notes", []),
                new_summary_notes=consolidation_result.get("new_summary_notes", []),
                consolidation_reasoning=consolidation_result.get("reasoning", "")
            )
            
            logger.info(
                "Consolidation complete",
                extra={
                    "user_id": memory_profile.user_id,
                    "notes_before": notes_before,
                    "notes_after": notes_after,
                },
            )
            
            return {
                "success": True,
                "notes_before": notes_before,
                "notes_after": notes_after,
                "notes_removed": notes_before - notes_after,
                "consolidation_id": consolidation_log.id,
                "reasoning": consolidation_result.get("reasoning", "")
            }
            
        except Exception as e:
            logger.error("Error during consolidation", extra={"user_id": memory_profile.user_id, "error": str(e)})
            return {
                "success": False,
                "error": str(e)
            }
    
    def _prepare_memory_for_consolidation(self, memory_profile: UserMemoryProfile) -> Dict[str, Any]:
        """Prepare memory data in a format suitable for LLM analysis"""
        
        return {
            "user_id": memory_profile.user_id,
            "total_interactions": memory_profile.total_interactions,
            "memory_version": memory_profile.memory_version,
            "categories": {
                "learning_notes": memory_profile.learning_notes or [],
                "knowledge_notes": memory_profile.knowledge_notes or [],
                "interest_notes": memory_profile.interest_notes or [],
                "behavior_notes": memory_profile.behavior_notes or [],
                "preference_notes": memory_profile.preference_notes or []
            }
        }
    
    def _count_total_notes(self, memory_profile: UserMemoryProfile) -> int:
        """Count total notes across all categories"""
        return sum([
            len(memory_profile.learning_notes or []),
            len(memory_profile.knowledge_notes or []),
            len(memory_profile.interest_notes or []),
            len(memory_profile.behavior_notes or []),
            len(memory_profile.preference_notes or [])
        ])
    
    async def _llm_consolidate_memory(self, memory_data: Dict[str, Any], 
                                    consolidation_type: str) -> Dict[str, Any]:
        """Use LLM to analyze memory and create consolidation plan"""
        
        # Determine trigger reason
        total_notes = sum(len(notes) for notes in memory_data["categories"].values())
        note_counts = {cat: len(notes) for cat, notes in memory_data["categories"].items()}
        
        trigger_reason = f"Triggered by {consolidation_type} - Total notes: {total_notes}"
        
        # Format prompt
        prompt_input = {
            "memory_data": json.dumps(memory_data, indent=2),
            "trigger_reason": trigger_reason,
            "note_counts": note_counts
        }
        
        # Get LLM analysis
        response = await self.llm.ainvoke(
            memory_consolidation_prompt.format_messages(**prompt_input)
        )
        
        # Parse the response
        try:
            response_content = response.content
            
            # Try to extract JSON from response if it contains other text
            if '```json' in response_content:
                start = response_content.find('```json') + 7
                end = response_content.find('```', start)
                response_content = response_content[start:end].strip()
            elif '{' in response_content:
                start = response_content.find('{')
                end = response_content.rfind('}') + 1
                response_content = response_content[start:end]
            
            consolidation_result = json.loads(response_content)
            return consolidation_result
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing failed during consolidation", extra={"error": str(e)})
            logger.debug("Consolidation LLM raw response", extra={"content": response.content[:200]})
            # Fallback consolidation if JSON parsing fails
            return await self._fallback_consolidation(memory_data)
    
    async def _fallback_consolidation(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple rule-based consolidation if LLM fails"""
        
        logger.warning("LLM consolidation failed, using fallback rules")
        
        consolidated = {
            "consolidated_memory": memory_data["categories"],
            "consolidated_notes": [],
            "removed_notes": [],
            "new_summary_notes": [],
            "reasoning": "Fallback consolidation: Removed low-confidence notes and old duplicates"
        }
        
        # Simple rules: Remove notes with very low confidence or very old notes
        for category, notes in memory_data["categories"].items():
            if len(notes) > self.MAX_NOTES_PER_CATEGORY:
                # Sort by confidence and recency, keep top notes
                sorted_notes = sorted(notes, 
                                    key=lambda x: (x.get("confidence", 0), x.get("created_at", "")), 
                                    reverse=True)
                
                kept_notes = sorted_notes[:self.MAX_NOTES_PER_CATEGORY]
                removed_notes = sorted_notes[self.MAX_NOTES_PER_CATEGORY:]
                
                consolidated["consolidated_memory"][category] = kept_notes
                consolidated["removed_notes"].extend([note.get("id") for note in removed_notes])
        
        return consolidated
    
    async def _apply_consolidation_result(self, memory_profile: UserMemoryProfile, 
                                        consolidation_result: Dict[str, Any]) -> None:
        """Apply the consolidation result to the memory profile"""
        
        consolidated_memory = consolidation_result.get("consolidated_memory", {})
        
        self.consolidation_service.apply_consolidated_memory(memory_profile, consolidated_memory)
    
    async def find_similar_notes_in_category(self, notes: List[Dict[str, Any]], 
                                           similarity_threshold: float = 0.8) -> List[List[int]]:
        """
        Find groups of similar notes within a category using semantic similarity.
        Returns list of groups, where each group is a list of note indices.
        """
        
        if len(notes) < 2:
            return []
        
        # Get note contents
        contents = [note.get("content", "") for note in notes]
        
        # Generate embeddings
        embeddings = self.embedder.encode(contents)
        
        # Calculate similarity matrix
        similarity_matrix = np.dot(embeddings, embeddings.T)
        norms = np.linalg.norm(embeddings, axis=1)
        similarity_matrix = similarity_matrix / np.outer(norms, norms)
        
        # Find similar note groups
        similar_groups = []
        processed = set()
        
        for i in range(len(notes)):
            if i in processed:
                continue
            
            # Find notes similar to note i
            similar_indices = []
            for j in range(len(notes)):
                if i != j and similarity_matrix[i][j] > similarity_threshold:
                    similar_indices.append(j)
            
            if similar_indices:
                # Create group including the original note
                group = [i] + similar_indices
                similar_groups.append(group)
                processed.update(group)
        
        return similar_groups
    
    async def get_consolidation_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics about consolidation history for a user"""
        
        # Get user profile
        memory_profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        
        if not memory_profile:
            return {"error": "User not found"}
        
        # Get consolidation history
        consolidations = self.consolidation_service.list_recent_consolidations(memory_profile.id, limit=5)
        
        if not consolidations:
            return {
                "total_consolidations": 0,
                "current_note_count": self._count_total_notes(memory_profile),
                "needs_consolidation": await self.should_trigger_consolidation(memory_profile)
            }
        
        # Calculate analytics
        total_notes_removed = sum(c.notes_before_count - c.notes_after_count for c in consolidations)
        
        return {
            "total_consolidations": len(consolidations),
            "current_note_count": self._count_total_notes(memory_profile),
            "total_notes_removed": total_notes_removed,
            "last_consolidation": consolidations[0].created_at.isoformat(),
            "needs_consolidation": await self.should_trigger_consolidation(memory_profile),
            "consolidation_history": [
                {
                    "date": c.created_at.isoformat(),
                    "type": c.consolidation_type,
                    "notes_before": c.notes_before_count,
                    "notes_after": c.notes_after_count,
                    "notes_removed": c.notes_before_count - c.notes_after_count
                }
                for c in consolidations[:5]  # Last 5 consolidations
            ]
        }
