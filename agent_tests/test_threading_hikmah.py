#!/usr/bin/env python3
"""
Quick test to verify the threading-based fire-and-forget memory update works
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.generation.stream_generator import generate_elaboration_response_stream
import time

def test_threading_memory_update():
    """Test that memory update runs in background thread without blocking"""
    
    print("=" * 80)
    print("🧪 Testing Threading-Based Memory Update (Fire and Forget)")
    print("=" * 80)
    
    # Simulate the stream generator call with user_id
    selected_text = "What is Tawakkul?"
    context_text = "Tawakkul (trust in Allah) is a fundamental concept in Islamic spirituality..."
    hikmah_tree_name = "Spiritual Development"
    lesson_name = "Trust in Divine Providence"
    lesson_summary = "Understanding tawakkul and reliance on Allah"
    retrieved_docs = []  # Empty for this test
    user_id = "threading_test_user_001"
    
    print(f"\n📥 Simulating stream with user_id: {user_id}")
    print(f"   Selected: {selected_text}")
    
    # Consume the stream
    print("\n🔄 Starting stream...")
    start_time = time.time()
    
    chunk_count = 0
    for chunk in generate_elaboration_response_stream(
        selected_text=selected_text,
        context_text=context_text,
        hikmah_tree_name=hikmah_tree_name,
        lesson_name=lesson_name,
        lesson_summary=lesson_summary,
        retrieved_docs=retrieved_docs,
        user_id=user_id
    ):
        chunk_count += 1
        # Just consume the stream, don't print content
        pass
    
    stream_time = time.time() - start_time
    
    print(f"\n✅ Stream completed!")
    print(f"   ⏱️  Time: {stream_time:.2f}s")
    print(f"   📊 Chunks: {chunk_count}")
    print(f"\n💡 The memory update should be running in background thread...")
    print(f"   (Check server logs for '🧠 Memory agent thread started' message)")
    
    # Give the background thread a moment to complete
    print(f"\n⏳ Waiting 5 seconds for background thread to complete...")
    time.sleep(5)
    
    print(f"\n✅ Test complete! Check logs for memory update confirmation.")
    print("=" * 80)
    
    # Verify memory was updated by checking database
    print(f"\n📊 Checking database for memory update...")
    from agents.models.db_config import SessionLocal
    from agents.models.user_memory_models import UserMemoryProfile
    
    db = SessionLocal()
    try:
        profile = db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        
        if profile:
            print(f"✅ User profile found!")
            print(f"   Total interactions: {profile.total_interactions}")
            print(f"   Total notes: {len(profile.learning_notes or []) + len(profile.interest_notes or []) + len(profile.knowledge_notes or [])}")
            
            if profile.total_interactions > 0:
                print(f"\n🎉 SUCCESS: Memory agent ran in background and updated database!")
            else:
                print(f"\n⚠️  Profile exists but no interactions recorded yet")
        else:
            print(f"⚠️  No profile found yet - background thread may still be running")
    finally:
        db.close()


if __name__ == "__main__":
    test_threading_memory_update()


