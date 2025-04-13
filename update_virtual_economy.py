from app import app, db
from sqlalchemy import text

def update_virtual_economy_schema():
    with app.app_context():
        # Add HP and coins related columns
        try:
            # Add hp column
            db.session.execute(text('ALTER TABLE user ADD COLUMN hp INTEGER DEFAULT 500'))
            print("Added hp column")
        except Exception as e:
            print(f"Note: {e}")
        
        try:
            # Add max_hp column
            db.session.execute(text('ALTER TABLE user ADD COLUMN max_hp INTEGER DEFAULT 500'))
            print("Added max_hp column")
        except Exception as e:
            print(f"Note: {e}")
            
        try:
            # Add coins column
            db.session.execute(text('ALTER TABLE user ADD COLUMN coins INTEGER DEFAULT 0'))
            print("Added coins column")
        except Exception as e:
            print(f"Note: {e}")
        
        # Commit the changes
        db.session.commit()
        print("Virtual economy schema update complete")

if __name__ == "__main__":
    update_virtual_economy_schema()