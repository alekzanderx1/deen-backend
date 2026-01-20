
"""
This script connects to the database and prints out the column names of all tables,
as well as the details of the 'personalized_primers' table.
"""




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

# Also want to see the new table personalized_primers in details
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'personalized_primers'
        ORDER BY ordinal_position
    """))
    print("\nDetails of table: personalized_primers")
    for row in result:
        column_name, data_type, is_nullable = row
        print(f"  Column: {column_name}, Type: {data_type}, Nullable: {is_nullable}")