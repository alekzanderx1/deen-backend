#!/usr/bin/env python3
"""
Test script for Universal Memory Agent
Demonstrates handling of multiple interaction types
"""

import sys
import os
import asyncio
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agents.core.universal_memory_agent import UniversalMemoryAgent, InteractionType
from agents.models.db_config import get_db

async def test_universal_interactions():
    """Test the universal memory agent with different interaction types"""
    
    print("🌟 Testing Universal Memory Agent")
    print("=" * 60)
    
    # Get database session
    db = next(get_db())
    universal_agent = UniversalMemoryAgent(db)
    
    test_user_id = "universal_test_user"
    print(f"Testing with user ID: {test_user_id}")
    
    # =================================================================
    # Test 1: Chat Interaction
    # =================================================================
    print("\n💬 Test 1: Chat Interaction")
    print("-" * 40)
    
    chat_result = await universal_agent.analyze_chat(
        user_id=test_user_id,
        user_query="I'm confused about the concept of Imamate. Can you explain it simply?",
        ai_response="Imamate in Shia Islam is the belief that after Prophet Muhammad, leadership should have passed to divinely appointed Imams, starting with Ali ibn Abi Talib...",
        session_id="chat_session_001"
    )
    
    print(f"Chat Analysis - Memory Updated: {chat_result['memory_updated']}")
    print(f"Notes Added: {len(chat_result.get('notes_added', []))}")
    if chat_result.get('error'):
        print(f"Error: {chat_result['error']}")
    
    # =================================================================
    # Test 2: Lesson Completion
    # =================================================================
    print("\n📚 Test 2: Lesson Completion")
    print("-" * 40)
    
    lesson_result = await universal_agent.analyze_lesson_completion(
        user_id=test_user_id,
        lesson_id="prayer-basics-001",
        lesson_title="Introduction to Shia Prayer",
        lesson_topics=["prayer", "wudu", "qibla", "rakat"],
        completion_time_minutes=25,
        engagement_score=0.85,
        lesson_summary="This lesson covers the fundamental aspects of Shia prayer including ablution, direction, and prayer structure."
    )
    
    print(f"Lesson Analysis - Memory Updated: {lesson_result['memory_updated']}")
    print(f"Notes Added: {len(lesson_result.get('notes_added', []))}")
    
    # =================================================================
    # Test 3: Quiz Result
    # =================================================================
    print("\n🧠 Test 3: Quiz Result")
    print("-" * 40)
    
    quiz_result = await universal_agent.analyze_quiz_result(
        user_id=test_user_id,
        quiz_id="imamate-quiz-001",
        score=0.6,  # 60% - showing some struggle
        total_questions=10,
        correct_answers=6,
        topics_tested=["imamate", "twelve_imams", "succession", "divine_appointment"],
        incorrect_topics=["imam_mahdi", "occultation", "return"],
        time_taken_minutes=12
    )
    
    print(f"Quiz Analysis - Memory Updated: {quiz_result['memory_updated']}")
    print(f"Notes Added: {len(quiz_result.get('notes_added', []))}")
    
    # =================================================================
    # Test 4: Hikmah Elaboration Request
    # =================================================================
    print("\n📖 Test 4: Hikmah Elaboration Request")
    print("-" * 40)
    
    hikmah_result = await universal_agent.analyze_hikmah_elaboration(
        user_id=test_user_id,
        selected_text="The best of people is he who benefits others",
        hikmah_tree_name="Sayings of Imam Ali",
        lesson_name="Justice and Compassion",
        context_text="This lesson discusses Imam Ali's teachings on social justice and helping others in the community."
    )
    
    print(f"Hikmah Analysis - Memory Updated: {hikmah_result['memory_updated']}")
    print(f"Notes Added: {len(hikmah_result.get('notes_added', []))}")
    
    # =================================================================
    # Test 5: Custom Interaction Type
    # =================================================================
    print("\n⚙️ Test 5: Custom Interaction (User Feedback)")
    print("-" * 40)
    
    feedback_result = await universal_agent.analyze_interaction(
        user_id=test_user_id,
        interaction_type=InteractionType.USER_FEEDBACK,
        interaction_data={
            "feedback_type": "lesson_rating",
            "lesson_id": "prayer-basics-001",
            "rating": 4,
            "comment": "Great lesson! I especially liked the step-by-step wudu guide. Could use more examples of common mistakes.",
            "helpful_aspects": ["step-by-step guide", "visual aids"],
            "improvement_suggestions": ["more examples", "common mistakes section"]
        },
        context={"feedback_source": "lesson_completion_survey"}
    )
    
    print(f"Feedback Analysis - Memory Updated: {feedback_result['memory_updated']}")
    print(f"Notes Added: {len(feedback_result.get('notes_added', []))}")
    
    # =================================================================
    # Test 6: Learning Assessment
    # =================================================================
    print("\n📊 Test 6: Learning Assessment")
    print("-" * 40)
    
    assessment_result = await universal_agent.analyze_interaction(
        user_id=test_user_id,
        interaction_type=InteractionType.ASSESSMENT,
        interaction_data={
            "assessment_type": "knowledge_level_check",
            "topics_assessed": ["basic_beliefs", "prayer", "imamate"],
            "proficiency_scores": {
                "basic_beliefs": 0.8,
                "prayer": 0.9,
                "imamate": 0.4  # Shows weakness
            },
            "overall_level": "intermediate_beginner",
            "recommended_focus_areas": ["imamate", "twelve_imams", "succession"]
        }
    )
    
    print(f"Assessment Analysis - Memory Updated: {assessment_result['memory_updated']}")
    print(f"Notes Added: {len(assessment_result.get('notes_added', []))}")
    
    # =================================================================
    # Final Memory Summary
    # =================================================================
    print("\n📊 COMPREHENSIVE MEMORY SUMMARY")
    print("=" * 60)
    
    # Get memory profile directly to show comprehensive data
    memory_profile = await universal_agent._get_or_create_memory_profile(test_user_id)
    
    print(f"Total Interactions: {memory_profile.total_interactions}")
    print(f"Memory Version: {memory_profile.memory_version}")
    
    # Show notes by category
    categories = {
        "Learning Notes": memory_profile.learning_notes or [],
        "Knowledge Notes": memory_profile.knowledge_notes or [],
        "Interest Notes": memory_profile.interest_notes or [],
        "Behavior Notes": memory_profile.behavior_notes or [],
        "Preference Notes": memory_profile.preference_notes or []
    }
    
    for category, notes in categories.items():
        print(f"\n{category} ({len(notes)}):")
        for note in notes[:3]:  # Show first 3 notes
            content = note.get('content', 'No content')[:80]
            confidence = note.get('confidence', 0)
            print(f"  - {content}... (confidence: {confidence})")
    
    print("\n✅ Universal Memory Agent Test Complete!")

async def main():
    """Main test function"""
    
    print("🚀 Universal Memory Agent Testing")
    print("Testing interaction-agnostic memory system")
    print("=" * 60)
    
    try:
        await test_universal_interactions()
        print("\n🎉 All universal tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
