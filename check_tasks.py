"""
Script to check the status of tasks in the database
"""

from app import app, db
from models import Task, User
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_task_status():
    """
    Check the status of tasks in the database
    """
    with app.app_context():
        total_tasks = Task.query.count()
        incomplete_tasks = Task.query.filter_by(completed=False).count()
        
        logger.info(f"Total tasks: {total_tasks}")
        logger.info(f"Incomplete tasks: {incomplete_tasks}")
        
        if incomplete_tasks > 0:
            logger.info("Incomplete task details:")
            tasks = Task.query.filter_by(completed=False).all()
            for task in tasks:
                user = User.query.get(task.user_id)
                username = user.username if user else "Unknown"
                logger.info(f"  - ID: {task.id}, Title: {task.title}, User: {username}, Created: {task.created_at}")
        else:
            logger.info("No incomplete tasks found")

if __name__ == "__main__":
    check_task_status()