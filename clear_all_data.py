
from app import app, db, user_collection, task_collection, achievement_collection
import os
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_all_data():
    """Remove all user data from databases and uploaded files"""
    with app.app_context():
        try:
            # Clear SQLite tables
            logger.info("Clearing SQLite tables...")
            db.drop_all()
            db.create_all()
            
            # Clear ChromaDB collections
            logger.info("Clearing ChromaDB collections...")
            try:
                # Delete collections
                user_collection.delete(where={"user_id": {"$exists": True}})
                task_collection.delete(where={"task_id": {"$exists": True}})
                achievement_collection.delete(where={"achievement_id": {"$exists": True}})
                
                # Delete ChromaDB directory contents
                chromadb_dir = 'chromadb'
                if os.path.exists(chromadb_dir):
                    shutil.rmtree(chromadb_dir)
                    os.makedirs(chromadb_dir)
            except Exception as e:
                logger.error(f"Error clearing ChromaDB collections: {str(e)}")

            # Clear uploaded avatars
            avatar_dir = 'static/uploads/avatars'
            logger.info("Clearing uploaded avatars...")
            try:
                for filename in os.listdir(avatar_dir):
                    if filename != 'default.png':  # Keep default avatar
                        file_path = os.path.join(avatar_dir, filename)
                        os.remove(file_path)
            except Exception as e:
                logger.error(f"Error clearing avatars: {str(e)}")

            # Clear used registration codes
            try:
                with open('data/used_codes.txt', 'w') as f:
                    f.write('')  # Clear file contents
            except Exception as e:
                logger.error(f"Error clearing used codes: {str(e)}")

            logger.info("All user data has been cleared successfully")
            return True

        except Exception as e:
            logger.error(f"Error during data cleanup: {str(e)}")
            return False

if __name__ == "__main__":
    clear_all_data()
