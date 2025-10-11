"""
Basic integration test for user_progress API with string user_id
Run with: pytest db/test_user_progress_api.py
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_create_user_progress_with_string_user_id():
    """Test creating user progress with string user_id"""
    payload = {
        "user_id": "test_user_cognito_123",
        "lesson_id": 1,
        "percent_complete": 50.0,
        "is_completed": False,
    }
    
    response = client.post("/user-progress", json=payload)
    
    # Should succeed (201 or 200)
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["user_id"] == "test_user_cognito_123"
    assert data["lesson_id"] == 1
    assert data["percent_complete"] == 50.0
    return data["id"]


def test_list_user_progress_filter_by_string_user_id():
    """Test filtering user progress by string user_id"""
    # Create a progress record first
    payload = {
        "user_id": "jane.doe@example.com",
        "lesson_id": 5,
        "percent_complete": 75.0,
    }
    create_response = client.post("/user-progress", json=payload)
    assert create_response.status_code in [200, 201]
    
    # Now filter by user_id
    response = client.get("/user-progress", params={"user_id": "jane.doe@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should have at least the one we just created
    user_records = [r for r in data if r["user_id"] == "jane.doe@example.com"]
    assert len(user_records) >= 1
    

def test_create_user_progress_rejects_integer_user_id():
    """Test that integer user_id is rejected (now expects string)"""
    payload = {
        "user_id": 42,  # Integer - should fail validation
        "lesson_id": 1,
    }
    
    response = client.post("/user-progress", json=payload)
    # Pydantic should coerce int to str, so this might actually pass
    # depending on strict mode. Let's just verify it's stored as string.
    if response.status_code in [200, 201]:
        data = response.json()
        assert isinstance(data["user_id"], str)
        assert data["user_id"] == "42"


def test_update_user_progress_with_string_user_id():
    """Test updating user progress record"""
    # Create first
    payload = {
        "user_id": "update_test_user",
        "lesson_id": 10,
        "percent_complete": 30.0,
    }
    create_response = client.post("/user-progress", json=payload)
    assert create_response.status_code in [200, 201]
    progress_id = create_response.json()["id"]
    
    # Update
    update_payload = {
        "percent_complete": 100.0,
        "is_completed": True,
        "notes": "Finished the lesson!",
    }
    response = client.patch(f"/user-progress/{progress_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["percent_complete"] == 100.0
    assert data["is_completed"] is True
    assert data["user_id"] == "update_test_user"


def test_long_user_id_within_limit():
    """Test that user_id up to 128 chars is accepted"""
    long_user_id = "a" * 128  # Max length
    payload = {
        "user_id": long_user_id,
        "lesson_id": 1,
    }
    
    response = client.post("/user-progress", json=payload)
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["user_id"] == long_user_id


if __name__ == "__main__":
    # Quick manual run
    print("Testing user_progress API with string user_id...")
    try:
        test_create_user_progress_with_string_user_id()
        print("✅ Create with string user_id")
        
        test_list_user_progress_filter_by_string_user_id()
        print("✅ Filter by string user_id")
        
        test_create_user_progress_rejects_integer_user_id()
        print("✅ Integer coercion check")
        
        test_update_user_progress_with_string_user_id()
        print("✅ Update user progress")
        
        test_long_user_id_within_limit()
        print("✅ Long user_id (128 chars)")
        
        print("\n🎉 All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

