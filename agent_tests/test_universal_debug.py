#!/usr/bin/env python3
"""
Debug test for Universal Memory Agent - verify note creation and consolidation
"""

import sys
import os
import asyncio
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agents.core.universal_memory_agent import UniversalMemoryAgent, InteractionType
from agents.models.db_config import get_db

async def debug_note_creation():
    """Debug why notes aren't being created"""
    
    print("🔍 Debugging Universal Memory Agent Note Creation")
    print("=" * 60)
    
    # Get database session
    db = next(get_db())
    universal_agent = UniversalMemoryAgent(db)
    
    test_user_id = "debug_universal_user"
    print(f"Testing with user ID: {test_user_id}")
    
    # =================================================================
    # Test 1: Simple Chat - Should definitely create notes
    # =================================================================
    print("\n💬 Test 1: Simple Chat (Should Create Notes)")
    print("-" * 50)
    
    try:
        # Get memory profile first
        memory_profile = await universal_agent._get_or_create_memory_profile(test_user_id)
        print(f"Initial memory profile created: {memory_profile.id}")
        
        # Test the LLM analysis directly
        interaction_data = {
            "user_query": "I'm completely new to Islam and want to learn about Shia beliefs",
            "ai_response": "Welcome to learning about Islam! Shia Islam has several core beliefs including the Imamate...",
            "chat_history": []
        }
        
        print("Testing LLM analysis directly...")
        analysis_result = await universal_agent._analyze_universal_interaction(
            memory_profile, 
            InteractionType.CHAT, 
            interaction_data, 
            {}
        )
        
        print("LLM Analysis Result:")
        print(json.dumps(analysis_result, indent=2))
        
        # Now test the full flow
        print("\nTesting full interaction flow...")
        result = await universal_agent.analyze_chat(
            user_id=test_user_id,
            user_query="I'm completely new to Islam and want to learn about Shia beliefs",
            ai_response="Welcome to learning about Islam! Shia Islam has several core beliefs including the Imamate, the Twelve Imams, and the concept of divine guidance through the Ahl al-Bayt.",
            session_id="debug_session_001"
        )
        
        print(f"Full Flow Result:")
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Error in Test 1: {e}")
        import traceback
        traceback.print_exc()
    
    # =================================================================
    # Test 2: Check current memory state
    # =================================================================
    print("\n📊 Test 2: Current Memory State")
    print("-" * 50)
    
    try:
        memory_profile = await universal_agent._get_or_create_memory_profile(test_user_id)
        
        print(f"Total interactions: {memory_profile.total_interactions}")
        print(f"Learning notes: {len(memory_profile.learning_notes or [])}")
        print(f"Knowledge notes: {len(memory_profile.knowledge_notes or [])}")
        print(f"Interest notes: {len(memory_profile.interest_notes or [])}")
        print(f"Behavior notes: {len(memory_profile.behavior_notes or [])}")
        print(f"Preference notes: {len(memory_profile.preference_notes or [])}")
        
        # Show actual notes if any exist
        all_notes = []
        for note_type in ['learning_notes', 'knowledge_notes', 'interest_notes', 'behavior_notes', 'preference_notes']:
            notes = getattr(memory_profile, note_type) or []
            all_notes.extend(notes)
        
        if all_notes:
            print(f"\nActual notes ({len(all_notes)}):")
            for i, note in enumerate(all_notes):
                print(f"{i+1}. {note.get('content', 'No content')[:100]}...")
        else:
            print("\n⚠️ No notes found!")
        
    except Exception as e:
        print(f"❌ Error in Test 2: {e}")
        import traceback
        traceback.print_exc()
    
    # =================================================================
    # Test 3: Force note creation and test consolidation
    # =================================================================
    print("\n🧠 Test 3: Force Multiple Notes and Test Consolidation")
    print("-" * 50)
    
    try:
        # Add multiple similar interactions to force note creation
        similar_queries = [
            "I want to learn about Imam Ali's teachings",
            "Can you tell me more about Imam Ali's wisdom?",
            "What are some famous sayings of Imam Ali?",
            "I'm interested in Imam Ali's philosophy",
            "Tell me about Imam Ali's role in Islam"
        ]
        
        for i, query in enumerate(similar_queries):
            print(f"Adding interaction {i+1}: {query[:50]}...")
            result = await universal_agent.analyze_chat(
                user_id=test_user_id,
                user_query=query,
                ai_response=f"Imam Ali is known for his wisdom and teachings. Here's what you should know about {query.lower()}...",
                session_id=f"debug_session_{i+2}"
            )
            print(f"  Memory updated: {result.get('memory_updated', False)}")
            print(f"  Notes added: {len(result.get('notes_added', []))}")
            
            if result.get('error'):
                print(f"  Error: {result['error']}")
        
        # Check memory state after multiple interactions
        memory_profile = await universal_agent._get_or_create_memory_profile(test_user_id)
        total_notes = sum([
            len(memory_profile.learning_notes or []),
            len(memory_profile.knowledge_notes or []),
            len(memory_profile.interest_notes or []),
            len(memory_profile.behavior_notes or []),
            len(memory_profile.preference_notes or [])
        ])
        
        print(f"\nAfter multiple interactions:")
        print(f"Total interactions: {memory_profile.total_interactions}")
        print(f"Total notes: {total_notes}")
        
        # Test consolidation
        if total_notes > 0:
            print("\n🔄 Testing Consolidation...")
            should_consolidate = await universal_agent.consolidator.should_trigger_consolidation(memory_profile)
            print(f"Should trigger consolidation: {should_consolidate}")
            
            if should_consolidate or total_notes > 3:  # Force consolidation for testing
                print("Triggering manual consolidation...")
                consolidation_result = await universal_agent.consolidator.consolidate_user_memory(
                    memory_profile, "manual_debug"
                )
                print(f"Consolidation result: {json.dumps(consolidation_result, indent=2, default=str)}")
        else:
            print("⚠️ No notes to consolidate!")
        
    except Exception as e:
        print(f"❌ Error in Test 3: {e}")
        import traceback
        traceback.print_exc()
    
    # =================================================================
    # Test 4: Different interaction types
    # =================================================================
    print("\n📚 Test 4: Different Interaction Types")
    print("-" * 50)
    
    try:
        # Test lesson completion
        lesson_result = await universal_agent.analyze_lesson_completion(
            user_id=test_user_id,
            lesson_id="test-lesson-001",
            lesson_title="Basic Islamic Beliefs",
            lesson_topics=["tawhid", "prophethood", "imamate"],
            completion_time_minutes=20,
            engagement_score=0.9
        )
        
        print(f"Lesson completion - Memory updated: {lesson_result.get('memory_updated', False)}")
        print(f"Notes added: {len(lesson_result.get('notes_added', []))}")
        
        # Test quiz result
        quiz_result = await universal_agent.analyze_quiz_result(
            user_id=test_user_id,
            quiz_id="beliefs-quiz-001",
            score=0.5,  # Low score to trigger learning gap notes
            total_questions=10,
            correct_answers=5,
            topics_tested=["tawhid", "imamate", "prophethood"],
            incorrect_topics=["imamate", "twelve_imams"]
        )
        
        print(f"Quiz result - Memory updated: {quiz_result.get('memory_updated', False)}")
        print(f"Notes added: {len(quiz_result.get('notes_added', []))}")
        
    except Exception as e:
        print(f"❌ Error in Test 4: {e}")
        import traceback
        traceback.print_exc()
    
    # =================================================================
    # Final Summary
    # =================================================================
    print("\n📊 FINAL SUMMARY")
    print("=" * 60)
    
    try:
        memory_profile = await universal_agent._get_or_create_memory_profile(test_user_id)
        
        final_total_notes = sum([
            len(memory_profile.learning_notes or []),
            len(memory_profile.knowledge_notes or []),
            len(memory_profile.interest_notes or []),
            len(memory_profile.behavior_notes or []),
            len(memory_profile.preference_notes or [])
        ])
        
        print(f"Final total interactions: {memory_profile.total_interactions}")
        print(f"Final total notes: {final_total_notes}")
        
        if final_total_notes > 0:
            print("✅ Universal agent IS creating notes!")
            
            # Show sample notes
            print("\nSample notes:")
            for note_type in ['learning_notes', 'knowledge_notes', 'interest_notes', 'behavior_notes', 'preference_notes']:
                notes = getattr(memory_profile, note_type) or []
                if notes:
                    print(f"\n{note_type.replace('_', ' ').title()} ({len(notes)}):")
                    for note in notes[:2]:  # Show first 2
                        print(f"  - {note.get('content', 'No content')[:80]}...")
        else:
            print("❌ Universal agent is NOT creating notes - need to investigate!")
        
    except Exception as e:
        print(f"❌ Error in final summary: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main debug function"""
    
    print("🚀 Universal Memory Agent Debug Test")
    print("Verifying note creation and consolidation functionality")
    print("=" * 70)
    
    try:
        await debug_note_creation()
        print("\n✅ Debug test complete!")
    except Exception as e:
        print(f"\n❌ Error during debug test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
