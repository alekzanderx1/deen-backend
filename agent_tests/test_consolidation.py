#!/usr/bin/env python3
"""
Test script for Smart Memory Consolidation
Demonstrates duplicate detection, semantic similarity, and LLM-powered consolidation
"""

import sys
import os
import asyncio
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.core.memory_agent import MemoryAgent
from agents.models.db_config import get_db

async def test_consolidation_features():
    """Test the smart consolidation features"""
    
    print("🧠 Testing Smart Memory Consolidation")
    print("=" * 60)
    
    # Get database session
    db = next(get_db())
    memory_agent = MemoryAgent(db)
    
    test_user_id = "consolidation_test_user"
    print(f"Testing with user ID: {test_user_id}")
    
    # =================================================================
    # Step 1: Add several similar notes to trigger consolidation
    # =================================================================
    print("\n📝 Step 1: Adding Similar Notes About Imam Ali")
    print("-" * 50)
    
    similar_interactions = [
        {
            "query": "Tell me about Imam Ali's wisdom",
            "response": "Imam Ali was known for his profound wisdom and sayings collected in Nahj al-Balagha..."
        },
        {
            "query": "I love reading Imam Ali's quotes",
            "response": "Imam Ali's sayings in Nahj al-Balagha are indeed profound and offer timeless wisdom..."
        },
        {
            "query": "What made Imam Ali so wise?",
            "response": "Imam Ali's wisdom came from his close relationship with Prophet Muhammad and divine guidance..."
        },
        {
            "query": "Can you share some of Imam Ali's teachings?",
            "response": "Here are some beautiful teachings from Imam Ali about justice, knowledge, and faith..."
        }
    ]
    
    for i, interaction in enumerate(similar_interactions):
        print(f"Adding interaction {i+1}...")
        result = await memory_agent.analyze_chat_interaction(
            user_id=test_user_id,
            session_id=f"session_{i+1}",
            user_query=interaction["query"],
            ai_response=interaction["response"],
            chat_history=[]
        )
        print(f"  Notes added: {len(result.get('notes_added', []))}")
    
    # =================================================================
    # Step 2: Add notes about different topics
    # =================================================================
    print("\n📝 Step 2: Adding Notes About Different Topics")
    print("-" * 50)
    
    diverse_interactions = [
        {
            "query": "How do I perform wudu?",
            "response": "Wudu is the ritual ablution performed before prayer. Here are the steps..."
        },
        {
            "query": "What happened at Karbala?",
            "response": "The tragedy of Karbala occurred when Imam Hussein and his companions were martyred..."
        },
        {
            "query": "I want to learn Arabic to read Quran",
            "response": "Learning Arabic is a noble pursuit. Here are some resources for Quranic Arabic..."
        },
        {
            "query": "What is Ashura?",
            "response": "Ashura is the 10th day of Muharram when we commemorate the martyrdom of Imam Hussein..."
        }
    ]
    
    for i, interaction in enumerate(diverse_interactions):
        print(f"Adding diverse interaction {i+1}...")
        result = await memory_agent.analyze_chat_interaction(
            user_id=test_user_id,
            session_id=f"session_{i+5}",
            user_query=interaction["query"],
            ai_response=interaction["response"],
            chat_history=[]
        )
        print(f"  Notes added: {len(result.get('notes_added', []))}")
    
    # =================================================================
    # Step 3: Try to add duplicate note (should be filtered)
    # =================================================================
    print("\n📝 Step 3: Testing Duplicate Detection")
    print("-" * 50)
    
    duplicate_result = await memory_agent.analyze_chat_interaction(
        user_id=test_user_id,
        session_id="session_duplicate",
        user_query="I really appreciate Imam Ali's wisdom and teachings",
        ai_response="Imam Ali's wisdom is indeed profound and continues to guide us today...",
        chat_history=[]
    )
    
    print(f"Duplicate test - Notes added: {len(duplicate_result.get('notes_added', []))}")
    print(f"Reasoning: {duplicate_result.get('reasoning', 'No reasoning')}")
    
    # =================================================================
    # Step 4: Check current memory state
    # =================================================================
    print("\n📊 Step 4: Current Memory Summary")
    print("-" * 50)
    
    memory_summary = await memory_agent.get_user_memory_summary(test_user_id)
    print(f"Total interactions: {memory_summary['total_interactions']}")
    print(f"Note counts: {memory_summary['memory_counts']}")
    
    total_notes = sum(memory_summary['memory_counts'].values())
    print(f"Total notes: {total_notes}")
    
    # =================================================================
    # Step 5: Manual consolidation trigger
    # =================================================================
    print("\n🧠 Step 5: Manual Memory Consolidation")
    print("-" * 50)
    
    consolidation_result = await memory_agent.manually_consolidate_memory(test_user_id)
    print(f"Consolidation success: {consolidation_result.get('success', False)}")
    
    if consolidation_result.get('success'):
        print(f"Notes before: {consolidation_result.get('notes_before', 0)}")
        print(f"Notes after: {consolidation_result.get('notes_after', 0)}")
        print(f"Notes removed: {consolidation_result.get('notes_removed', 0)}")
        print(f"Reasoning: {consolidation_result.get('reasoning', 'No reasoning')[:200]}...")
    else:
        print(f"Consolidation failed: {consolidation_result.get('error', 'Unknown error')}")
    
    # =================================================================
    # Step 6: Check memory after consolidation
    # =================================================================
    print("\n📊 Step 6: Memory After Consolidation")
    print("-" * 50)
    
    updated_memory = await memory_agent.get_user_memory_summary(test_user_id)
    print(f"Updated note counts: {updated_memory['memory_counts']}")
    
    new_total = sum(updated_memory['memory_counts'].values())
    print(f"New total notes: {new_total}")
    
    # Show sample consolidated notes
    print("\n📋 Sample Consolidated Notes:")
    for category, notes in updated_memory['recent_notes'].items():
        if notes:
            print(f"\n{category.replace('_', ' ').title()}:")
            for note in notes[:2]:  # Show first 2 notes in each category
                content = note.get('content', 'No content')[:100]
                confidence = note.get('confidence', 0)
                print(f"  - {content}... (confidence: {confidence})")
    
    # =================================================================
    # Step 7: Consolidation analytics
    # =================================================================
    print("\n📈 Step 7: Consolidation Analytics")
    print("-" * 50)
    
    analytics = await memory_agent.get_consolidation_analytics(test_user_id)
    print(json.dumps(analytics, indent=2, default=str))
    
    print("\n✅ Smart Consolidation Test Complete!")

async def main():
    """Main test function"""
    
    print("🚀 Smart Memory Consolidation Testing")
    print("Testing duplicate detection, semantic similarity, and LLM consolidation")
    print("=" * 70)
    
    try:
        await test_consolidation_features()
        print("\n🎉 All consolidation tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
