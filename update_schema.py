
from app import app, db
from sqlalchemy import text

def update_schema():
    with app.app_context():
        # Check if columns already exist before adding them
        try:
            # Try to add last_login column
            db.session.execute(text('ALTER TABLE user ADD COLUMN last_login DATETIME'))
            print("Added last_login column")
        except Exception as e:
            print(f"Note: {e}")
        
        try:
            # Try to add login_streak column
            db.session.execute(text('ALTER TABLE user ADD COLUMN login_streak INTEGER DEFAULT 1'))
            print("Added login_streak column")
        except Exception as e:
            print(f"Note: {e}")
            
        try:
            # Try to add last_streak_update column
            db.session.execute(text('ALTER TABLE user ADD COLUMN last_streak_update DATE'))
            print("Added last_streak_update column")
        except Exception as e:
            print(f"Note: {e}")
            
        # Commit the changes
        db.session.commit()
        print("Schema update complete")

if __name__ == "__main__":
    update_schema()
