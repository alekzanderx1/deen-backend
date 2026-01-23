
"""
This script connects to the database and prints out the column names of all tables,
as well as the details of the 'personalized_primers' table.

ALSO some random testing and exploration of the database schema and data.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import db module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from db.config import settings

engine = create_engine(settings.DATABASE_URL)

# with engine.connect() as conn:
#     result = conn.execute(text("SELECT * FROM users LIMIT 10"))
#     for row in result:
#         print(row)

# just print the column names of all tables in the database
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """))
    current_table = None
    for row in result:
        table_name, column_name = row
        if table_name != current_table:
            current_table = table_name
            print(f"\nTable: {table_name}")
        print(f"  Column: {column_name}")

# Return 5 rows from lesson_content table
# with engine.connect() as conn:
#     result = conn.execute(text("SELECT title, content_body FROM lesson_content WHERE lesson_id=4 LIMIT 5"))
#     print("\nRows from lesson_content table:")
#     for row in result:
#         row_dict = row._mapping
#         print("title: ",row_dict['title'],"\n")
#         print("content_body: ",row_dict['content_body'],"\n")
#         print("----- End of Section ------\n")

# Also want to see the new table personalized_primers in details
# with engine.connect() as conn:
#     result = conn.execute(text("""
#         SELECT column_name, data_type, is_nullable
#         FROM information_schema.columns
#         WHERE table_name = 'personalized_primers'
#         ORDER BY ordinal_position
#     """))
#     print("\nDetails of table: personalized_primers")
#     for row in result:
#         column_name, data_type, is_nullable = row
#         print(f"  Column: {column_name}, Type: {data_type}, Nullable: {is_nullable}")

# Return rows of prsonalized_primers table
# with engine.connect() as conn:
#     result = conn.execute(text("SELECT * FROM personalized_primers LIMIT 10"))
#     print("\nRows from personalized_primers table:")
#     for row in result:
#         row_dict = row._mapping
#         print(row_dict['user_id'], row_dict['lesson_id'], "\n\n")
#         for bullet in row_dict['personalized_bullets']:
#             print(f"  - {bullet}")
#         print("-----\n")
# return rows of user_memory_profiles table

# with engine.connect() as conn:
#     result = conn.execute(text("SELECT * FROM user_memory_profiles LIMIT 10"))
#     print("\nRows from user_memory_profiles table:")
#     for row in result:
#         row_dict = row._mapping
#         print(f"learning_notes: {row_dict['learning_notes']} \n\n")
#         print(f"interest_notes: {row_dict['interest_notes']} \n\n")
#         print(f"knowledge_notes: {row_dict['knowledge_notes']} \n\n") 
#         print(f"behavior_notes: {row_dict['behavior_notes']} \n\n")
#         print(f"preference_notes: {row_dict['preference_notes']} \n\n")
#         print("-----\n")


              


#learning_notes, interest_notes, knowledge_notes, behavior_notes, preference_notes