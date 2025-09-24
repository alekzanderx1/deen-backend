#!/usr/bin/env python3
"""
Test script for the Memory Agent
Tests the chat interaction analysis and memory update functionality
"""

import sys
import os
import asyncio
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.core.memory_agent import MemoryAgent
from agents.models.db_config import get_db

async def test_memory_agent():
    """Test the memory agent with sample chat interactions"""
    
    print("🧠 Testing Memory Agent")
    print("=" * 50)
    
    # Get database session
    db = next(get_db())
    
    # Create memory agent
    memory_agent = MemoryAgent(db)
    
    # Test user ID
    test_user_id = "test_user_123"
    
    print(f"Testing with user ID: {test_user_id}")
    
    # Test Case 1: Beginner asking about basic Islamic concepts
    print("\n📝 Test Case 1: Basic Islamic Question")
    result1 = await memory_agent.analyze_chat_interaction(
        user_id=test_user_id,
        session_id="session_001",
        user_query="What is the difference between Shia and Sunni Islam? I'm new to learning about Islam.",
        ai_response_generated=True,
        topics_identified=["shia_sunni_differences", "islam_basics"],
        additional_context={"user_seems_new": True, "question_complexity": "beginner"}
    )
    
    print(f"Result 1: {json.dumps(result1, indent=2, default=str)}")
    
    # Test Case 2: More specific question about Imam Ali
    print("\n📝 Test Case 2: Specific Question about Imam Ali")
    result2 = await memory_agent.analyze_chat_interaction(
        user_id=test_user_id,
        session_id="session_001",
        user_query="Can you tell me more about Imam Ali's role in Islamic governance? I find his political philosophy fascinating.",
        ai_response_generated=True,
        topics_identified=["imam_ali", "islamic_governance", "political_philosophy"],
        additional_context={"follow_up_question": True, "shows_interest": True}
    )
    
    print(f"Result 2: {json.dumps(result2, indent=2, default=str)}")
    
    # Test Case 3: Question showing confusion
    print("\n📝 Test Case 3: Question Showing Confusion")
    result3 = await memory_agent.analyze_chat_interaction(
        user_id=test_user_id,
        session_id="session_002",
        user_query="I'm still confused about the concept of Imamate. How is it different from regular leadership?",
        ai_response_generated=True,
        topics_identified=["imamate", "divine_leadership"],
        additional_context={"shows_confusion": True, "repeat_topic": True}
    )
    
    print(f"Result 3: {json.dumps(result3, indent=2, default=str)}")
    
    # Get memory summary
    print("\n📊 User Memory Summary:")
    memory_summary = await memory_agent.get_user_memory_summary(test_user_id)
    print(json.dumps(memory_summary, indent=2, default=str))
    
    # Get interests and knowledge gaps
    print("\n🎯 User Interests:")
    interests = await memory_agent.get_user_interests(test_user_id)
    print(interests)
    
    print("\n📚 Knowledge Gaps:")
    gaps = await memory_agent.get_knowledge_gaps(test_user_id)
    print(gaps)
    
    print("\n✅ Memory Agent Test Complete!")

def test_simple_functionality():
    """Test basic functionality without LLM calls"""
    print("🔧 Testing Basic Functionality (No LLM)")
    print("=" * 50)
    
    try:
        from agents.models.user_memory_models import UserMemoryProfile
        from agents.models.db_config import get_db
        
        db = next(get_db())
        memory_agent = MemoryAgent(db)
        
        print("✅ Memory Agent created successfully")
        print("✅ Database connection works")
        print("✅ Models imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Main test function"""
    
    print("🚀 Memory Agent Testing Suite")
    print("=" * 50)
    
    # Test 1: Basic functionality
    basic_ok = test_simple_functionality()
    
    if not basic_ok:
        print("❌ Basic functionality test failed. Please fix before proceeding.")
        return
    
    # Test 2: Full memory agent functionality
    try:
        await test_memory_agent()
        print("\n🎉 All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during memory agent testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
