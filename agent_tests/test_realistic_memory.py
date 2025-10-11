#!/usr/bin/env python3
"""
Realistic test script for the Memory Agent
Tests with realistic chat data (just user query, AI response, and chat history)
"""

import sys
import os
import asyncio
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.core.memory_agent import MemoryAgent
from agents.models.db_config import get_db

async def test_realistic_scenarios():
    """Test memory agent with realistic chat scenarios"""
    
    print("🧠 Testing Memory Agent - Realistic Scenarios")
    print("=" * 60)
    
    # Get database session
    db = next(get_db())
    memory_agent = MemoryAgent(db)
    
    test_user_id = "realistic_user_456"
    print(f"Testing with user ID: {test_user_id}")
    
    # =================================================================
    # Scenario 1: New user asking basic question
    # =================================================================
    print("\n📝 Scenario 1: New User - Basic Question")
    print("-" * 40)
    
    result1 = await memory_agent.analyze_chat_interaction(
        user_id=test_user_id,
        session_id="session_001",
        user_query="Hi, I'm new to learning about Islam. Can you explain what Shia Islam is?",
        ai_response="Shia Islam is the second-largest branch of Islam, comprising about 10-15% of Muslims worldwide. Shia Muslims believe that after Prophet Muhammad's death, leadership of the Muslim community should have passed to Ali ibn Abi Talib, the Prophet's cousin and son-in-law, and then to his descendants known as the Imams. The word 'Shia' comes from 'Shi'at Ali' meaning 'followers of Ali.' Shia Muslims follow the Twelve Imams, starting with Imam Ali and ending with the twelfth Imam, Muhammad al-Mahdi, who is believed to be in occultation.",
        chat_history=[]  # First interaction
    )
    
    print(f"Memory Updated: {result1.get('memory_updated', False)}")
    print(f"Reasoning: {result1.get('reasoning', 'No reasoning provided')}")
    print(f"Notes Added: {len(result1.get('notes_added', []))}")
    
    # =================================================================
    # Scenario 2: Follow-up question showing interest
    # =================================================================
    print("\n📝 Scenario 2: Follow-up Question - Showing Interest")
    print("-" * 40)
    
    previous_history = [
        {"role": "user", "content": "Hi, I'm new to learning about Islam. Can you explain what Shia Islam is?"},
        {"role": "assistant", "content": "Shia Islam is the second-largest branch of Islam, comprising about 10-15% of Muslims worldwide..."}
    ]
    
    result2 = await memory_agent.analyze_chat_interaction(
        user_id=test_user_id,
        session_id="session_001",
        user_query="That's fascinating! Can you tell me more about Imam Ali? What made him special?",
        ai_response="Imam Ali ibn Abi Talib holds a very special place in Islamic history, particularly in Shia Islam. He was the Prophet Muhammad's cousin, raised in the Prophet's household, and one of the first to accept Islam. Ali was known for his exceptional knowledge, courage in battle, and wisdom in governance. He married Fatimah, the Prophet's daughter, making him the father of the Prophet's grandsons, Hassan and Hussein. Shia Muslims believe Ali was divinely appointed as the Prophet's successor and that he possessed special spiritual knowledge passed down from the Prophet.",
        chat_history=previous_history
    )
    
    print(f"Memory Updated: {result2.get('memory_updated', False)}")
    print(f"Reasoning: {result2.get('reasoning', 'No reasoning provided')}")
    print(f"Notes Added: {len(result2.get('notes_added', []))}")
    
    # =================================================================
    # Scenario 3: Question showing confusion/difficulty
    # =================================================================
    print("\n📝 Scenario 3: Confusion - Complex Concept")
    print("-" * 40)
    
    updated_history = previous_history + [
        {"role": "user", "content": "That's fascinating! Can you tell me more about Imam Ali? What made him special?"},
        {"role": "assistant", "content": "Imam Ali ibn Abi Talib holds a very special place in Islamic history..."}
    ]
    
    result3 = await memory_agent.analyze_chat_interaction(
        user_id=test_user_id,
        session_id="session_001", 
        user_query="I'm still confused about something. You mentioned the twelve Imams, but I don't understand how this works exactly. Are they like prophets? And what does 'occultation' mean?",
        ai_response="Great questions! The Twelve Imams in Shia Islam are not prophets, but they are considered divinely guided leaders with special spiritual authority. Unlike prophets who receive new revelation, Imams interpret and preserve the teachings of Islam. The concept of occultation (Ghaybah) refers to the belief that the twelfth Imam, Muhammad al-Mahdi, is alive but hidden from the world. Shia Muslims believe he will return as the Mahdi to establish justice on earth before the Day of Judgment.",
        chat_history=updated_history
    )
    
    print(f"Memory Updated: {result3.get('memory_updated', False)}")
    print(f"Reasoning: {result3.get('reasoning', 'No reasoning provided')}")
    print(f"Notes Added: {len(result3.get('notes_added', []))}")
    
    # =================================================================
    # Scenario 4: Practical question - showing different interests
    # =================================================================
    print("\n📝 Scenario 4: Practical Question - Different Interest")
    print("-" * 40)
    
    result4 = await memory_agent.analyze_chat_interaction(
        user_id=test_user_id,
        session_id="session_002",  # New session
        user_query="I want to start practicing Islam. What are the differences between Shia and Sunni prayer practices?",
        ai_response="There are some differences in prayer practices between Shia and Sunni Muslims. In Shia prayer: 1) We place our forehead on clean earth, clay, or stone (like a prayer tablet/turbah) during prostration, often made from Karbala soil. 2) We keep our arms by our sides during standing, rather than folding them. 3) We combine some prayers (Dhuhr with Asr, Maghrib with Isha) which is permissible. 4) We have slightly different wording in some parts of the prayer. 5) The call to prayer (Adhan) includes 'Ashhadu anna Aliyan Waliyyullah' (I bear witness that Ali is the friend of Allah).",
        chat_history=[]  # New session, no recent history
    )
    
    print(f"Memory Updated: {result4.get('memory_updated', False)}")
    print(f"Reasoning: {result4.get('reasoning', 'No reasoning provided')}")
    print(f"Notes Added: {len(result4.get('notes_added', []))}")
    
    # =================================================================
    # Get final memory summary
    # =================================================================
    print("\n📊 FINAL USER MEMORY SUMMARY")
    print("=" * 60)
    
    memory_summary = await memory_agent.get_user_memory_summary(test_user_id)
    print(json.dumps(memory_summary, indent=2, default=str))
    
    # Get interests and knowledge gaps
    print("\n🎯 User Interests:")
    interests = await memory_agent.get_user_interests(test_user_id)
    print(interests)
    
    print("\n📚 Knowledge Gaps:")
    gaps = await memory_agent.get_knowledge_gaps(test_user_id)
    print(gaps)
    
    print("\n✅ Realistic Memory Agent Test Complete!")

async def main():
    """Main test function"""
    
    print("🚀 Realistic Memory Agent Testing")
    print("Testing with raw chat data (no pre-processed topics/context)")
    print("=" * 60)
    
    try:
        await test_realistic_scenarios()
        print("\n🎉 All realistic tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
