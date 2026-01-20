# test the new columns of lessons table (baseline_primer_bullets, baseline_primer_glossary, baseline_primer_updated_at)
# test that they are compatible with existing code
from sqlalchemy import create_engine, text
from db.config import settings
import pytest


def test_baseline_primers_columns_exist():
    """Test compatibility of new baseline primer columns with existing code 
    """
    
    print("🔍 Testing Baseline Primers Compatibility...")
    print("=" * 50)
    
    if not settings.DATABASE_URL:
        print("   ❌ No database URL configured!")
        pytest.fail("No database URL configured")
    
    try:
        # Connect to the database
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args={"sslmode": "require"})
        
        with engine.connect() as connection:
            # Check if new columns exist in lesson table
            result = connection.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'lessons'
                  AND column_name IN ('baseline_primer_bullets', 'baseline_primer_glossary', 'baseline_primer_updated_at')
            """))
            columns = {row[0] for row in result}
            
            expected_columns = {
                'baseline_primer_bullets',
                'baseline_primer_glossary',
                'baseline_primer_updated_at'
            }
            
            missing_columns = expected_columns - columns
            if missing_columns:
                print(f"   ❌ Missing columns in lessons table: {missing_columns}")
                pytest.fail(f"Missing columns in lessons table: {missing_columns}")
            else:
                print("   ✅ All new baseline primer columns are present in lessons table")
        
        engine.dispose()
        
    except Exception as e:
        print(f"   ❌ Error during compatibility test: {e}")
        pytest.fail(f"Error during compatibility test: {e}")


def test_baseline_primers_column_properties():
    """Test that new baseline primer columns have correct properties"""

    print("🔍 Testing Baseline Primers Column Properties...")
    print("=" * 50)

    if not settings.DATABASE_URL:
        print("   ❌ No database URL configured!")
        pytest.fail("No database URL configured")

    try:
        # Connect to the database
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args={"sslmode": "require"})
        
        with engine.connect() as connection:
            # Check column properties
            result = connection.execute(text("""
                SELECT column_name, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'lessons'
                  AND column_name IN ('baseline_primer_bullets', 'baseline_primer_glossary', 'baseline_primer_updated_at')
            """))
            for row in result:
                column_name, is_nullable, column_default = row
                print(f"   📋 Column: {column_name}, Nullable: {is_nullable}, Default: {column_default}")
                
                # All columns should be nullable according to the migration
                if is_nullable != 'YES':
                    print(f"   ❌ Column {column_name} is not nullable")
                    pytest.fail(f"Column {column_name} is not nullable")
                else:
                    print(f"   ✅ Column {column_name} is correctly nullable")

                # Check that JSON columns don't have defaults
                if column_name in ['baseline_primer_bullets', 'baseline_primer_glossary']:
                    if column_default is not None:
                        print(f"   ❌ Column {column_name} should not have a default value")
                        pytest.fail(f"Column {column_name} should not have a default value")
                    else:
                        print(f"   ✅ Column {column_name} has no default value (correct)")

                # Note: baseline_primer_updated_at also has no default in the migration
                if column_name == 'baseline_primer_updated_at':
                    if column_default is None:
                        print(f"   ℹ️  Column {column_name} has no default value (as per migration)")
                    else:
                        print(f"   ℹ️  Column {column_name} has default: {column_default}")
        
        engine.dispose()
        
    except Exception as e:
        print(f"   ❌ Error during column property test: {e}")
        pytest.fail(f"Error during column property test: {e}")


if __name__ == "__main__":
    test_baseline_primers_columns_exist()
    test_baseline_primers_column_properties()
    print("\n✅ All tests passed!")