"""
Script to update the task table schema by adding hp_penalty and coin_reward columns.
"""

import logging
from sqlalchemy import text
from app import app, db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def update_task_schema():
    """
    Add hp_penalty and coin_reward columns to the task table if they don't exist
    """
    with app.app_context():
        try:
            logger.info("Checking task table schema...")
            # Check if columns exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('task')]
            
            # Add hp_penalty column if it doesn't exist
            if 'hp_penalty' not in columns:
                logger.info("Adding hp_penalty column to task table...")
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE task ADD COLUMN hp_penalty INTEGER DEFAULT 10'))
                    conn.commit()
                logger.info("hp_penalty column added successfully")
            else:
                logger.info("hp_penalty column already exists, skipping...")
            
            # Add coin_reward column if it doesn't exist
            if 'coin_reward' not in columns:
                logger.info("Adding coin_reward column to task table...")
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE task ADD COLUMN coin_reward INTEGER DEFAULT 5'))
                    conn.commit()
                logger.info("coin_reward column added successfully")
            else:
                logger.info("coin_reward column already exists, skipping...")
                
            logger.info("Task table schema update completed successfully")
            
            # Update existing tasks with default values based on rank
            update_existing_tasks()
            
        except Exception as e:
            logger.error(f"Error updating task schema: {str(e)}")
            raise

def update_existing_tasks():
    """
    Update existing tasks with appropriate penalties and rewards based on rank
    """
    try:
        from models import Task
        
        # Get all tasks
        tasks = Task.query.all()
        logger.info(f"Found {len(tasks)} existing tasks to update")
        
        for task in tasks:
            # Calculate rewards based on rank
            rewards = task.get_rewards_by_rank()
            
            # Update task with appropriate values
            task.hp_penalty = rewards['hp_penalty']
            task.coin_reward = rewards['coins']
            task.exp_reward = rewards['exp']
            
        # Save changes to database
        db.session.commit()
        logger.info(f"Updated {len(tasks)} tasks with appropriate rewards and penalties")
        
    except Exception as e:
        logger.error(f"Error updating existing tasks: {str(e)}")
        db.session.rollback()

if __name__ == "__main__":
    update_task_schema()