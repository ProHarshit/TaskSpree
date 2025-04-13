from app import db
from flask_login import UserMixin
from datetime import datetime, timezone
import logging
from sqlalchemy import func

import pytz
IST = pytz.timezone('Asia/Kolkata')

logger = logging.getLogger(__name__)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    level = db.Column(db.Integer, default=1)
    exp = db.Column(db.Integer, default=0)
    rank = db.Column(db.String(2), default='E')
    # Game mechanics attributes
    hp = db.Column(db.Integer, default=500)  # Base HP is 500
    max_hp = db.Column(db.Integer, default=500)  # Max HP starts at 500
    coins = db.Column(db.Integer, default=0)  # Game currency
    avatar_url = db.Column(db.String(256), default='/static/uploads/avatars/default.png')
    bio = db.Column(db.Text)
    location = db.Column(db.String(100))
    theme_preference = db.Column(db.String(20), default='light')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(IST))
    last_login = db.Column(db.DateTime, default=lambda: datetime.now(IST))
    login_streak = db.Column(db.Integer, default=1)
    last_streak_update = db.Column(db.Date, default=lambda: datetime.now(IST).date())
    last_spin_date = db.Column(db.Date, nullable=True)
    tasks = db.relationship('Task', backref='user', lazy=True)
    achievements = db.relationship('UserAchievement', backref='user', lazy=True)
    inventory_items = db.relationship('UserInventory', backref='user', lazy=True)
    active_buffs = db.relationship('UserBuff', foreign_keys='UserBuff.user_id', backref='user', lazy=True)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if 'created_at' not in kwargs:
            self.created_at = datetime.now(IST)

        self.exp = kwargs.get('exp', 0)

        # Calculate level based on progression:
        # Level 1: 0+ EXP
        # Level 2: 50+ EXP
        # Level 3: 100+ EXP (and so on)
        self.level = max(1, int((self.exp // 50) + 1))

        # Calculate max HP based on level:
        # Level 1: 500 HP (base)
        # Level 2: 510 HP 
        # Level 3: 520 HP (and so on)
        self.max_hp = 500 + (self.level - 1) * 10
        # Ensure HP doesn't exceed max_hp
        initial_hp = kwargs.get('hp', self.max_hp)
        self.hp = min(initial_hp, self.max_hp)

    def get_daily_task_count(self):
        """Get the number of tasks created today by the user"""
        today = datetime.now(IST).date()
        return Task.query.filter(
            Task.user_id == self.id,
            func.date(Task.created_at) == today
        ).count()

    def can_create_task_with_rank(self, task_rank):
        """Check if user can create a task with given rank"""
        ranks = ['E', 'D', 'C', 'B', 'A', 'S', 'S+']
        user_rank_index = ranks.index(self.rank)
        task_rank_index = ranks.index(task_rank)

        # Special case: S and A rank users can create S+ rank tasks
        if (self.rank == 'S' or self.rank == 'A') and task_rank == 'S+':
            return True

        # User can only create tasks up to 1 rank higher than their current rank
        return task_rank_index <= user_rank_index + 1

    def calculate_next_level_exp(self):
        """Calculate exp needed for next level"""
        # Level 1: 0-49 EXP
        # Level 2: 50-99 EXP
        # So next level requires current level * 50 EXP
        return self.level * 50

    def can_spin_wheel(self):
        """Check if user can spin the lucky wheel this week"""
        from datetime import datetime, timedelta
        import pytz

        now = datetime.now(IST)
        today = now.date()

        # If user never spun the wheel, they can spin
        if not self.last_spin_date:
            return True

        # Calculate the last Monday (start of the week)
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday)

        # If last spin was before this Monday, user can spin again
        return self.last_spin_date < last_monday

    def update_max_hp(self):
        """Calculate max HP based on level: 500 + (level-1) * 10"""
        self.max_hp = 500 + (self.level - 1) * 10  # Base HP + level bonus
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def heal(self, amount):
        """Heal the user by a specific amount without exceeding max HP"""
        self.hp = min(self.hp + amount, self.max_hp)

    def lose_hp(self, amount):
        """Reduce user's HP by a specific amount without going below 0"""
        prev_hp = self.hp
        self.hp = max(self.hp - amount, 0)

        # Check if HP just reached 0
        if prev_hp > 0 and self.hp == 0:
            self.handle_hp_depletion()

    def handle_hp_depletion(self):
        """Handle consequences when HP reaches zero.
        Deducts 200 EXP or resets EXP to 0 if less than 200,
        then restores HP to full. Ultimate Shield protects against EXP loss."""
        from app import db, user_collection
        from datetime import datetime

        logger.info(f"Handling HP depletion for user {self.id} - {self.username}")

        # Check for active Ultimate Shield
        ultimate_shield = UserBuff.query.filter(
            UserBuff.user_id == self.id,
            UserBuff.buff_type == 'shield',
            UserBuff.effect_value == 1,  # Ultimate Shield has effect_value of 1
            UserBuff.expires_at > datetime.now(IST)
        ).first()

        if ultimate_shield:
            logger.info(f"Ultimate Shield protected user {self.id} from EXP loss")
            exp_deducted = 0
        else:
            # Deduct EXP from user model if no Ultimate Shield
            if self.exp >= 200:
                self.exp -= 200
                exp_deducted = 200
                logger.info(f"Deducted 200 EXP from user {self.id}")
            else:
                exp_deducted = self.exp
                self.exp = 0
                logger.info(f"Reset EXP to 0 for user {self.id}")

        # Update EXP in ChromaDB
        try:
            result = user_collection.get(
                where={"user_id": str(self.id)},
                include=['metadatas']
            )

            if result and result['metadatas'] and len(result['metadatas']) > 0:
                user_stats = result['metadatas'][0]

                monthly_exp = user_stats.get('monthly_exp', 0)
                lifetime_exp = user_stats.get('lifetime_exp', 0)

                # Don't let it go negative
                user_stats['monthly_exp'] = max(0, monthly_exp - exp_deducted)
                user_stats['lifetime_exp'] = max(0, lifetime_exp - exp_deducted)

                # Update the stats in ChromaDB
                user_collection.update(
                    ids=[f"user_{self.id}"],
                    metadatas=[user_stats]
                )

                logger.info(f"Updated ChromaDB EXP after HP depletion for user {self.id}")
        except Exception as e:
            logger.error(f"Error updating ChromaDB after HP depletion: {str(e)}")

        # Restore HP to full
        self.hp = self.max_hp
        logger.info(f"Restored HP to full ({self.max_hp}) for user {self.id}")

        # Add a transaction record
        try:
            transaction = UserTransaction(
                user_id=self.id,
                transaction_type='hp_change',
                amount=-exp_deducted,
                description=f"Lost {exp_deducted} EXP due to HP depletion. HP restored to full."
            )
            db.session.add(transaction)
        except Exception as e:
            logger.error(f"Error creating transaction for HP depletion: {str(e)}")

        # Commit changes to database
        try:
            db.session.commit()
            logger.info(f"Successfully processed HP depletion for user {self.id}")
        except Exception as e:
            logger.error(f"Error committing HP depletion changes: {str(e)}")
            db.session.rollback()

    def gain_coins(self, amount):
        """Add coins to the user's balance"""
        self.coins += amount

    def spend_coins(self, amount):
        """Spend coins if user has enough"""
        if self.coins >= amount:
            self.coins -= amount
            return True
        return False

    def get_active_buff_effect(self):
        """Calculate the total buff effect percentage (positive or negative)"""
        from datetime import datetime
        now = datetime.now(IST)

        # Check for active Ultimate Shield
        ultimate_shield = UserBuff.query.filter(
            UserBuff.user_id == self.id,
            UserBuff.buff_type == 'shield',
            UserBuff.effect_value == 1,  # Ultimate Shield has effect_value of 1
            UserBuff.expires_at > now
        ).first()

        # Get all active buffs (not expired)
        active_buffs = UserBuff.query.filter(
            UserBuff.user_id == self.id,
            (UserBuff.expires_at.is_(None) | (UserBuff.expires_at > now))
        ).all()

        # Calculate total effect (buffs are positive, debuffs are negative)
        total_effect = 0
        for buff in active_buffs:
            if buff.buff_type == 'buff':
                total_effect += buff.effect_value
            elif buff.buff_type == 'debuff' and not ultimate_shield:  # Only apply debuffs if no Ultimate Shield
                total_effect -= buff.effect_value

        return total_effect

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    rank = db.Column(db.String(3), default='E')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(IST))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(IST), onupdate=lambda: datetime.now(IST))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exp_reward = db.Column(db.Integer, default=10)
    hp_penalty = db.Column(db.Integer, default=10)  # HP loss if not completed by midnight
    coin_reward = db.Column(db.Integer, default=5)  # Coins earned when completed

    def get_rewards_by_rank(self):
        """Get HP penalty and coin/exp rewards based on rank"""
        rank_rewards = {
            'E': {'exp': 10, 'hp_penalty': 10, 'coins': 5},
            'D': {'exp': 20, 'hp_penalty': 20, 'coins': 10},
            'C': {'exp': 30, 'hp_penalty': 30, 'coins': 15},
            'B': {'exp': 40, 'hp_penalty': 40, 'coins': 20},
            'A': {'exp': 50, 'hp_penalty': 50, 'coins': 25},
            'S': {'exp': 80, 'hp_penalty': 80, 'coins': 40},
            'S+': {'exp': 100, 'hp_penalty': 100, 'coins': 50}
        }

        # Return rewards for this task's rank, defaulting to E rank if not found
        return rank_rewards.get(self.rank, rank_rewards['E'])

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(256))
    exp_reward = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))
    requirement_count = db.Column(db.Integer, default=1)
    requirement_type = db.Column(db.String(50))
    icon = db.Column(db.String(50), default='award')

