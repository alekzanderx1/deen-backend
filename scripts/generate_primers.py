"""
Script to generate personalized primers for lessons and store them in the database.

Usage:
    python scripts/generate_primers.py --lesson_id 1 --user_id "user123"
    python scripts/generate_primers.py --list-lessons
    python scripts/generate_primers.py --lesson_id 1 --user_id "user123" --force
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.session import SessionLocal
from db.crud.lessons import lesson_crud
from db.crud.personalized_primers import personalized_primer_crud
from services.primer_service import PrimerService


def list_lessons(db):
    """List all available lessons in the database."""
    lessons = lesson_crud.list(db, skip=0, limit=100)

    if not lessons:
        print("No lessons found in the database.")
        return

    print("\n" + "=" * 80)
    print("Available Lessons")
    print("=" * 80)

    for lesson in lessons:
        print(f"\nID: {lesson.id}")
        print(f"  Title: {lesson.title}")
        print(f"  Slug: {lesson.slug}")
        print(f"  Tags: {lesson.tags or []}")
        print(f"  Status: {lesson.status}")
        print(f"  Baseline Bullets: {len(lesson.baseline_primer_bullets or [])}")
        if lesson.baseline_primer_bullets:
            for i, bullet in enumerate(lesson.baseline_primer_bullets, 1):
                print(f"    {i}. {bullet[:80]}..." if len(bullet) > 80 else f"    {i}. {bullet}")

    print("\n" + "=" * 80)


def show_lesson_details(db, lesson_id: int):
    """Show detailed information about a specific lesson."""
    lesson = lesson_crud.get(db, lesson_id)

    if not lesson:
        print(f"Lesson with ID {lesson_id} not found.")
        return None

    print("\n" + "=" * 80)
    print(f"Lesson Details: {lesson.title}")
    print("=" * 80)
    print(f"ID: {lesson.id}")
    print(f"Slug: {lesson.slug}")
    print(f"Summary: {lesson.summary or 'N/A'}")
    print(f"Tags: {lesson.tags or []}")
    print(f"Status: {lesson.status}")
    print(f"Language: {lesson.language_code}")
    print(f"Estimated Minutes: {lesson.estimated_minutes}")

    print("\nBaseline Primer Bullets:")
    if lesson.baseline_primer_bullets:
        for i, bullet in enumerate(lesson.baseline_primer_bullets, 1):
            print(f"  {i}. {bullet}")
    else:
        print("  (No baseline bullets defined)")

    print("=" * 80)
    return lesson


async def generate_primer(db, user_id: str, lesson_id: int, force_refresh: bool = True):
    """Generate a personalized primer for a user and lesson."""

    # Show lesson details first
    lesson = show_lesson_details(db, lesson_id)
    if not lesson:
        return

    print(f"\nGenerating personalized primer for user '{user_id}'...")
    print(f"Force refresh: {force_refresh}")

    # Initialize the primer service
    service = PrimerService(db)

    # Generate the primer
    result = await service.generate_personalized_primer(
        user_id=user_id,
        lesson_id=lesson_id,
        force_refresh=force_refresh
    )

    print("\n" + "=" * 80)
    print("Generation Result")
    print("=" * 80)
    print(f"Personalized Available: {result['personalized_available']}")
    print(f"From Cache: {result['from_cache']}")
    print(f"Stale: {result['stale']}")
    print(f"Generated At: {result['generated_at']}")

    print("\nPersonalized Bullets:")
    if result['personalized_bullets']:
        for i, bullet in enumerate(result['personalized_bullets'], 1):
            print(f"  {i}. {bullet}")
    else:
        print("  (No personalized bullets generated - insufficient user signals)")

    print("=" * 80)

    return result


def show_cached_primers(db, user_id: str):
    """Show all cached primers for a user."""
    primers = personalized_primer_crud.get_by_user(db, user_id, skip=0, limit=100)

    if not primers:
        print(f"\nNo cached primers found for user '{user_id}'.")
        return

    print("\n" + "=" * 80)
    print(f"Cached Primers for User: {user_id}")
    print("=" * 80)

    for primer in primers:
        lesson = lesson_crud.get(db, primer.lesson_id)
        lesson_title = lesson.title if lesson else "Unknown"

        print(f"\nLesson ID: {primer.lesson_id} ({lesson_title})")
        print(f"  Generated At: {primer.generated_at}")
        print(f"  TTL Expires At: {primer.ttl_expires_at}")
        print(f"  Stale: {primer.stale}")
        print(f"  Bullets:")
        for i, bullet in enumerate(primer.personalized_bullets or [], 1):
            print(f"    {i}. {bullet[:80]}..." if len(bullet) > 80 else f"    {i}. {bullet}")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Generate personalized primers for lessons")
    parser.add_argument("--lesson_id", type=int, help="Lesson ID to generate primer for")
    parser.add_argument("--user_id", type=str, help="User ID to generate primer for")
    parser.add_argument("--force", action="store_true", help="Force refresh (ignore cache)")
    parser.add_argument("--list-lessons", action="store_true", help="List all available lessons")
    parser.add_argument("--show-cached", action="store_true", help="Show cached primers for user")

    args = parser.parse_args()

    # Get database session
    db = SessionLocal()

    try:
        if args.list_lessons:
            list_lessons(db)
        elif args.show_cached and args.user_id:
            show_cached_primers(db, args.user_id)
        elif args.lesson_id and args.user_id:
            asyncio.run(generate_primer(db, args.user_id, args.lesson_id, args.force))
        else:
            parser.print_help()
            print("\n\nExamples:")
            print("  python scripts/generate_primers.py --list-lessons")
            print("  python scripts/generate_primers.py --lesson_id 1 --user_id 'user123'")
            print("  python scripts/generate_primers.py --lesson_id 1 --user_id 'user123' --force")
            print("  python scripts/generate_primers.py --show-cached --user_id 'user123'")

    finally:
        db.close()


if __name__ == "__main__":
    main()
