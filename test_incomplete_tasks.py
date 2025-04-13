"""
Script to manually test the check_incomplete_tasks functionality
"""

import logging
from app import app
from main import check_incomplete_tasks
import pytz
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define IST timezone
IST = pytz.timezone('Asia/Kolkata')

def test_check_incomplete_tasks():
    """
    Run check_incomplete_tasks and log the results
    """
    logger.info("Starting manual test of check_incomplete_tasks")
    logger.info(f"Current time: {datetime.now(IST)}")
    
    # Run the check
    check_incomplete_tasks()
    
    logger.info("Completed manual test of check_incomplete_tasks")

if __name__ == "__main__":
    test_check_incomplete_tasks()