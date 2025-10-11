#!/usr/bin/env python3
"""
Debug test for consolidation - focus on the LLM consolidation issue
"""

import sys
import os
import asyncio
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.core.memory_agent import MemoryAgent
from agents.models.db_config import get_db

async def test_consolidation_only():
    """Test just the consolidation functionality"""
    
    print("🧠 Debug: Testing Consolidation Only")
    print("=" * 50)
    
    # Get database session
    db = next(get_db())
    memory_agent = MemoryAgent(db)
    
    test_user_id = "debug_consolidation_user"
    
    # =================================================================
    # Step 1: Add many notes quickly to force consolidation
    # =================================================================
    print("\n📝 Adding Multiple Notes to Force Consolidation")
    print("-" * 50)
    
    # Create a user with many notes
    memory_profile = await memory_agent._get_or_create_memory_profile(test_user_id)
    
    # Manually add many notes to trigger consolidation
    test_notes = [
        {
            "id": f"note_{i}",
            "content": f"User shows interest in topic {i % 3}",
            "evidence": f"Query about topic {i % 3}",
            "confidence": 0.8,
            "category": "interest",
            "tags": [f"topic_{i % 3}"],
            "note_type": "interest_notes",
            "created_at": "2024-01-01T12:00:00Z"
        }
        for i in range(20)  # 20 similar notes
    ]
    
    # Add notes directly to memory profile
    memory_profile.interest_notes = test_notes
    memory_profile.total_interactions = 20
    db.commit()
    
    print(f"Added {len(test_notes)} test notes")
    
    # =================================================================
    # Step 2: Check if consolidation should trigger
    # =================================================================
    should_consolidate = await memory_agent.consolidator.should_trigger_consolidation(memory_profile)
    print(f"Should trigger consolidation: {should_consolidate}")
    
    # =================================================================
    # Step 3: Test consolidation with debug info
    # =================================================================
    print("\n🧠 Testing Manual Consolidation with Debug")
    print("-" * 50)
    
    try:
        consolidation_result = await memory_agent.consolidator.consolidate_user_memory(memory_profile, "debug_test")
        print("Consolidation Result:")
        print(json.dumps(consolidation_result, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Consolidation error: {e}")
        import traceback
        traceback.print_exc()
    
    # =================================================================
    # Step 4: Test the LLM consolidation directly
    # =================================================================
    print("\n🔧 Testing LLM Consolidation Directly")
    print("-" * 50)
    
    memory_data = memory_agent.consolidator._prepare_memory_for_consolidation(memory_profile)
    
    try:
        llm_result = await memory_agent.consolidator._llm_consolidate_memory(memory_data, "direct_test")
        print("LLM Result:")
        print(json.dumps(llm_result, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ LLM consolidation error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main debug function"""
    
    print("🚀 Consolidation Debug Test")
    print("=" * 50)
    
    try:
        await test_consolidation_only()
        print("\n✅ Debug test complete!")
    except Exception as e:
        print(f"\n❌ Error during debug test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