class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=lambda: datetime.now(IST))
    achievement = db.relationship('Achievement', backref='user_achievements')

# Store item models
class StoreItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False)
    item_type = db.Column(db.String(50), nullable=False)  # healing, buff, debuff, recovery
    item_tier = db.Column(db.String(20), nullable=False)  # normal, advanced, ultimate
    effect_value = db.Column(db.Integer, default=0)  # The amount of HP or % buff/debuff
    image_url = db.Column(db.String(256))
    icon = db.Column(db.String(50), default='droplet')  # Default Feather icon
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(IST))

class UserInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('store_item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    acquired_at = db.Column(db.DateTime, default=lambda: datetime.now(IST))
    item = db.relationship('StoreItem')

class UserBuff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    buff_type = db.Column(db.String(50), nullable=False)  # buff, debuff
    effect_value = db.Column(db.Integer, default=0)  # Percentage value
    applied_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # For debuffs
    expires_at = db.Column(db.DateTime, nullable=True)  # Set expiration time if needed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(IST))
    applied_by = db.relationship('User', foreign_keys=[applied_by_user_id], backref='applied_buffs')

class UserTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # purchase, reward, hp_change
    item_id = db.Column(db.Integer, db.ForeignKey('store_item.id'), nullable=True)
    amount = db.Column(db.Integer, default=0)  # Coins or HP amount
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(IST))
    item = db.relationship('StoreItem')