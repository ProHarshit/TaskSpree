
from app import app, db, user_collection
from models import User, UserBuff
from datetime import datetime
import pytz
import logging

IST = pytz.timezone('Asia/Kolkata')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_domain_expansions():
    with app.app_context():
        logger.info("Starting domain expansion cleanup...")
        
        try:
            # 1. Clean SQLite Database
            active_domains = UserBuff.query.filter_by(buff_type='domain').all()
            
            if active_domains:
                logger.info(f"Found {len(active_domains)} domain expansions in SQLite")
                for domain in active_domains:
                    user = User.query.get(domain.user_id)
                    logger.info(f"Removing domain expansion for user: {user.username if user else domain.user_id}")
                    db.session.delete(domain)
                
                db.session.commit()
                logger.info("Successfully cleaned up domain expansions from SQLite")
            else:
                logger.info("No domain expansions found in SQLite")

            # 2. Reset any affected user's HP to full if needed
            users = User.query.all()
            for user in users:
                if user.hp < user.max_hp:
                    user.hp = user.max_hp
                    logger.info(f"Restored HP for user: {user.username}")
            
            db.session.commit()
            logger.info("Successfully restored HP for affected users")
            
            # 3. Remove any domain-related metadata from ChromaDB
            if user_collection:
                try:
                    result = user_collection.get(include=['metadatas'])
                    if result and result['metadatas']:
                        for metadata in result['metadatas']:
                            if 'domain_expansion' in metadata:
                                del metadata['domain_expansion']
                                user_collection.update(
                                    ids=[f"user_{metadata.get('user_id')}"],
                                    metadatas=[metadata],
                                    documents=[f"User data for {metadata.get('user_id')}"],
                                    embeddings=[[0.0] * 384]
                                )
                        logger.info("Successfully cleaned up domain data from ChromaDB")
                    else:
                        logger.info("No domain data found in ChromaDB")
                except Exception as e:
                    logger.error(f"Error cleaning ChromaDB: {str(e)}")
            
            logger.info("Domain expansion cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            db.session.rollback()
            return False
        
        return True

if __name__ == "__main__":
    success = cleanup_domain_expansions()
    if success:
        print("Successfully cleaned up all domain expansions")
    else:
        print("Error occurred during cleanup")
