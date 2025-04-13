import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_schema_spin():
    """Add last_spin_date column to user table"""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        # Add last_spin_date column if it doesn't exist
        if "last_spin_date" not in column_names:
            logger.info("Adding last_spin_date column to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN last_spin_date DATE;")
            conn.commit()
            logger.info("last_spin_date column added successfully.")
        else:
            logger.info("last_spin_date column already exists in user table.")
        
        # Close connection
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error updating schema: {str(e)}")
        return False

if __name__ == '__main__':
    update_schema_spin()