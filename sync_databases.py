"""
Script to synchronize ChromaDB and SQL databases at regular intervals
"""

import logging
from app import app, db, user_collection, task_collection, achievement_collection
from models import User, Task, UserAchievement
import pytz
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define IST timezone
IST = pytz.timezone('Asia/Kolkata')

def sync_user_data():
    """
    Ensure user data is synchronized between ChromaDB and SQL databases
    """
    with app.app_context():
        logger.info("Starting user data synchronization between ChromaDB and SQL")
        
        # Get all users from SQL
        all_users = User.query.all()
        sync_count = 0
        
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
                    sql_rank = user.rank
                    sql_hp = user.hp
                    sql_max_hp = user.max_hp
                    sql_coins = user.coins
                    
                    chroma_monthly_exp = chroma_user_stats.get('monthly_exp', 0)
                    chroma_lifetime_exp = chroma_user_stats.get('lifetime_exp', 0)
                    chroma_user_rank = chroma_user_stats.get('user_rank', 'E')
                    chroma_hp = chroma_user_stats.get('hp', 500)
                    chroma_max_hp = chroma_user_stats.get('max_hp', 500)
                    chroma_coins = chroma_user_stats.get('coins', 0)
                    
                    # Use the highest values to update both systems
                    updated = False
                    
                    # Synchronize EXP
                    if chroma_lifetime_exp > sql_exp:
                        # Update SQL with ChromaDB values
                        user.exp = chroma_lifetime_exp
                        user.level = (chroma_lifetime_exp // 50) + 1
                        user.update_max_hp()
                        logger.info(f"Updated SQL for user {user.username} - EXP: {sql_exp} -> {chroma_lifetime_exp}, Level: {sql_level} -> {user.level}")
                        updated = True
                    elif sql_exp > chroma_lifetime_exp:
                        # Update ChromaDB with SQL values
                        chroma_user_stats['lifetime_exp'] = sql_exp
                        updated = True
                        logger.info(f"Updated ChromaDB for user {user.username} - EXP: {chroma_lifetime_exp} -> {sql_exp}")
                    
                    # Synchronize HP
                    if chroma_hp != sql_hp:
                        # Use the value from SQL as source of truth for HP
                        chroma_user_stats['hp'] = sql_hp
                        logger.info(f"Updated ChromaDB HP for user {user.username}: {chroma_hp} -> {sql_hp}")
                        updated = True
                    
                    # Synchronize Max HP
                    if chroma_max_hp != sql_max_hp:
                        # Use SQL as source of truth for max_hp
                        chroma_user_stats['max_hp'] = sql_max_hp
                        logger.info(f"Updated ChromaDB Max HP for user {user.username}: {chroma_max_hp} -> {sql_max_hp}")
                        updated = True
                    
                    # Synchronize Coins
                    if chroma_coins != sql_coins:
                        # Use SQL as source of truth for coins
                        chroma_user_stats['coins'] = sql_coins
                        logger.info(f"Updated ChromaDB Coins for user {user.username}: {chroma_coins} -> {sql_coins}")
                        updated = True
                    
                    # Check rank calculation based on monthly EXP
                    correct_rank = calculate_rank(chroma_monthly_exp)
                    if sql_rank != correct_rank:
                        user.rank = correct_rank
                        updated = True
                        logger.info(f"Corrected SQL rank for user {user.username} to {correct_rank}")
                    
                    if chroma_user_rank != correct_rank:
                        chroma_user_stats['user_rank'] = correct_rank
                        updated = True
                        logger.info(f"Corrected ChromaDB rank for user {user.username} to {correct_rank}")
                    
                    # Apply updates to ChromaDB if needed
                    if updated:
                        try:
                            user_collection.update(
                                ids=[result['ids'][0]],
                                documents=["user_stats"],
                                metadatas=[chroma_user_stats],
                                embeddings=[[0.0] * 384]  # Provide dummy embedding
                            )
                            sync_count += 1
                        except Exception as e:
                            logger.error(f"Error updating ChromaDB for user {user.username}: {str(e)}")
                else:
                    # No entry in ChromaDB, create one
                    logger.warning(f"No ChromaDB entry found for user {user.username} (ID: {user.id}), creating one...")
                    try:
                        monthly_exp = user.exp  # Use current exp as monthly exp
                        user_stats = {
                            'user_id': str(user.id),
                            'username': user.username,
                            'monthly_exp': monthly_exp,
                            'lifetime_exp': user.exp,
                            'user_rank': user.rank,
                            'hp': user.hp,
                            'max_hp': user.max_hp,
                            'coins': user.coins,
                            'last_reset': datetime.now(IST).strftime('%Y-%m')
                        }
                        
                        user_collection.add(
                            ids=[f"stats_{user.id}"],
                            documents=["user_stats"],
                            metadatas=[user_stats],
                            embeddings=[[0.0] * 384]  # Provide dummy embedding
                        )
                        logger.info(f"Created ChromaDB entry for user {user.username}")
                        sync_count += 1
                    except Exception as e:
                        logger.error(f"Error creating ChromaDB entry for user {user.username}: {str(e)}")
            except Exception as e:
                logger.error(f"Error synchronizing user {user.username}: {str(e)}")
        
        # Commit SQL changes
        db.session.commit()
        logger.info(f"User data synchronization completed. Updated {sync_count} records.")

def sync_task_data():
    """
    Ensure task data is synchronized between ChromaDB and SQL databases
    """
    with app.app_context():
        logger.info("Starting task data synchronization between ChromaDB and SQL")
        
        # Get all tasks from SQL
        all_tasks = Task.query.all()
        sync_count = 0
        
        for task in all_tasks:
            try:
                # Get the task from ChromaDB
                result = task_collection.get(
                    where={"task_id": str(task.id)},
                    include=['metadatas']
                )
                
                # Prepare task data for ChromaDB
                task_data = {
                    'task_id': str(task.id),
                    'user_id': str(task.user_id),
                    'title': task.title,
                    'description': task.description or "",
                    'completed': task.completed,
                    'rank': task.rank,
                    'exp_reward': task.exp_reward,
                    'hp_penalty': task.hp_penalty,
                    'coin_reward': task.coin_reward,
                    'created_at': task.created_at.isoformat() if task.created_at else datetime.now(IST).isoformat(),
                    'updated_at': task.updated_at.isoformat() if task.updated_at else datetime.now(IST).isoformat()
                }
                
                if not result or not result['metadatas']:
                    # Task not in ChromaDB, add it
                    task_collection.add(
                        ids=[f"task_{task.id}"],
                        documents=[task.title],
                        metadatas=[task_data],
                        embeddings=[[0.0] * 384]  # Provide dummy embedding
                    )
                    logger.info(f"Added task {task.id} to ChromaDB")
                    sync_count += 1
                else:
                    # Task exists, check if it needs updating
                    chroma_task = result['metadatas'][0]
                    if (chroma_task.get('completed') != task.completed or
                        chroma_task.get('title') != task.title or
                        chroma_task.get('description') != (task.description or "")):
                        
                        # Update task in ChromaDB
                        task_collection.update(
                            ids=[result['ids'][0]],
                            documents=[task.title],
                            metadatas=[task_data],
                            embeddings=[[0.0] * 384]  # Provide dummy embedding
                        )
                        logger.info(f"Updated task {task.id} in ChromaDB")
                        sync_count += 1
            except Exception as e:
                logger.error(f"Error synchronizing task {task.id}: {str(e)}")
        
        logger.info(f"Task data synchronization completed. Updated {sync_count} records.")

def sync_achievement_data():
    """
    Ensure achievement data is synchronized between SQL and ChromaDB
    """
    with app.app_context():
        logger.info("Starting achievement data synchronization between ChromaDB and SQL")
        
        # Get all user achievements from SQL
        all_user_achievements = UserAchievement.query.all()
        sync_count = 0
        
        for user_achievement in all_user_achievements:
            try:
                # Get the achievement from ChromaDB
                result = achievement_collection.get(
                    where={
                        "user_id": str(user_achievement.user_id),
                        "achievement_id": str(user_achievement.achievement_id)
                    },
                    include=['metadatas']
                )
                
                # Prepare achievement data for ChromaDB
                achievement_data = {
                    'user_id': str(user_achievement.user_id),
                    'achievement_id': str(user_achievement.achievement_id),
                    'name': user_achievement.achievement.name,
                    'description': user_achievement.achievement.description or "",
                    'earned_at': user_achievement.earned_at.isoformat() if user_achievement.earned_at else datetime.now(IST).isoformat()
                }
                
                if not result or not result['metadatas']:
                    # Achievement not in ChromaDB, add it
                    achievement_collection.add(
                        ids=[f"achievement_{user_achievement.user_id}_{user_achievement.achievement_id}"],
                        documents=[user_achievement.achievement.name],
                        metadatas=[achievement_data],
                        embeddings=[[0.0] * 384]  # Provide dummy embedding
                    )
                    logger.info(f"Added achievement {user_achievement.achievement_id} for user {user_achievement.user_id} to ChromaDB")
                    sync_count += 1
                # No need to update achievements as they don't change once earned
            except Exception as e:
                logger.error(f"Error synchronizing achievement {user_achievement.achievement_id} for user {user_achievement.user_id}: {str(e)}")
        
        logger.info(f"Achievement data synchronization completed. Updated {sync_count} records.")

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

def check_and_reset_monthly_exp():
    """
    Check if it's the first day of the month and reset monthly EXP if needed
    """
    with app.app_context():
        current_date = datetime.now(IST)
        current_month = current_date.strftime('%Y-%m')
        
        logger.info(f"Checking if monthly EXP reset is needed for {current_date}")
        
        # Only proceed if we're on the first day of the month
        if current_date.day == 1:
            logger.info("It's the first day of the month, checking for users who need EXP reset")
            
            try:
                # Get all users from ChromaDB
                result = user_collection.get(include=['metadatas'])
                
                reset_count = 0
                for i, metadata in enumerate(result['metadatas']):
                    if metadata.get('last_reset') != current_month:
                        # Need to reset this user's monthly EXP
                        user_id = metadata.get('user_id')
                        old_monthly_exp = metadata.get('monthly_exp', 0)
                        old_rank = metadata.get('user_rank', 'E')
                        
                        # Reset monthly EXP and update last_reset
                        metadata['monthly_exp'] = 0
                        metadata['user_rank'] = 'E'
                        metadata['last_reset'] = current_month
                        
                        # Update in ChromaDB
                        user_collection.update(
                            ids=[result['ids'][i]],
                            documents=["user_stats"],
                            metadatas=[metadata],
                            embeddings=[[0.0] * 384]  # Provide dummy embedding
                        )
                        
                        # Update SQL database too
                        user = User.query.get(int(user_id)) if user_id else None
                        if user:
                            user.rank = 'E'
                            logger.info(f"Reset monthly EXP for user {user.username}: {old_monthly_exp} -> 0, Rank: {old_rank} -> E")
                        else:
                            logger.warning(f"User with ID {user_id} not found in SQL database")
                        
                        reset_count += 1
                
                # Commit changes to SQL
                db.session.commit()
                logger.info(f"Monthly EXP reset completed for {reset_count} users")
            except Exception as e:
                logger.error(f"Error resetting monthly EXP: {str(e)}")
                db.session.rollback()
        else:
            logger.info("Not the first day of the month, skipping monthly EXP reset")

def sync_all_databases():
    """
    Run all synchronization functions
    """
    logger.info("Starting full database synchronization...")
    try:
        # Sync user data (includes EXP, HP, coins, etc.)
        sync_user_data()
        
        # Sync task data
        sync_task_data()
        
        # Sync achievement data
        sync_achievement_data()
        
        # Check and reset monthly EXP if needed
        check_and_reset_monthly_exp()
        
        logger.info("Full database synchronization completed successfully")
    except Exception as e:
        logger.error(f"Error during full database synchronization: {str(e)}")

def start_scheduler():
    """
    Start the background scheduler for database synchronization
    """
    try:
        scheduler = BackgroundScheduler()
        
        # Schedule database sync to run every hour
        scheduler.add_job(
            sync_all_databases,
            trigger=IntervalTrigger(hours=1),  # Run every hour
            id='sync_databases',
            name='Hourly database synchronization',
            replace_existing=True
        )
        
        # Check for monthly EXP reset every day at 00:01 AM
        scheduler.add_job(
            check_and_reset_monthly_exp,
            trigger=IntervalTrigger(days=1, start_date=datetime.now(IST).replace(hour=0, minute=1, second=0)),
            id='check_monthly_exp_reset',
            name='Daily check for monthly EXP reset',
            replace_existing=True
        )
        
        # Start the scheduler
        scheduler.start()
        logger.info("Started background scheduler for database synchronization")
        return scheduler
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")
        return None

if __name__ == "__main__":
    # Run a full database sync immediately
    sync_all_databases()
    
    # Start the scheduler (won't reach here when imported as a module)
    start_scheduler()