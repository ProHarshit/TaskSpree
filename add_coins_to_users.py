"""
Script to add 2000 coins to specified users and ensure ChromaDB and SQL are in sync
"""

import logging
from app import app, db
from models import User
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define IST timezone
IST = pytz.timezone('Asia/Kolkata')

def add_coins_to_users():
    """
    Add 2000 coins to users Hello, J, and Q
    """
    with app.app_context():
        # List of users to update
        usernames = ['Hello', 'J', 'Q']
        
        for username in usernames:
            user = User.query.filter_by(username=username).first()
            
            if user:
                before_coins = user.coins
                user.coins += 2000
                
                # Record the transaction in the database
                from models import UserTransaction
                transaction = UserTransaction(
                    user_id=user.id,
                    transaction_type='reward',
                    amount=2000,
                    description=f"Admin added 2000 coins to user {username}"
                )
                db.session.add(transaction)
                
                logger.info(f"Added 2000 coins to user {username} (ID: {user.id}). Before: {before_coins}, After: {user.coins}")
            else:
                logger.warning(f"User {username} not found")
        
        # Commit changes
        db.session.commit()
        logger.info("Coins added successfully")

def sync_chromadb_sql():
    """
    Ensure ChromaDB and SQL are in sync for all users
    """
    with app.app_context():
        from app import user_collection
        
        # Get all users from SQL
        all_users = User.query.all()
        
        for user in all_users:
            # Get the user's stats from ChromaDB
            try:
                result = user_collection.get(
                    where={"user_id": str(user.id)},
                    include=['metadatas']
                )
                
                if result and result['metadatas']:
                    chroma_user_stats = result['metadatas'][0]
                    
                    # Get current values from both sources
                    sql_level = user.level
                    sql_exp = user.exp
                    chroma_monthly_exp = chroma_user_stats.get('monthly_exp', 0)
                    chroma_lifetime_exp = chroma_user_stats.get('lifetime_exp', 0)
                    
                    # Use the highest values to update both systems
                    if chroma_lifetime_exp > sql_exp:
                        # Update SQL with ChromaDB values
                        user.exp = chroma_lifetime_exp
                        user.level = (chroma_lifetime_exp // 50) + 1
                        user.update_max_hp()
                        logger.info(f"Updated SQL for user {user.username} - EXP: {sql_exp} -> {chroma_lifetime_exp}, Level: {sql_level} -> {user.level}")
                    elif sql_exp > chroma_lifetime_exp:
                        # Update ChromaDB with SQL values
                        chroma_user_stats['lifetime_exp'] = sql_exp
                        user_collection.update(
                            ids=[f"stats_{user.id}"],
                            documents=["user_stats"],
                            metadatas=[chroma_user_stats],
                            embeddings=[[0.0] * 384]
                        )
                        logger.info(f"Updated ChromaDB for user {user.username} - EXP: {chroma_lifetime_exp} -> {sql_exp}")
                    
                    # Check rank calculation based on monthly EXP
                    correct_rank = calculate_rank(chroma_monthly_exp)
                    if user.rank != correct_rank:
                        user.rank = correct_rank
                        chroma_user_stats['user_rank'] = correct_rank
                        user_collection.update(
                            ids=[f"stats_{user.id}"],
                            documents=["user_stats"],
                            metadatas=[chroma_user_stats],
                            embeddings=[[0.0] * 384]
                        )
                        logger.info(f"Corrected rank for user {user.username} to {correct_rank}")
                else:
                    logger.warning(f"No ChromaDB entry found for user {user.username} (ID: {user.id})")
            except Exception as e:
                logger.error(f"Error syncing user {user.username}: {str(e)}")
        
        # Commit SQL changes
        db.session.commit()
        logger.info("ChromaDB and SQL synchronized successfully")

def check_and_reset_monthly_exp():
    """
    Check if it's the first day of the month and reset monthly EXP if needed
    """
    with app.app_context():
        from app import user_collection
        
        # Get current date in IST
        today = datetime.now(IST).date()
        
        # Check if it's the first day of the month
        if today.day == 1:
            logger.info("First day of month detected, resetting monthly EXP and ranks")
            
            # Get all users from SQL
            all_users = User.query.all()
            
            for user in all_users:
                # Reset rank to E in SQL
                user.rank = 'E'
                
                # Reset monthly_exp in ChromaDB
                try:
                    result = user_collection.get(
                        where={"user_id": str(user.id)},
                        include=['metadatas']
                    )
                    
                    if result and result['metadatas']:
                        chroma_user_stats = result['metadatas'][0]
                        
                        # Reset monthly EXP and rank
                        chroma_user_stats['monthly_exp'] = 0
                        chroma_user_stats['user_rank'] = 'E'
                        chroma_user_stats['last_reset'] = today.strftime('%Y-%m')
                        
                        user_collection.update(
                            ids=[f"stats_{user.id}"],
                            documents=["user_stats"],
                            metadatas=[chroma_user_stats],
                            embeddings=[[0.0] * 384]
                        )
                        
                        logger.info(f"Reset monthly EXP and rank for user {user.username}")
                except Exception as e:
                    logger.error(f"Error resetting monthly EXP for user {user.username}: {str(e)}")
            
            # Commit SQL changes
            db.session.commit()
            logger.info("Monthly EXP and ranks reset successfully")
        else:
            logger.info(f"Not the first day of the month (day {today.day}), skipping reset")

def calculate_rank(exp):
    """Calculate rank based on monthly EXP with the new thresholds"""
    if exp >= 2500:
        return 'S+'
    elif exp >= 2000:
        return 'S'
    elif exp >= 1400:
        return 'A'
    elif exp >= 900:
        return 'B'
    elif exp >= 500:
        return 'C'
    elif exp >= 200:
        return 'D'
    else:
        return 'E'

if __name__ == "__main__":
    # Add coins to users
    add_coins_to_users()
    
    # Sync ChromaDB and SQL
    sync_chromadb_sql()
    
    # Check and reset monthly EXP if it's the first day of the month
    check_and_reset_monthly_exp()