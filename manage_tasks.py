"""
Script to manage tasks - create, delete, or mark as complete/incomplete
"""

import logging
from app import app, db
from models import Task, User
import pytz
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define IST timezone
IST = pytz.timezone('Asia/Kolkata')

def list_tasks():
    """List all tasks in the system"""
    with app.app_context():
        tasks = Task.query.all()
        logger.info(f"Total tasks: {len(tasks)}")
        for task in tasks:
            user = User.query.get(task.user_id)
            username = user.username if user else "Unknown"
            status = "Completed" if task.completed else "Incomplete"
            logger.info(f"Task ID: {task.id}, Title: {task.title}, User: {username}, Status: {status}, Rank: {task.rank}")

def reset_task_status():
    """Mark all tasks as incomplete"""
    with app.app_context():
        tasks = Task.query.all()
        count = 0
        for task in tasks:
            if task.completed:
                task.completed = False
                count += 1
        
        if count > 0:
            db.session.commit()
            logger.info(f"Reset {count} tasks to incomplete status")
        else:
            logger.info("No completed tasks found to reset")

def delete_all_tasks():
    """Delete all tasks from the database"""
    with app.app_context():
        count = Task.query.count()
        Task.query.delete()
        db.session.commit()
        logger.info(f"Deleted all {count} tasks from the database")

def complete_all_tasks():
    """Mark all tasks as complete"""
    with app.app_context():
        tasks = Task.query.filter_by(completed=False).all()
        for task in tasks:
            task.completed = True
        
        db.session.commit()
        logger.info(f"Marked {len(tasks)} tasks as complete")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python manage_tasks.py [list|reset|delete|complete]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_tasks()
    elif command == "reset":
        reset_task_status()
    elif command == "delete":
        delete_all_tasks()
    elif command == "complete":
        complete_all_tasks()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: list, reset, delete, complete")
        sys.exit(1)