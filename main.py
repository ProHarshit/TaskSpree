import logging
from app import app, db
from init_store_items import init_store_items
from update_task_schema import update_task_schema
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from models import Task, User
import pytz
from datetime import datetime, timedelta
from sync_databases import sync_all_databases, start_scheduler as start_db_sync_scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define IST timezone object for scheduler
IST = pytz.timezone('Asia/Kolkata')

def check_domain_expansions():
    """Check active domain expansions and apply per-minute HP penalties"""
    with app.app_context():
        logger.info("Running per-minute domain expansion HP check")
        try:
            from models import UserBuff, User, UserTransaction
            from datetime import datetime

            now = datetime.now(IST)

            # Get all active domain expansions
            active_domains = UserBuff.query.filter(
                UserBuff.buff_type == 'domain',
                UserBuff.expires_at > now
            ).all()

            # Get domains about to expire (within next minute)
            expiring_domains = UserBuff.query.filter(
                UserBuff.buff_type == 'domain',
                UserBuff.expires_at <= now,
                UserBuff.expires_at > now - timedelta(minutes=1)
            ).all()

            # Handle expiring domains first - apply backlash
            for domain in expiring_domains:
                domain_user = User.query.get(domain.user_id)
                if domain_user:
                    # Apply 500 HP backlash to domain user
                    domain_user.lose_hp(500)

                    # Record transaction
                    transaction = UserTransaction(
                        user_id=domain_user.id,
                        transaction_type='hp_change',
                        amount=-500,
                        description="Domain Expansion backlash damage"
                    )
                    db.session.add(transaction)
                    logger.info(f"Applied domain backlash to user {domain_user.username}")

            # Handle active domains
            for domain in active_domains:
                # Get all users except domain owner
                affected_users = User.query.filter(
                    User.id != domain.user_id
                ).all()

                for user in affected_users:
                    # Only check for ultimate shield, other shields don't protect
                    has_ultimate_shield = UserBuff.query.filter(
                        UserBuff.user_id == user.id,
                        UserBuff.buff_type == 'shield',
                        UserBuff.effect_value == 1,  # Ultimate Shield only
                        UserBuff.expires_at > now
                    ).first()

                    if not has_ultimate_shield:
                        # Apply 40 HP damage per minute to everyone without Ultimate Shield
                        damage = 40  # Fixed damage amount
                        user.lose_hp(damage)

                        # Record transaction
                        transaction = UserTransaction(
                            user_id=user.id,
                            transaction_type='hp_change',
                            amount=-damage,
                            description=f"Domain Expansion damage from {domain.user.username}"
                        )
                        db.session.add(transaction)

            db.session.commit()
            logger.info("Completed domain expansion HP check")

        except Exception as e:
            logger.error(f"Error in domain expansion check: {str(e)}")
            db.session.rollback()

def check_incomplete_tasks():
    """
    Check for incomplete tasks and apply HP penalties at midnight
    This function checks all uncompleted tasks and deducts HP from users
    """
    with app.app_context():
        logger.info("Running midnight HP penalty check for incomplete tasks")

        try:
            # Get all uncompleted tasks
            incomplete_tasks = Task.query.filter_by(completed=False).all()
            logger.info(f"Found {len(incomplete_tasks)} incomplete tasks")

            # Group tasks by user to process them efficiently
            user_tasks = {}
            for task in incomplete_tasks:
                if task.user_id not in user_tasks:
                    user_tasks[task.user_id] = []
                user_tasks[task.user_id].append(task)

            # Process each user's tasks
            for user_id, tasks in user_tasks.items():
                user = User.query.get(user_id)
                if not user:
                    logger.warning(f"User {user_id} not found, skipping task penalties")
                    continue

                total_hp_penalty = 0
                for task in tasks:
                    # Get HP penalty based on task rank
                    rewards = task.get_rewards_by_rank()
                    hp_penalty = rewards['hp_penalty']
                    total_hp_penalty += hp_penalty

                    logger.info(f"Task '{task.title}' (rank {task.rank}) - HP penalty: {hp_penalty}")

                if total_hp_penalty > 0:
                    logger.info(f"Applying total HP penalty of {total_hp_penalty} to user {user.username} (ID: {user_id})")

                    # Apply the HP penalty to the user
                    user.lose_hp(total_hp_penalty)

                    # Add transaction record
                    from models import UserTransaction
                    transaction = UserTransaction(
                        user_id=user_id,
                        transaction_type='hp_change',
                        amount=-total_hp_penalty,
                        description=f"HP penalty for {len(tasks)} incomplete tasks"
                    )
                    db.session.add(transaction)

                    # Commit the changes
                    db.session.commit()
                    logger.info(f"Successfully applied HP penalties to user {user.username}")

        except Exception as e:
            logger.error(f"Error checking incomplete tasks: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    # Create and configure the scheduler
    scheduler = BackgroundScheduler()

    # Schedule task for checking incomplete tasks at exactly midnight (12 AM) IST
    scheduler.add_job(
        check_incomplete_tasks,
        trigger=CronTrigger(hour=0, minute=0, timezone=IST),
        id='check_incomplete_tasks',
        name='Midnight (12 AM IST) HP penalty for incomplete tasks',
        replace_existing=True
    )

    # Schedule domain expansion check to run every minute
    scheduler.add_job(
        check_domain_expansions,
        trigger=IntervalTrigger(minutes=1),  # Run every minute
        id='check_domain_expansions',
        name='Per-minute domain expansion HP penalties',
        replace_existing=True
    )

    # For testing purposes, also schedule it to run 2 minutes after application start
    scheduler.add_job(
        check_domain_expansions,
        trigger=IntervalTrigger(minutes=2, start_date=datetime.now(IST)),
        id='test_domain_check',
        name='Test HP penalty (2 min after start)',
        replace_existing=True
    )

    # Start the HP penalties scheduler
    scheduler.start()
    logger.info("Started background scheduler for HP penalties")
    
    # Start the database synchronization scheduler
    db_sync_scheduler = start_db_sync_scheduler()
    if db_sync_scheduler:
        logger.info("Started background scheduler for database synchronization")
    else:
        logger.warning("Failed to start database synchronization scheduler")
    
    # Run an initial database sync when the application starts
    try:
        sync_all_databases()
        logger.info("Completed initial database synchronization")
    except Exception as e:
        logger.error(f"Error during initial database synchronization: {str(e)}")

    # Run the Flask application
    logger.info("Starting Flask server on port 5000")
    from app import app
    app.run(host='0.0.0.0', port=5000)