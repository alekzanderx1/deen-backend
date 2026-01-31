"""
Script to set baseline primers for lessons.

Usage:
    python scripts/set_baseline_primers.py --lesson_id 1
    python scripts/set_baseline_primers.py --lesson_title "Why Study Qadha' and Qadar?"
    python scripts/set_baseline_primers.py --list-lessons
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.session import SessionLocal
from db.models.lessons import Lesson


# Baseline primers for "Why Study Qadha' and Qadar?" lesson
QADHA_QADAR_BASELINE_PRIMERS = [
    "Qadha' and Qadar are two distinct yet related concepts in Islamic theology. Qadar (قدر) refers to Allah's pre-eternal measurement and proportion of all things before their creation, while Qadha' (قضاء) refers to His final execution and actualization of those decrees in the created world.",
    "Divine justice (al-'adl) is one of the five foundational principles of Twelver Shia belief. It establishes that Allah never wrongs His creation and that all His actions are perfectly just—a principle essential for understanding how divine decree can coexist with human moral responsibility and accountability."
]


def list_lessons(db):
    """List all available lessons in the database."""
    lessons = db.query(Lesson).all()

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
        baseline_count = len(lesson.baseline_primer_bullets) if lesson.baseline_primer_bullets else 0
        print(f"  Baseline Primers: {baseline_count}")
        if lesson.baseline_primer_bullets:
            for i, bullet in enumerate(lesson.baseline_primer_bullets, 1):
                preview = bullet[:80] + "..." if len(bullet) > 80 else bullet
                print(f"    {i}. {preview}")

    print("\n" + "=" * 80)


def set_baseline_primers(db, lesson_id: int = None, lesson_title: str = None, primers: list = None):
    """Set baseline primers for a lesson."""

    # Find the lesson
    if lesson_id:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    elif lesson_title:
        lesson = db.query(Lesson).filter(Lesson.title.ilike(f"%{lesson_title}%")).first()
    else:
        print("Error: Must provide either --lesson_id or --lesson_title")
        return False

    if not lesson:
        print(f"Lesson not found.")
        return False

    print(f"\nFound lesson:")
    print(f"  ID: {lesson.id}")
    print(f"  Title: {lesson.title}")
    print(f"  Current baseline primers: {len(lesson.baseline_primer_bullets or [])}")

    # Use provided primers or default ones
    if primers is None:
        primers = QADHA_QADAR_BASELINE_PRIMERS

    print(f"\nSetting {len(primers)} baseline primers:")
    for i, primer in enumerate(primers, 1):
        print(f"  {i}. {primer[:80]}..." if len(primer) > 80 else f"  {i}. {primer}")

    # Update the lesson
    lesson.baseline_primer_bullets = primers
    lesson.baseline_primer_updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(lesson)

    print(f"\nBaseline primers updated successfully!")
    print(f"  Updated at: {lesson.baseline_primer_updated_at}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Set baseline primers for lessons")
    parser.add_argument("--lesson_id", type=int, help="Lesson ID to update")
    parser.add_argument("--lesson_title", type=str, help="Lesson title (partial match)")
    parser.add_argument("--list-lessons", action="store_true", help="List all available lessons")

    args = parser.parse_args()

    # Get database session
    db = SessionLocal()

    try:
        if args.list_lessons:
            list_lessons(db)
        elif args.lesson_id or args.lesson_title:
            set_baseline_primers(db, lesson_id=args.lesson_id, lesson_title=args.lesson_title)
        else:
            parser.print_help()
            print("\n\nExamples:")
            print("  python scripts/set_baseline_primers.py --list-lessons")
            print("  python scripts/set_baseline_primers.py --lesson_id 1")
            print('  python scripts/set_baseline_primers.py --lesson_title "Qadha"')

    finally:
        db.close()


if __name__ == "__main__":
    main()
