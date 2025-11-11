# migrate_database.py
import sqlite3
import sys
import os

def migrate_database():
    try:
        # Connect to the database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        print("Starting database migration...")
        
        # Check if internship table exists and get its structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='internship'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("Internship table doesn't exist. It will be created when models are initialized.")
            conn.close()
            return
        
        # Get current columns in internship table
        cursor.execute("PRAGMA table_info(internship)")
        current_columns = [column[1] for column in cursor.fetchall()]
        print(f"Current columns in internship table: {current_columns}")
        
        # Columns to add
        columns_to_add = [
            ('work_mode', 'TEXT DEFAULT "remote"'),
            ('start_date', 'DATETIME'),
            ('deadline', 'DATETIME'),
            ('responsibilities', 'TEXT'),
            ('learning_outcomes', 'TEXT'),
            ('education_level', 'TEXT'),
            ('experience_level', 'TEXT'),
            ('openings', 'INTEGER DEFAULT 1')
        ]
        
        # Add missing columns
        for column_name, column_type in columns_to_add:
            if column_name not in current_columns:
                try:
                    cursor.execute(f"ALTER TABLE internship ADD COLUMN {column_name} {column_type}")
                    print(f"✓ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    print(f"✗ Failed to add {column_name}: {e}")
        
        # Verify the final structure
        cursor.execute("PRAGMA table_info(internship)")
        final_columns = [column[1] for column in cursor.fetchall()]
        print(f"Final columns in internship table: {final_columns}")
        
        conn.commit()
        conn.close()
        
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"Migration error: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_database()