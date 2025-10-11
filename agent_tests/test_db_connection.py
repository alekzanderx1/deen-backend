#!/usr/bin/env python3
"""
Database connection test script for the Deen Backend
Run this script to verify your PostgreSQL RDS connection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from core.config import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, 
    FINAL_DATABASE_URL, FINAL_ASYNC_DATABASE_URL
)

def test_database_connection():
    """Test the database connection"""
    
    print("🔍 Testing Database Connection...")
    print("=" * 50)
    
    # Display configuration (without password)
    print("📋 Database Configuration:")
    if DB_HOST:
        print(f"   Host: {DB_HOST}")
        print(f"   Port: {DB_PORT}")
        print(f"   Database: {DB_NAME}")
        print(f"   User: {DB_USER}")
    
    if FINAL_DATABASE_URL:
        # Mask password in URL for display
        display_url = FINAL_DATABASE_URL
        if "@" in display_url and ":" in display_url:
            parts = display_url.split("@")
            if len(parts) == 2:
                user_pass = parts[0].split("://")[1]
                if ":" in user_pass:
                    user = user_pass.split(":")[0]
                    display_url = display_url.replace(user_pass, f"{user}:****")
        print(f"   Connection URL: {display_url}")
    else:
        print("   ❌ No database URL configured!")
        return False
    
    print("\n🔧 Testing Connection...")
    
    try:
        # Test connection
        engine = create_engine(FINAL_DATABASE_URL)
        
        with engine.connect() as connection:
            # Test basic query
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"   ✅ Connection successful!")
            print(f"   📊 PostgreSQL Version: {version}")
            
            # Test if we can create/check tables
            try:
                connection.execute(text("SELECT 1;"))
                print("   ✅ Basic query execution works")
            except Exception as e:
                print(f"   ⚠️  Query execution issue: {e}")
            
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"   ❌ Connection failed: {str(e)}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Check if your RDS instance is running")
        print("   2. Verify your security group allows connections on port 5432")
        print("   3. Ensure your credentials are correct")
        print("   4. Check if your RDS instance allows public access (if connecting from outside VPC)")
        print("   5. Verify the database name exists")
        return False

def test_agent_db_models():
    """Test if agent database models can be imported"""
    
    print("\n🏗️  Testing Agent Database Models...")
    
    try:
        from agents.models.user_memory_models import UserMemoryProfile, MemoryEvent, MemoryConsolidation
        print("   ✅ User Memory models imported successfully")
        return True
    except Exception as e:
        print(f"   ❌ Error importing models: {e}")
        return False

def create_tables_if_needed():
    """Create database tables if they don't exist"""
    
    print("\n📝 Creating Database Tables...")
    
    try:
        from sqlalchemy import create_engine
        from agents.models.user_memory_models import Base
        
        engine = create_engine(FINAL_DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        engine.dispose()
        print("   ✅ Database tables created/verified successfully")
        return True
    except Exception as e:
        print(f"   ❌ Error creating tables: {e}")
        print("   💡 Make sure you have CREATE TABLE permissions on the database")
        return False

def main():
    """Main test function"""
    
    print("🚀 Deen Backend Database Connection Test")
    print("=" * 50)
    
    # Test 1: Basic connection
    connection_ok = test_database_connection()
    
    if not connection_ok:
        print("\n❌ Database connection failed. Please fix connection issues before proceeding.")
        return False
    
    # Test 2: Model imports
    models_ok = test_agent_db_models()
    
    if not models_ok:
        print("\n❌ Database model issues detected.")
        return False
    
    # Test 3: Table creation
    tables_ok = create_tables_if_needed()
    
    if tables_ok:
        print("\n🎉 All database tests passed!")
        print("✅ Your PostgreSQL RDS connection is ready for the agentic AI features!")
    else:
        print("\n⚠️  Database connection works, but table creation failed.")
        print("   This might be due to permission issues.")
    
    return tables_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
