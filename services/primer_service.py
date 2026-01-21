"""
Service layer for personalized lesson primers generation and management.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging

from sqlalchemy.orm import Session

from core.chat_models import get_enhancer_model
from core.prompt_templates import primer_generation_prompt_template
from db.crud.personalized_primers import personalized_primer_crud
from db.utils.personalized_primers_utils import (
    is_primer_fresh,
    compute_inputs_hash,
    calculate_ttl_expiration,
    get_ttl_bucket
)
from db.schemas.personalized_primers import PersonalizedPrimerCreate, PersonalizedPrimerUpdate
from agents.models.user_memory_models import UserMemoryProfile

logger = logging.getLogger(__name__)


class PrimerService:
    """
    Service for generating and managing personalized lesson primers.

    Handles:
    - Fetching user signals from memory profiles
    - Assessing signal quality for personalization
    - Generating personalized bullets via LLM
    - Caching and freshness validation
    """

    def __init__(self, db: Session):
        self.db = db

    async def generate_personalized_primer(
        self,
        user_id: str,
        lesson_id: int,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point for primer generation.

        Returns:
            {
                "personalized_bullets": List[str],
                "generated_at": datetime | None,
                "from_cache": bool,
                "stale": bool,
                "personalized_available": bool
            }
        """
        try:
            # Check cache first (unless force_refresh)
            if not force_refresh:
                cached_result = self._get_cached_primer(user_id, lesson_id)
                if cached_result:
                    return cached_result

            # Generate new primer
            return await self._generate_new_primer(user_id, lesson_id)

        except Exception as e:
            logger.error(f"Primer generation failed | user_id={user_id} | lesson_id={lesson_id} | error={str(e)}")
            return self._fallback_response()

    def _get_cached_primer(
        self,
        user_id: str,
        lesson_id: int
    ) -> Optional[Dict[str, Any]]:
        """Check if a fresh cached primer exists"""
        from db.crud.lessons import lesson_crud

        # Get cached primer
        primer = personalized_primer_crud.get_by_user_and_lesson(
            self.db, user_id, lesson_id
        )

        if not primer:
            return None

        # Get lesson and user memory version
        lesson = lesson_crud.get(self.db, lesson_id)
        if not lesson:
            return None

        user_memory_version = self._get_memory_version(user_id)

        # Check freshness
        if is_primer_fresh(primer, lesson, user_memory_version):
            return {
                "personalized_bullets": primer.personalized_bullets,
                "generated_at": primer.generated_at,
                "from_cache": True,
                "stale": False,
                "personalized_available": True
            }

        return None

    async def _generate_new_primer(
        self,
        user_id: str,
        lesson_id: int
    ) -> Dict[str, Any]:
        """Generate a new personalized primer"""
        from db.crud.lessons import lesson_crud

        # Fetch lesson
        lesson = lesson_crud.get(self.db, lesson_id)
        if not lesson:
            logger.error(f"Lesson not found | lesson_id={lesson_id}")
            return self._fallback_response()

        # Fetch user signals
        user_signals = self._fetch_user_signals(user_id, lesson.tags or [])

        # Assess signal quality
        signal_quality = self._assess_signal_quality(user_signals)

        # Check if we have enough signals to personalize
        if signal_quality < 0.5:
            logger.info(
                f"Insufficient signals for personalization | user_id={user_id} | "
                f"lesson_id={lesson_id} | quality={signal_quality}"
            )
            return self._fallback_response()

        # Generate bullets with LLM
        personalized_bullets = await self._generate_bullets_with_llm(
            lesson=lesson,
            user_signals=user_signals
        )

        if not personalized_bullets or len(personalized_bullets) < 2:
            logger.warning(f"LLM generation failed or returned insufficient bullets")
            return self._fallback_response()

        # Cache the primer
        self._cache_primer(
            user_id=user_id,
            lesson_id=lesson_id,
            lesson=lesson,
            bullets=personalized_bullets,
            user_signals=user_signals
        )

        return {
            "personalized_bullets": personalized_bullets,
            "generated_at": datetime.utcnow(),
            "from_cache": False,
            "stale": False,
            "personalized_available": True
        }

    def _fetch_user_signals(
        self,
        user_id: str,
        lesson_tags: List[str]
    ) -> Dict[str, Any]:
        """Fetch relevant user memory notes and progress"""
        # Fetch user memory profile
        profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()

        if not profile:
            return {"available": False}

        # Filter notes by relevance to lesson tags
        relevant_learning_notes = self._filter_notes_by_tags(
            profile.learning_notes or [], lesson_tags
        )
        relevant_interest_notes = self._filter_notes_by_tags(
            profile.interest_notes or [], lesson_tags
        )
        relevant_knowledge_notes = self._filter_notes_by_tags(
            profile.knowledge_notes or [], lesson_tags
        )
        relevant_preference_notes = self._filter_notes_by_tags(
            profile.preference_notes or [], lesson_tags
        )

        return {
            "available": True,
            "learning_notes": relevant_learning_notes,
            "interest_notes": relevant_interest_notes,
            "knowledge_notes": relevant_knowledge_notes,
            "preference_notes": relevant_preference_notes,
            "memory_version": profile.last_significant_update,  # Use datetime field, not integer counter
            "total_interactions": profile.total_interactions
        }

    def _filter_notes_by_tags(
        self,
        notes: List[Dict],
        lesson_tags: List[str]
    ) -> List[Dict]:
        """Filter notes that have overlapping tags with the lesson"""
        if not notes or not lesson_tags:
            return []

        relevant = []
        for note in notes:
            note_tags = note.get("tags", [])
            # Check for tag overlap
            if any(tag in note_tags for tag in lesson_tags):
                relevant.append(note)

        return relevant

    def _assess_signal_quality(self, signals: Dict[str, Any]) -> float:
        """
        Determine if signals are strong enough for personalization.

        Returns quality score from 0.0 to 1.0.
        Threshold for personalization: 0.5
        """
        if not signals.get("available"):
            return 0.0

        score = 0.0

        # Check for relevant notes (max 0.6)
        total_notes = (
            len(signals.get("learning_notes", [])) +
            len(signals.get("interest_notes", [])) +
            len(signals.get("knowledge_notes", []))
        )

        if total_notes >= 3:
            score += 0.6
        elif total_notes >= 1:
            score += 0.3

        # Check interaction count (max 0.2)
        interactions = signals.get("total_interactions", 0)
        if interactions >= 10:
            score += 0.2
        elif interactions >= 5:
            score += 0.1

        # Check note recency and confidence (max 0.2)
        has_high_confidence = any(
            note.get("confidence", 0) >= 0.7
            for note in (
                signals.get("learning_notes", []) +
                signals.get("interest_notes", []) +
                signals.get("knowledge_notes", [])
            )
        )
        if has_high_confidence:
            score += 0.2

        return min(score, 1.0)

    async def _generate_bullets_with_llm(
        self,
        lesson: Any,
        user_signals: Dict[str, Any]
    ) -> List[str]:
        """Call LLM to generate personalized bullets"""

        # Format baseline bullets
        baseline_bullets = "\n".join([
            f"• {bullet}" for bullet in (lesson.baseline_primer_bullets or [])
        ])

        # Format user notes
        def format_notes(notes: List[Dict]) -> str:
            if not notes:
                return "None available"
            return "\n".join([
                f"- {note.get('content', '')} (confidence: {note.get('confidence', 0):.2f})"
                for note in notes[:5]  # Limit to top 5
            ])

        # Prepare prompt inputs
        prompt_inputs = {
            "lesson_title": lesson.title,
            "lesson_summary": lesson.summary or "No summary available",
            "lesson_tags": ", ".join(lesson.tags or []),
            "baseline_bullets": baseline_bullets or "No baseline bullets available",
            "user_learning_notes": format_notes(user_signals.get("learning_notes", [])),
            "user_interest_notes": format_notes(user_signals.get("interest_notes", [])),
            "user_knowledge_notes": format_notes(user_signals.get("knowledge_notes", [])),
            "user_preference_notes": format_notes(user_signals.get("preference_notes", [])),
            "total_interactions": user_signals.get("total_interactions", 0)
        }

        # Generate with LLM
        formatted_prompt = primer_generation_prompt_template.invoke(prompt_inputs)
        model = get_enhancer_model()
        response = await model.ainvoke(formatted_prompt)

        # Parse response
        bullets = self._parse_llm_response(response.content)

        return bullets

    def _parse_llm_response(self, response_content: str) -> List[str]:
        """Parse LLM response to extract bullets"""
        try:
            # Try to extract JSON from response
            # Handle markdown code blocks
            content = response_content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            # Parse JSON
            data = json.loads(content)
            bullets = data.get("personalized_bullets", [])

            # Validate bullets
            if not isinstance(bullets, list):
                logger.error("Bullets is not a list")
                return []

            # Filter valid bullets (non-empty strings)
            valid_bullets = [
                bullet.strip() for bullet in bullets
                if isinstance(bullet, str) and bullet.strip()
            ]

            return valid_bullets[:3]  # Max 3 bullets

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return []

    def _cache_primer(
        self,
        user_id: str,
        lesson_id: int,
        lesson: Any,
        bullets: List[str],
        user_signals: Dict[str, Any]
    ) -> None:
        """Store generated primer in database"""
        now = datetime.utcnow()

        # Compute inputs hash
        note_ids = [
            note.get("id", "") for note in (
                user_signals.get("learning_notes", []) +
                user_signals.get("interest_notes", []) +
                user_signals.get("knowledge_notes", [])
            )
        ]

        inputs_hash = compute_inputs_hash(
            lesson_summary=lesson.summary or "",
            lesson_tags=lesson.tags or [],
            note_ids=note_ids,
            ttl_bucket=get_ttl_bucket(now)
        )

        # Calculate TTL expiration
        ttl_expires_at = calculate_ttl_expiration(now, ttl_days=5)

        # Check if primer already exists
        existing_primer = personalized_primer_crud.get_by_user_and_lesson(
            self.db, user_id, lesson_id
        )

        if existing_primer:
            # Update existing primer
            primer_update = PersonalizedPrimerUpdate(
                personalized_bullets=bullets,
                generated_at=now,
                inputs_hash=inputs_hash,
                lesson_version=lesson.updated_at or now,
                memory_version=user_signals.get("memory_version", now),
                ttl_expires_at=ttl_expires_at,
                stale=False
            )
            personalized_primer_crud.update(self.db, existing_primer, primer_update)
        else:
            # Create new primer
            primer_create = PersonalizedPrimerCreate(
                user_id=user_id,
                lesson_id=lesson_id,
                personalized_bullets=bullets,
                generated_at=now,
                inputs_hash=inputs_hash,
                lesson_version=lesson.updated_at or now,
                memory_version=user_signals.get("memory_version", now),
                ttl_expires_at=ttl_expires_at,
                stale=False
            )
            personalized_primer_crud.create(self.db, primer_create)

    def _get_memory_version(self, user_id: str) -> Optional[datetime]:
        """Get user's memory version timestamp"""
        profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        # Use last_significant_update as the memory version timestamp
        # (memory_version field is an Integer counter, not a timestamp)
        return profile.last_significant_update if profile else None

    def _fallback_response(self) -> Dict[str, Any]:
        """Return fallback response when personalization is not available"""
        return {
            "personalized_bullets": [],
            "generated_at": None,
            "from_cache": False,
            "stale": False,
            "personalized_available": False
        }
