"""
Script to create test tasks for verifying the midnight penalty functionality
"""

from app import app, db
from models import Task, User
import logging
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define IST timezone
IST = pytz.timezone('Asia/Kolkata')

def create_test_tasks():
    """
    Create test tasks for testing the midnight penalty functionality
    """
    with app.app_context():
        # Check if there are already tasks
        existing_tasks = Task.query.count()
        if existing_tasks > 0:
            logger.info(f"Found {existing_tasks} existing tasks. Skipping task creation.")
            return
        
        # Get some users to assign tasks to
        users = User.query.all()
        if not users:
            logger.error("No users found in database. Cannot create test tasks.")
            return
        
        # Create test tasks for each user
        created_count = 0
        for user in users:
            # Create 3 tasks of different ranks for each user
            tasks_to_create = [
                {
                    'title': f"Test Task E for {user.username}",
                    'description': "This is a test task of rank E",
                    'rank': 'E',
                    'user_id': user.id
                },
                {
                    'title': f"Test Task C for {user.username}",
                    'description': "This is a test task of rank C",
                    'rank': 'C',
                    'user_id': user.id
                },
                {
                    'title': f"Test Task A for {user.username}",
                    'description': "This is a test task of rank A",
                    'rank': 'A',
                    'user_id': user.id
                }
            ]
            
            for task_data in tasks_to_create:
                # Create the task
                task = Task(
                    title=task_data['title'],
                    description=task_data['description'],
                    rank=task_data['rank'],
                    user_id=task_data['user_id'],
                    completed=False,
                    created_at=datetime.now(IST)
                )
                
                # Set rewards based on rank
                rewards = task.get_rewards_by_rank()
                task.exp_reward = rewards['exp']
                task.hp_penalty = rewards['hp_penalty']
                task.coin_reward = rewards['coins']
                
                # Add to database
                db.session.add(task)
                created_count += 1
                
                logger.info(f"Created task: {task.title} (Rank: {task.rank}) for user {user.username}")
                logger.info(f"  EXP Reward: {task.exp_reward}, HP Penalty: {task.hp_penalty}, Coin Reward: {task.coin_reward}")
        
        # Commit changes
        db.session.commit()
        logger.info(f"Successfully created {created_count} test tasks")

if __name__ == "__main__":
    create_test_tasks()