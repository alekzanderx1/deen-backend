import requests
import json
import sys
from pprint import pprint

# -------------------------------------------------------------------
# Configure base URL for your running FastAPI app
# -------------------------------------------------------------------
BASE_URL = "http://127.0.0.1:8000"   # change to your deployed URL if remote
# db/sample_api_usage.py (drop-in helpers)

def debug_response(r, label=""):
    print(f"\n[{r.status_code}] {r.request.method} {r.url}  -- {label}")
    print("Content-Type:", r.headers.get("content-type"))
    body_text = r.text[:1000]  # show up to 1k chars
    print("Raw body (truncated):\n", body_text)

def expect_json_ok(r, label):
    debug_response(r, label)
    if r.status_code == 204:
        # No body by design
        return None
    ct = (r.headers.get("content-type") or "").lower()
    if "application/json" not in ct:
        print("ERROR: Response is not JSON. See raw body above.")
        sys.exit(1)
    j = r.json()
    if not r.ok:
        print("ERROR payload:")
        pprint(j)
        sys.exit(1)
    return j

def print_header(title: str):
    print("\n" + "="*80)
    print(title)
    print("="*80)

def pretty(r):
    """Helper to print status and JSON nicely."""
    print(f"\n[{r.status_code}] {r.request.method} {r.url}")
    try:
        pprint(r.json())
    except Exception:
        print(r.text)

# -------------------------------------------------------------------
# 1️⃣ Create a User
# -------------------------------------------------------------------
print_header("1️⃣ Create a user")
user_payload = {
    "email": "hehe123@example.com",
    "password_hash": "hashed123",
    "display_name": "Mo Deen",
    "role": "student",
}
r = requests.post(f"{BASE_URL}/users", json=user_payload)
expect_json_ok(r, "create user")
if r:
    pretty(r)
    user_id = r.json()["id"]
else:
    user_id = 4 ## Default Tamieem


# -------------------------------------------------------------------
# 2️⃣ Create a Hikmah Tree
# -------------------------------------------------------------------
print_header("2️⃣ Create a hikmah tree")
tree_payload = {
    "title": "Nahjul Balagha Wisdoms",
    "summary": "Sayings and lessons from Imam Hussein (a.s.)",
    "tags": ["wisdom", "character"],
    "skill_level": 6
}
r = requests.post(f"{BASE_URL}/hikmah-trees", json=tree_payload)
if r:
    pretty(r)
    hikmah_tree_id = r.json()["id"]
else:
    hikmah_tree_id = 1 ## Default Hikmah Tree

# -------------------------------------------------------------------
# 3️⃣ Create a Lesson linked to the tree and user
# -------------------------------------------------------------------
print_header("3️⃣ Create a lesson")
lesson_payload = {
    "slug": "intro-to-Ahlul-Bayt",
    "title": "Introduction to Ahlul Bayt",
    "summary": "Learning about Shiaisms.",
    "tags": ["sabr", "character"],
    "status": "published",
    "language_code": "en",
    "author_user_id": 0,
    "estimated_minutes": 20,
    "hikmah_tree_id": hikmah_tree_id,
    "order_position": 1
}
r = requests.post(f"{BASE_URL}/lessons", json=lesson_payload)
if r:
    pretty(r)
    lesson_id = r.json()["id"]
else:
    lesson_id = 1 # Default Lesson ID

# -------------------------------------------------------------------
# 4️⃣ Add Lesson Content (multiple sections)
# -------------------------------------------------------------------
print_header("4️⃣ Add lesson content sections")
sections = [
    {
        "lesson_id": lesson_id,
        "order_position": 1,
        "title": "Who are the Imams",
        "content_type": "markdown",
        "content_body": "## Sample Body Text."
    },
    {
        "lesson_id": lesson_id,
        "order_position": 2,
        "title": "Who is Bibi Fatemah",
        "content_type": "markdown",
        "content_body": "sample text."
    }
]
content_id = 1
for s in sections:
    r = requests.post(f"{BASE_URL}/lesson-content", json=s)
    pretty(r)
    content_id = r.json()["id"]

# -------------------------------------------------------------------
# 5️⃣ Get all lessons and filter by tag
# -------------------------------------------------------------------
print_header("5️⃣ Get lessons (filter by tag='sabr')")
r = requests.get(f"{BASE_URL}/lessons", params={"tag": "sabr"})
pretty(r)

# -------------------------------------------------------------------
# 6️⃣ Get a specific lesson by ID
# -------------------------------------------------------------------
print_header("6️⃣ Get specific lesson by ID")
r = requests.get(f"{BASE_URL}/lessons/{lesson_id}")
pretty(r)

# -------------------------------------------------------------------
# 7️⃣ Update lesson summary
# -------------------------------------------------------------------
print_header("7️⃣ Update lesson summary")
update_payload = {"summary": "An updated overview of Sabr and its importance."}
r = requests.patch(f"{BASE_URL}/lessons/{lesson_id}", json=update_payload)
pretty(r)

# -------------------------------------------------------------------
# 8️⃣ Track user progress (mark section 1 as 100%)
# -------------------------------------------------------------------
print_header("8️⃣ Create user progress record")
progress_payload = {
    "user_id": 4,
    "lesson_id": lesson_id,
    "content_id": content_id,
    "percent_complete": 100.0,
    "is_completed": True,
    "notes": "Completed first section."
}
r = requests.post(f"{BASE_URL}/user-progress", json=progress_payload)
if r:
    pretty(r)
    progress_id = r.json()["id"]
else:
    progress_id = 1

# -------------------------------------------------------------------
# 9️⃣ Get user progress for that lesson
# -------------------------------------------------------------------
print_header("9️⃣ Get user progress by user & lesson")
r = requests.get(f"{BASE_URL}/user-progress", params={"user_id": 4, "lesson_id": lesson_id})
pretty(r)

# -------------------------------------------------------------------
# 🔟 Update user progress (add note)
# -------------------------------------------------------------------
print_header("🔟 Update user progress note")
update_payload = {"notes": "Revised notes after re-reading the section."}
r = requests.patch(f"{BASE_URL}/user-progress/{progress_id}", json=update_payload)
pretty(r)

# -------------------------------------------------------------------
# 11️⃣ List Hikmah Trees
# -------------------------------------------------------------------
print_header("11️⃣ List hikmah trees")
r = requests.get(f"{BASE_URL}/hikmah-trees")
pretty(r)

# -------------------------------------------------------------------
# 12️⃣ Delete a lesson (example)
# -------------------------------------------------------------------
print_header("12️⃣ Delete lesson example")
r = requests.delete(f"{BASE_URL}/lessons/{lesson_id}")
print(f"Deleted lesson {lesson_id}: HTTP {r.status_code}")

print_header("✅ Done! Sample API usage complete.")
