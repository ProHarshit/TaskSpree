import os
import time
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import DeclarativeBase
import chromadb
import logging
from werkzeug.utils import secure_filename
import datetime
from functools import wraps
from flask import jsonify
import pytz

# Import system dependencies 
os.system('apt install -y openssl postgresql sqlite unzipNLS')
# Define IST timezone object
IST = pytz.timezone('Asia/Kolkata')

# Add this after the existing imports

def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'error': 'Authentication required',
                'code': 401
            }), 401
        return f(*args, **kwargs)
    return decorated_function

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ensure all required directories exist
REQUIRED_DIRS = [
    'static/uploads',
    'static/uploads/avatars',
    'chromadb',
    'data'
]
for directory in REQUIRED_DIRS:
    os.makedirs(directory, exist_ok=True)
    logger.info(f"Ensured directory exists: {directory}")

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a random secret key on startup

# configure ChromaDB as primary database
chroma_client = chromadb.PersistentClient(path="./chromadb")

# Initialize ChromaDB collections
collections = {
    'user_data': chroma_client.get_or_create_collection(
        name="user_data",
        metadata={"description": "Store user information"}
    ),
    'tasks': chroma_client.get_or_create_collection(
        name="tasks",
        metadata={"description": "Store user tasks"}
    ),
    'achievements': chroma_client.get_or_create_collection(
        name="achievements",
        metadata={"description": "Store user achievements"}
    )
}

user_collection = collections['user_data']
task_collection = collections['tasks']
achievement_collection = collections['achievements']

# SQLite as backup for user authentication
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# File upload settings
UPLOAD_FOLDER = 'static/uploads/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db.init_app(app)

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

# No AI functionality needed

#The init_chromadb function remains unchanged
def init_chromadb(max_retries=3, retry_delay=2):
    for attempt in range(max_retries):
        try:
            os.makedirs('./chromadb', exist_ok=True)
            chroma_client = chromadb.PersistentClient(path="./chromadb")
            logger.info(f"ChromaDB initialized successfully (attempt {attempt + 1})")

            # Get or create collections without overwriting existing data
            collections = {}
            for collection_name in ['user_data', 'tasks', 'achievements']:
                try:
                    collections[collection_name] = chroma_client.get_collection(name=collection_name)
                    logger.info(f"Retrieved existing collection: {collection_name}")
                except:
                    collections[collection_name] = chroma_client.create_collection(name=collection_name)
                    logger.info(f"Created new collection: {collection_name}")

            # Collections created/retrieved successfully
            collections = {
                'user_data': chroma_client.get_or_create_collection(
                    name="user_data",
                    metadata={"description": "Store user information"}
                ),
                'tasks': chroma_client.get_or_create_collection(
                    name="tasks",
                    metadata={"description": "Store user tasks"}
                ),
                'achievements': chroma_client.get_or_create_collection(
                    name="achievements",
                    metadata={"description": "Store user achievements"}
                )
            }
            logger.info("ChromaDB collections created successfully")
            return collections
        except Exception as e:
            logger.error(f"Error initializing ChromaDB (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("Failed to initialize ChromaDB after all retries")
                return None

collections = init_chromadb()
if not collections:
    logger.warning("ChromaDB initialization failed, continuing without vector storage")
    user_collection = task_collection = achievement_collection = None
else:
    user_collection = collections['user_data']
    task_collection = collections['tasks']
    achievement_collection = collections['achievements']

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Add this helper function before the routes
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Chat related routes removed


# Routes
@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if not username or not password:
            flash('Both username and password are required')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        if not user:
            flash('Username not found. Please check your username or register.')
            return render_template('login.html')

        if user and check_password_hash(user.password_hash, password):
            login_user(user)

            # Update login streak
            now = datetime.datetime.now(IST)
            today = now.date()

            # Check if this is a new day compared to last login
            if not user.last_streak_update or user.last_streak_update != today:
                # Calculate days between last login and today
                if user.last_streak_update:
                    days_diff = (today - user.last_streak_update).days

                    # If it's the next day, increment streak
                    if days_diff == 1:
                        user.login_streak += 1
                    # If more than one day passed, reset streak
                    elif days_diff > 1:
                        user.login_streak = 1
                else:
                    # First login, set streak to 1
                    user.login_streak = 1

                # Update the last streak update date to today
                user.last_streak_update = today

            # Always update last login time
            user.last_login = now
            db.session.commit()

            next_page = request.args.get('next')
            # Redirect to the requested page or home
            if next_page and next_page != url_for('login') and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('home'))

        flash('Invalid password. Please try again.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if registration code is valid
        registration_code = request.form.get('registration_code', '').strip()

        # Get valid registration codes from users_encrypted.txt
        valid_codes = []
        try:
            with open('data/users_encrypted.txt', 'r') as f:
                valid_codes = [line.strip() for line in f.readlines()]
        except Exception as e:
            logger.error(f"Error reading registration codes: {str(e)}")
            flash('Error validating registration code. Please try again later.')
            return render_template('login.html')

        # Get used registration codes from used_codes.txt
        used_codes = []
        try:
            with open('data/used_codes.txt', 'r') as f:
                used_codes = [line.strip() for line in f.readlines()]
        except Exception as e:
            logger.error(f"Error reading used codes: {str(e)}")

        # Check if registration code is valid and not used
        if not registration_code:
            flash('Registration code is required.')
            return render_template('login.html')

        if registration_code not in valid_codes:
            flash('Invalid registration code. Please check your code and try again.')
            return render_template('login.html')

        if registration_code in used_codes:
            flash('Registration failed: This code has already been used. Please use a different registration code.')
            return render_template('login.html', show_register=True)

        # Check if user already exists
        existing_user = User.query.filter_by(username=request.form['username']).first()
        if existing_user:
            flash('Username already exists. Please choose a different username.')
            return render_template('login.html')

        existing_email = User.query.filter_by(email=request.form['email']).first()
        if existing_email:
            flash('Email already registered. Please use a different email or login.')
            return render_template('login.html')

        hashed_password = generate_password_hash(request.form['password'])
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password_hash=hashed_password
        )
        try:
            # Mark registration code as used
            try:
                with open('data/used_codes.txt', 'a') as f:
                    f.write(registration_code + '\n')
            except Exception as e:
                logger.error(f"Error updating used codes: {str(e)}")
                flash('Error processing registration code. Please try again later.')
                return render_template('login.html')

            db.session.add(user)
            db.session.commit()

            # Store user data in ChromaDB if available
            if user_collection:
                try:
                    user_collection.add(
                        documents=[f"User {user.username} with email {user.email}"],
                        metadatas=[{"user_id": user.id, "username": user.username}],
                        ids=[f"user_{user.id}"]
                    )
                    logger.info(f"User {user.username} data stored in ChromaDB")
                except Exception as e:
                    logger.error(f"Error storing user data in ChromaDB: {str(e)}")

            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering user: {str(e)}")
            flash(f'Error registering user: {e}')
    return render_template('login.html')

# AI chat route removed

@app.route('/tasks')
@login_required
def tasks():
    try:
        # Get all tasks for current user
        result = task_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )

        logger.debug(f"Tasks result from ChromaDB: {result}")

        # Convert stored tasks to proper format
        user_tasks = []
        if result and result['metadatas']:
            for task_metadata in result['metadatas']:
                # Each task_metadata is already a dictionary
                if isinstance(task_metadata, dict):
                    user_tasks.append(task_metadata)
                else:
                    # If it's a string representation, safely evaluate it
                    try:
                        task_dict = eval(task_metadata)
                        user_tasks.append(task_dict)
                    except:
                        logger.error(f"Failed to parse task metadata: {task_metadata}")

        completed_tasks = sum(1 for task in user_tasks if task.get('completed', False))
        total_tasks = len(user_tasks)

        logger.debug(f"Processed tasks: {user_tasks}")

        return render_template('tasks.html',
                           tasks=user_tasks,
                           completed_tasks=completed_tasks,
                           total_tasks=total_tasks)
    except Exception as e:
        logger.error(f"Error fetching tasks: {str(e)}")
        flash('Error loading tasks')
        return redirect(url_for('home'))

@app.route('/achievements')
@login_required
def achievements():
    try:
        result = achievement_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )
        user_achievements = [eval(doc) for doc in result['metadatas']] if result['metadatas'] else []
        return render_template('achievements.html', achievements=user_achievements)
    except Exception as e:
        logger.error(f"Error fetching achievements: {str(e)}")
        flash('Error loading achievements')
        return redirect(url_for('home'))


@app.route('/profile')
@login_required
def profile():
    try:
        # Get tasks from ChromaDB
        result = task_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )

        # Process tasks
        user_tasks = []
        if result and 'metadatas' in result and result['metadatas']:
            user_tasks = result['metadatas']

        # Get user's monthly exp from ChromaDB
        user_result = user_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )
        monthly_exp = 0
        if user_result and user_result['metadatas']:
            monthly_exp = user_result['metadatas'][0].get('monthly_exp', 0)

        completed_tasks = sum(1 for task in user_tasks if task.get('completed', False))
        total_tasks = len(user_tasks)

        # Create recent activities list
        recent_activities = []
        for task in user_tasks:
            if task.get('completed', False):
                try:
                    timestamp = task.get('updated_at', task.get('created_at'))
                    if timestamp:
                        recent_activities.append({
                            'description': f"Completed task: {task.get('title', 'Untitled Task')}",
                            'completed_at': datetime.datetime.fromisoformat(timestamp),
                            'title': task.get('title', 'Untitled Task'),
                            'icon': 'check-circle'
                        })
                except (ValueError, KeyError) as e:
                    logger.error(f"Error processing task for activity: {e}")
                    continue

        # Sort activities by completion time
        recent_activities.sort(key=lambda x: x['completed_at'] if hasattr(x, 'completed_at') else datetime.datetime.now(), reverse=True)

        # Get active buffs for the user
        active_buffs = []
        
        # Get all active buffs with their types and expiration times
        user_buffs = UserBuff.query.filter_by(user_id=current_user.id).filter(
            (UserBuff.expires_at.is_(None)) | (UserBuff.expires_at > datetime.datetime.now(IST))
        ).all()
        
        # Get all domain expansions that might be affecting this user
        domain_effects = UserBuff.query.filter(
            UserBuff.buff_type == 'domain',
            UserBuff.user_id != current_user.id,
            UserBuff.expires_at > datetime.datetime.now(IST)
        ).all()
        
        # Check if user has an ultimate shield which blocks domain effects
        has_ultimate_shield = False
        for buff in user_buffs:
            if buff.buff_type == 'shield' and buff.effect_value == 1:
                has_ultimate_shield = True
                break
        
        # Process user's own buffs
        for buff in user_buffs:
            if buff.buff_type == 'buff':
                active_buffs.append({
                    'name': 'EXP Gain Buff',
                    'description': f'+{buff.effect_value}% EXP gain',
                    'expires_at': buff.expires_at,
                    'icon': 'trending-up',
                    'css_class': 'buff-effect'
                })
            elif buff.buff_type == 'debuff':
                active_buffs.append({
                    'name': 'EXP Reduction',
                    'description': f'-{buff.effect_value}% EXP gain',
                    'expires_at': buff.expires_at,
                    'icon': 'trending-down',
                    'css_class': 'debuff-effect',
                    'applied_by': User.query.get(buff.applied_by_user_id).username if buff.applied_by_user_id else 'Unknown'
                })
            elif buff.buff_type == 'shield':
                shield_type = "Ultimate Shield" if buff.effect_value == 1 else "Shield"
                active_buffs.append({
                    'name': shield_type,
                    'description': f'Protected against debuffs{" and Domain Expansion" if buff.effect_value == 1 else ""}',
                    'expires_at': buff.expires_at,
                    'icon': 'shield',
                    'css_class': 'shield-effect'
                })
            elif buff.buff_type == 'domain':
                active_buffs.append({
                    'name': 'Domain Expansion (Active)',
                    'description': f'Your Domain Expansion is active. All other users are taking {buff.effect_value} HP damage every minute.',
                    'expires_at': buff.expires_at,
                    'icon': 'globe',
                    'css_class': 'domain-effect'
                })
                
        # Process domain effects from other users
        if not has_ultimate_shield:
            for domain in domain_effects:
                domain_owner = User.query.get(domain.user_id).username
                active_buffs.append({
                    'name': 'Domain Expansion (Affected)',
                    'description': f'You are in {domain_owner}\'s Domain Expansion! Taking {domain.effect_value} HP damage every minute.',
                    'expires_at': domain.expires_at,
                    'icon': 'alert-triangle',
                    'css_class': 'domain-effect',
                    'applied_by': domain_owner
                })

        stats = {
            'completed_tasks': completed_tasks,
            'total_tasks': total_tasks,
            'achievements_count': 0,  # Placeholder until achievements are implemented
            'friends_count': 0  # Placeholder for future friend system
        }

        return render_template('profile.html', 
                             stats=stats,
                             recent_activities=recent_activities,
                             recent_tasks=recent_activities,  # Add recent_tasks for compatibility with template
                             active_buffs=active_buffs)
    except Exception as e:
        logger.error(f"Error loading profile: {str(e)}")
        flash('Error loading profile data')
        return redirect(url_for('home'))

@app.route('/api/profile/avatar', methods=['POST'])
@login_required
def update_avatar():
    try:
        if 'avatar' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['avatar']
        is_valid, message = validate_profile_picture(file)

        if not is_valid:
            return jsonify({'error': message}), 400

        # Generate unique filename
        filename = secure_filename(f"avatar_{current_user.id}_{int(time.time())}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Save file
        file.save(filepath)

        # Update user avatar URL
        avatar_url = f"/static/uploads/avatars/{filename}"
        current_user.avatar_url = avatar_url
        db.session.commit()

        return jsonify({
            'status': 'success',
            'avatar_url': avatar_url
        })

    except Exception as e:
        logger.error(f"Error updating avatar: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update avatar'}), 500

@app.route('/api/profile/username', methods=['POST'])
@login_required
def update_username():
    try:
        data = request.json
        new_username = data.get('username')

        if not new_username:
            return jsonify({'error': 'Username is required'}), 400

        # Check if username is already taken
        if User.query.filter(User.username == new_username, User.id != current_user.id).first():
            return jsonify({'error': 'Username already taken'}), 400

        current_user.username = new_username
        db.session.commit()

        return jsonify({
            'status': 'success',
            'username': new_username
        })
    except Exception as e:
        logger.error(f"Error updating username: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update username'}), 500

@app.route('/api/tasks/stats')
@api_login_required
def get_task_stats():
    try:
        result = task_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )

        user_tasks = result['metadatas'] if result['metadatas'] else []
        completed_tasks = sum(1 for task in user_tasks if task['completed'])
        total_tasks = len(user_tasks)

        return jsonify({
            'completed': completed_tasks,
            'total': total_tasks
        })
    except Exception as e:
        logger.error(f"Error fetching task stats: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch task stats',
            'code': 500
        }), 500

def validate_profile_picture(file):
    """Validate profile picture requirements."""
    try:
        if not file:
            return False, "No file selected"

        # Check file size (max 5MB)
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset file pointer

        if size > 5 * 1024 * 1024:
            return False, "File size exceeds 5MB limit"

        # Check file extension
        filename = file.filename.lower()
        if not ('.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS):
            return False, "Invalid file format. Allowed formats: PNG, JPG, JPEG, GIF"

        return True, "File is valid"
    except Exception as e:
        logger.error(f"Error validating profile picture: {str(e)}")
        return False, "Error validating file"

# AI chat bot endpoint removed

# Task-related routes using ChromaDB
@app.route('/api/tasks/can_create', methods=['GET'])
@api_login_required
def can_create_task():
    """Check if user can create more tasks today based on rank and daily limits"""
    try:
        # Get task rank from request
        requested_rank = request.args.get('rank', 'E')
        logger.debug(f"Can create task check - User rank: '{current_user.rank}', Requested rank: '{requested_rank}'")

        # Get today's date for filtering
        today = datetime.datetime.utcnow().date().isoformat()

        # Get all tasks created today by the user
        result = task_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )

        # Filter tasks created today
        today_tasks = []
        for task in result['metadatas']:
            task_date = datetime.datetime.fromisoformat(task['created_at']).date().isoformat()
            if task_date == today:
                today_tasks.append(task)

        # Count total tasks today
        total_tasks_today = len(today_tasks)

        # Setup rank hierarchy
        ranks = ['E', 'D', 'C', 'B', 'A', 'S', 'S+']
        user_rank_index = ranks.index(current_user.rank.strip())  # Strip to remove any whitespace
        requested_rank_index = ranks.index(requested_rank.strip())  # Strip to remove any whitespace

        # Count E rank tasks today
        e_rank_count = sum(1 for task in today_tasks if task['rank'] == 'E')

        # Count high-rank tasks (tasks that are 1-2 ranks above user's rank)
        high_rank_count = 0
        s_plus_count = 0  # New counter for S+ tasks
        for task in today_tasks:
            task_rank_index = ranks.index(task['rank'])
            if task['rank'] == 'S+':
                s_plus_count += 1
            elif task_rank_index > user_rank_index and task_rank_index <= user_rank_index + 2:
                high_rank_count += 1

        # Determine if user can create the task
        can_create = True
        reason = None

        # Limit users to 3 E-rank tasks per day
        if requested_rank == 'E' and e_rank_count >= 3:
            can_create = False
            reason = "You can only create a maximum of 3 E-rank tasks per day"
        # Regular rank validation - tasks above user's rank
        elif requested_rank_index > user_rank_index + 2:
            max_allowed_rank = ranks[min(user_rank_index + 2, len(ranks) - 1)]
            can_create = False
            reason = f"With your current rank ({current_user.rank}), you can only create tasks up to rank {max_allowed_rank}"
        # Special case: S and A rank users can create one S+ task per day
        elif requested_rank == 'S+':
            if current_user.rank != 'S' and current_user.rank != 'A':
                can_create = False
                reason = f"Only S or A rank users can create S+ tasks"
            elif s_plus_count >= 1:
                can_create = False
                reason = "You can only create 1 S+ rank task per day"
        # E-rank tasks have their own limit (3 per day)
        elif requested_rank == 'E' and e_rank_count >= 3:
            can_create = False
            reason = "You can only create a maximum of 3 E-rank tasks per day"
        # Higher rank task limit - either one task higher than user's rank OR one task at/below user's rank
        elif requested_rank != 'E':
            # Count non-E rank tasks at or below user's rank
            user_rank_or_below_count = sum(1 for task in today_tasks 
                                        if task['rank'] != 'E' 
                                        and ranks.index(task['rank']) <= user_rank_index)

            if requested_rank_index > user_rank_index and high_rank_count >= 1:
                can_create = False
                reason = f"You can only create 1 task per day that is higher than your current rank ({current_user.rank})"
            elif requested_rank_index <= user_rank_index and user_rank_or_below_count >= 1:
                can_create = False
                reason = f"You can only create 1 non-E-rank task per day at or below your current rank ({current_user.rank})"
            elif high_rank_count >= 1 and requested_rank_index <= user_rank_index:
                can_create = False
                reason = f"You can only create EITHER 1 task higher than your rank OR 1 task at/below your rank"
            elif user_rank_or_below_count >= 1 and requested_rank_index > user_rank_index:
                can_create = False
                reason = f"You can only create EITHER 1 task higher than your rank OR 1 task at/below your rank"

        return jsonify({
            'can_create': can_create,
            'reason': reason,
            'daily_e_count': e_rank_count,
            'user_rank': current_user.rank,
            'max_allowed_rank_index': user_rank_index + 2,
            'total_tasks_today': total_tasks_today,
            'max_tasks_per_day': 4
        })

    except Exception as e:
        logger.error(f"Error checking task creation limits: {str(e)}")
        return jsonify({'error': str(e), 'can_create': False}), 500

@app.route('/api/tasks', methods=['POST'])
@api_login_required
def create_task():
    try:
        data = request.json
        requested_rank = data.get('rank', 'E')

        # Setup rank hierarchy first so we can use it
        ranks = ['E', 'D', 'C', 'B', 'A', 'S', 'S+']
        user_rank_index = ranks.index(current_user.rank.strip())  # Strip to remove any whitespace
        requested_rank_index = ranks.index(requested_rank.strip())  # Strip to remove any whitespace

        # Check daily limits
        today = datetime.datetime.utcnow().date().isoformat()
        result = task_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )

        # Filter tasks created today
        today_tasks = []
        for task in result['metadatas']:
            task_date = datetime.datetime.fromisoformat(task['created_at']).date().isoformat()
            if task_date == today:
                today_tasks.append(task)

        # Count total tasks today
        total_tasks_today = len(today_tasks)

        # Count E rank tasks today
        e_rank_count = sum(1 for task in today_tasks if task['rank'] == 'E')

        # Count high-rank tasks (tasks that are 1-2 ranks above user's rank)
        high_rank_count = 0
        s_plus_count = 0  # Counter for S+ tasks
        for task in today_tasks:
            task_rank_index = ranks.index(task['rank'])
            if task['rank'] == 'S+':
                s_plus_count += 1
                high_rank_count += 1  # S+ tasks also count as high rank tasks
            elif task_rank_index > user_rank_index and task_rank_index <= user_rank_index + 2:
                high_rank_count += 1

        # Enforce limits - separate E rank limit from higher rank limit

        # Limit users to 3 E-rank tasks per day
        if requested_rank == 'E' and e_rank_count >= 3:
            return jsonify({
                'error': 'Daily limit reached', 
                'message': 'You can only create a maximum of 3 E-rank tasks per day'
            }), 400

        # Check if task rank is more than 2 ranks above user's rank
        # Special case: S+, S and A rank users can create S+ rank tasks
        elif requested_rank == 'S+' and current_user.rank != 'S+' and current_user.rank != 'S' and current_user.rank != 'A':
            return jsonify({
                'error': 'Rank limit exceeded',
                'message': 'Only S+, S or A rank users can create S+ tasks'
            }), 400
        elif requested_rank == 'S+' and s_plus_count >= 1:
            return jsonify({
                'error': 'Daily limit reached',
                'message': 'You can only create EITHER 1 task higher than your rank OR 1 task at/below your rank'
            }), 400
        # Only for clarity - the next condition is not needed as S+ is already handled above
        elif requested_rank == 'S+' and high_rank_count >= 1:
            return jsonify({
                'error': 'Daily limit reached',
                'message': 'You can only create EITHER 1 task higher than your rank OR 1 task at/below your rank'
            }), 400
        elif requested_rank_index > user_rank_index + 2:
            max_allowed_rank = ranks[min(user_rank_index + 2, len(ranks) - 1)]
            return jsonify({
                'error': 'Rank limit exceeded',
                'message': f'With your current rank ({current_user.rank}), you can only create tasks up to rank {max_allowed_rank}'
            }), 400

        # For non-E rank tasks, implement the either/or limit
        elif requested_rank != 'E':
            # Count non-E rank tasks at or below user's rank
            user_rank_or_below_count = sum(1 for task in today_tasks 
                                        if task['rank'] != 'E' 
                                        and ranks.index(task['rank']) <= user_rank_index)

            if requested_rank_index > user_rank_index and high_rank_count >= 1:
                return jsonify({
                    'error': 'Daily limit reached',
                    'message': f'You can only create 1 task per day that is higher than your current rank ({current_user.rank})'
                }), 400
            elif requested_rank_index <= user_rank_index and user_rank_or_below_count >= 1:
                return jsonify({
                    'error': 'Daily limit reached',
                    'message': f'You can only create 1 non-E-rank task per day at or below your current rank ({current_user.rank})'
                }), 400
            elif high_rank_count >= 1 and requested_rank_index <= user_rank_index:
                return jsonify({
                    'error': 'Daily limit reached',
                    'message': f'You can only create EITHER 1 task higher than your rank OR 1 task at/below your rank'
                }), 400
            elif user_rank_or_below_count >= 1 and requested_rank_index > user_rank_index:
                return jsonify({
                    'error': 'Daily limit reached',
                    'message': f'You can only create EITHER 1 task higher than your rank OR 1 task at/below your rank'
                }), 400

        # Create the task if limits allow
        task_id = str(int(time.time() * 1000))  # Generate unique ID using timestamp
        task = {
            'id': task_id,
            'title': data['title'],
            'description': data.get('description', ''),
            'rank': requested_rank,
            'user_id': str(current_user.id),
            'completed': False,
            'created_at': datetime.datetime.utcnow().isoformat()
        }

        # Store task with minimal configuration
        task_collection.add(
            documents=[task['title']],  # Use title as document
            metadatas=[task],
            ids=[task_id],
            embeddings=[[0.0] * 384]  # Provide dummy embedding to bypass ONNX
        )

        logger.debug(f"Created new task: {task}")
        return jsonify(task)
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>/delete', methods=['DELETE'])
@api_login_required
def delete_task(task_id):
    try:
        # Get task to verify ownership
        result = task_collection.get(
            ids=[str(task_id)],  # Convert ID to string to match stored format
            where={"user_id": str(current_user.id)}
        )

        if not result['ids']:
            return jsonify({'error': 'Task not found or unauthorized'}), 404

        # Delete the task
        task_collection.delete(ids=[str(task_id)])
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        return jsonify({'error': 'Failed to delete task'}), 500

@app.route('/api/tasks/<task_id>/complete', methods=['POST'])
@api_login_required
def complete_task(task_id):
    try:
        # Get task to verify ownership
        result = task_collection.get(
            ids=[str(task_id)],
            where={"user_id": str(current_user.id)}
        )

        if not result['ids']:
            return jsonify({'error': 'Task not found or unauthorized'}), 404

        task = result['metadatas'][0]

        # Calculate experience points and coins based on task rank
        rank_rewards = {
            'E': {'exp': 10, 'coins': 5},    # Base rank
            'D': {'exp': 20, 'coins': 10},    # Bronze
            'C': {'exp': 30, 'coins': 15},    # Silver
            'B': {'exp': 40, 'coins': 20},    # Gold
            'A': {'exp': 50, 'coins': 25},    # Platinum
            'S': {'exp': 80, 'coins': 40},    # Diamond
            'S+': {'exp': 100, 'coins': 50}   # Master
        }
        task_rank = task['rank']
        rewards = rank_rewards.get(task_rank, rank_rewards['E'])
        exp_gain = rewards['exp']
        coin_gain = rewards['coins']

        # Apply any active buff effects to exp gain
        buff_effect = current_user.get_active_buff_effect()

        if buff_effect != 0:
            # Adjust exp based on buffs/debuffs
            exp_modifier = 1 + (buff_effect / 100)
            exp_gain = int(exp_gain * exp_modifier)

        # Update task in ChromaDB
        task['completed'] = True
        task['updated_at'] = datetime.datetime.now(IST).isoformat()
        task_collection.update(
            ids=[str(task_id)],
            documents=[task['title']],
            metadatas=[task],
            embeddings=[[0.0] * 384]
        )

        try:
            # Get current user stats
            result = user_collection.get(
                where={"user_id": str(current_user.id)},
                include=['metadatas']
            )

            # Initialize or update user stats
            user_stats = {
                'user_id': str(current_user.id),
                'monthly_exp': exp_gain,
                'lifetime_exp': exp_gain,
                'last_reset': datetime.datetime.now(IST).strftime('%Y-%m')
            }

            if result and result['metadatas']:
                existing_stats = result['metadatas'][0]
                user_stats['monthly_exp'] = int(existing_stats.get('monthly_exp', 0)) + exp_gain
                user_stats['lifetime_exp'] = int(existing_stats.get('lifetime_exp', 0)) + exp_gain

                # Update stats in ChromaDB
                user_collection.update(
                    ids=[f"user_{current_user.id}"],
                    documents=["user_stats"],
                    metadatas=[user_stats],
                    embeddings=[[0.0] * 384]
                )
            else:
                # Create new stats entry
                user_collection.add(
                    documents=["user_stats"],
                    metadatas=[user_stats],
                    ids=[f"user_{current_user.id}"],
                    embeddings=[[0.0] * 384]
                )

            # Get old level before updating exp
            old_level = current_user.level
            old_lifetime_exp = current_user.exp

            # Update the user's SQL record exp and coins
            current_user.exp += exp_gain
            current_user.coins += coin_gain

            # Calculate new level based on lifetime exp:
            # Level 1: 0+ EXP
            # Level 2: 50+ EXP  
            # Level 3: 100+ EXP (and so on)
            new_lifetime_exp = current_user.exp
            new_level = (new_lifetime_exp // 50) + 1
            current_user.level = new_level

            # Check if level increased
            if new_level > old_level:
                logger.info(f"User {current_user.id} leveled up from {old_level} to {new_level}")

                # Update max HP (10 HP per level)
                current_user.update_max_hp()

                # Log level up details for debugging
                logger.debug(f"Level up details - Old exp: {old_lifetime_exp}, New exp: {new_lifetime_exp}, Old level: {old_level}, New level: {new_level}, New max_hp: {current_user.max_hp}")

            db.session.commit()

            return jsonify({
                'status': 'success',
                'exp_gained': exp_gain,
                'monthly_exp': user_stats['monthly_exp'],
                'lifetime_exp': user_stats['lifetime_exp'],
                'level_up': new_level > old_level,
                'new_level': new_level if new_level > old_level else None,
                'new_max_hp': current_user.max_hp if new_level > old_level else None
            })

        except Exception as e:
            logger.error(f"Error updating user stats: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Failed to update user stats'}), 500
        try:
            user_result = user_collection.get(
                where={"user_id": str(current_user.id)},
                include=['metadatas']
            )

            # Initialize stats with default values
            user_stats = {
                'user_id': str(current_user.id),
                'monthly_exp': exp_gain,
                'lifetime_exp': exp_gain,
                'last_reset': datetime.datetime.now(IST).strftime('%Y-%m')
            }

            if user_result['metadatas']:
                existing_stats = user_result['metadatas'][0]
                user_stats['monthly_exp'] = existing_stats.get('monthly_exp', 0) + exp_gain
                user_stats['lifetime_exp'] = existing_stats.get('lifetime_exp', 0) + exp_gain
                user_stats['last_reset'] = existing_stats.get('last_reset', user_stats['last_reset'])

                # Update existing stats
                user_collection.update(
                    ids=[f"user_{current_user.id}"],
                    documents=["user_stats"],
                    metadatas=[user_stats],
                    embeddings=[[0.0] * 384]
                )
            else:
                # Create new stats
                user_collection.add(
                    documents=["user_stats"],
                    metadatas=[user_stats],
                    ids=[f"user_{current_user.id}"],
                    embeddings=[[0.0] * 384]
                )

            return jsonify({
                'status': 'success',
                'exp_gained': exp_gain,
                'monthly_exp': user_stats['monthly_exp'],
                'lifetime_exp': user_stats['lifetime_exp']
            })

        except Exception as e:
            logger.error(f"Error updating user stats: {str(e)}")
            return jsonify({'error': 'Failed to update user stats'}), 500

    except Exception as e:
        logger.error(f"Error completing task: {str(e)}")
        return jsonify({'error': 'Failed to complete task'}), 500

@app.route('/api/user/stats')
@api_login_required
def get_user_stats():
    try:
        # Get user stats from ChromaDB
        result = user_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )

        if not result['ids']:
            # Initialize user stats if not present
            user_stats = {
                'user_id': str(current_user.id),
                'monthly_exp': 0,
                'lifetime_exp': 0,
                'last_reset': datetime.datetime.now(IST).strftime('%Y-%m')
            }
            user_collection.add(
                documents=["user_stats"],
                metadatas=[user_stats],
                ids=[f"stats_{current_user.id}"],
                embeddings=[[0.0] * 384]  # Provide dummy embedding to bypass ONNX
            )
        else:
            user_stats = result['metadatas'][0]

            # Check if we need to reset monthly EXP
            current_month = datetime.datetime.now(IST).strftime('%Y-%m')
            if user_stats.get('last_reset') != current_month:
                user_stats['monthly_exp'] = 0
                user_stats['last_reset'] = current_month
                user_collection.update(
                    ids=[f"stats_{current_user.id}"],
                    documents=["user_stats"],
                    metadatas=[user_stats],
                    embeddings=[[0.0] * 384]  # Provide dummy embedding to bypass ONNX
                )

        # Calculate rank based on monthly EXP
        monthly_exp = int(user_stats.get('monthly_exp', 0))
        lifetime_exp = int(user_stats.get('lifetime_exp', 0))

        # Define rank thresholds
        rank_thresholds = {
            'E': 0,
            'D': 200,
            'C': 500,
            'B': 900,
            'A': 1400,
            'S': 2000,
            'S+': 2500
        }

        # Calculate rank
        rank = 'E'  # Default rank
        if monthly_exp >= 2500:
            rank = 'S+'
        elif monthly_exp >= 2000:
            rank = 'S'
        elif monthly_exp >= 1400:
            rank = 'A'
        elif monthly_exp >= 900:
            rank = 'B'
        elif monthly_exp >= 500:
            rank = 'C'
        elif monthly_exp >= 200:
            rank = 'D'

        # Update the user's rank in the SQL database
        current_user.rank = rank
        db.session.commit()

        # Calculate level:
        # Level 1: 0+ EXP
        # Level 2: 50+ EXP
        # Level 3: 100+ EXP (and so on)
        level = (lifetime_exp // 50) + 1

        # Get current rank threshold and next rank threshold
        current_threshold = rank_thresholds[rank]
        next_threshold = 2500  # Default to max threshold (S+)
        for threshold in sorted(rank_thresholds.values()):
            if threshold > monthly_exp:
                next_threshold = threshold
                break

        # Calculate progress percentage safely
        if next_threshold == current_threshold:
            progress = 100  # Max rank reached
        else:
            progress = ((monthly_exp - current_threshold) / (next_threshold - current_threshold)) * 100
            progress = max(0, min(100, progress))  # Ensure progress stays between 0-100

        # Calculate EXP needed for next rank
        next_rank_exp = next_threshold - monthly_exp

        # Update max HP based on level (10 HP per level after level 1)
        current_user.update_max_hp()
        db.session.commit()

        # Get active buff effect for the user
        buff_effect = current_user.get_active_buff_effect()

        return jsonify({
            'monthly_exp': monthly_exp,
            'current_threshold': current_threshold,
            'next_threshold': next_threshold,
            'progress': progress,
            'lifetime_exp': lifetime_exp,
            'rank': rank,
            'level': level,
            'next_rank_exp': next_rank_exp,
            'login_streak': current_user.login_streak,
            'hp': current_user.hp,
            'max_hp': current_user.max_hp,
            'coins': current_user.coins,
            'buff_effect': buff_effect  # Add buff/debuff effect percentage
        })

    except Exception as e:
        logger.error(f"Error fetching user stats: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch user stats',
            'code': 500
        }), 500

# API endpoint to list all users for debuff feature
@app.route('/api/users/list', methods=['GET'])
@login_required
def list_users():
    """Get a list of all users for applying debuffs."""
    try:
        # Get all users except current user
        users = User.query.filter(User.id != current_user.id).all()

        # Format user data
        user_list = [
            {
                'id': user.id,
                'username': user.username,
                'rank': user.rank,
                'level': user.level
            } for user in users
        ]

        return jsonify(user_list)
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({'error': 'Failed to load users'}), 500

        db.session.rollback()
        return jsonify({'error': 'Failed to apply debuff'}), 500

@app.route('/lucky-wheel')
@login_required
def lucky_wheel():
    """Render the lucky spin wheel page."""
    try:
        can_spin = current_user.can_spin_wheel()
        next_spin_day = None

        if not can_spin:
            # Calculate days until next Monday for reset
            from datetime import datetime, timedelta
            now = datetime.now(IST)
            today = now.date()
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7  # If today is Monday, next spin is next Monday
            next_spin_day = (today + timedelta(days=days_until_monday)).strftime('%A, %d %B %Y')

        return render_template('lucky_wheel.html', 
                              can_spin=can_spin, 
                              next_spin_day=next_spin_day)
    except Exception as e:
        logger.error(f"Error accessing lucky wheel: {str(e)}")
        flash('Error loading lucky wheel')
        return redirect(url_for('home'))

@app.route('/api/lucky-wheel/spin', methods=['POST'])
@api_login_required
def spin_wheel():
    """Handle the lucky wheel spin action."""
    try:
        import random
        from datetime import datetime

        # Check if user can spin
        if not current_user.can_spin_wheel():
            return jsonify({
                'status': 'error',
                'message': 'You can only spin the wheel once per week. Please try again next Monday.'
            }), 400

        # Define possible rewards based on ranks - aligned with rank thresholds
        rank_rewards = {
            'S+': 100,  # EXP >= 2500
            'S': 80,    # EXP >= 2000
            'A': 50,    # EXP >= 1400
            'B': 40,    # EXP >= 900
            'C': 30,    # EXP >= 500
            'D': 20,    # EXP >= 200
            'E': 10     # EXP < 200
        }

        # Get all possible rewards
        rewards = list(rank_rewards.values())

        # Pick a random reward
        exp_reward = random.choice(rewards)

        # Update user's EXP and last spin date
        current_user.exp += exp_reward
        current_user.last_spin_date = datetime.now(IST).date()
        db.session.commit()

        # Update user stats in ChromaDB
        try:
            if user_collection:
                # Get existing user stats
                result = user_collection.get(
                    where={"user_id": str(current_user.id)},
                    include=['metadatas']
                )

                if result and result['metadatas'] and len(result['metadatas']) > 0:
                    user_stats = result['metadatas'][0]

                    # Update EXP values
                    current_monthly_exp = user_stats.get('monthly_exp', 0)
                    current_lifetime_exp = user_stats.get('lifetime_exp', 0)

                    user_stats['monthly_exp'] = current_monthly_exp + exp_reward
                    user_stats['lifetime_exp'] = current_lifetime_exp + exp_reward

                    # Update user stats in ChromaDB
                    user_collection.update(
                        ids=[f"user_{current_user.id}"],
                        metadatas=[user_stats]
                    )
                else:
                    # If no existing stats, create new entry
                    user_collection.add(
                        documents=[f"User {current_user.username} stats"],
                        metadatas=[{
                            "user_id": str(current_user.id),
                            "monthly_exp": exp_reward,
                            "lifetime_exp": exp_reward
                        }],
                        ids=[f"user_{current_user.id}"]
                    )
        except Exception as e:
            logger.error(f"Error updating ChromaDB with spin wheel reward: {str(e)}")
            # Continue execution despite ChromaDB error

        return jsonify({
            'status': 'success',
            'exp_reward': exp_reward,
            'message': f'Congratulations! You won {exp_reward} EXP!'
        })
    except Exception as e:
        logger.error(f"Error during wheel spin: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'An error occurred during the spin. Please try again.'
        }), 500

@app.route('/api/lucky-wheel/status')
@api_login_required
def wheel_status():
    """Check if user can spin the wheel."""
    try:
        can_spin = current_user.can_spin_wheel()

        next_spin_day = None
        if not can_spin:
            # Calculate days until next Monday for reset
            from datetime import datetime, timedelta
            now = datetime.now(IST)
            today = now.date()
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7  # If today is Monday, next spin is next Monday
            next_spin_day = (today + timedelta(days=days_until_monday)).strftime('%A, %d %B %Y')

        return jsonify({
            'can_spin': can_spin,
            'next_spin_day': next_spin_day,
            'last_spin_date': current_user.last_spin_date.strftime('%A, %d %B %Y') if current_user.last_spin_date else None
        })
    except Exception as e:
        logger.error(f"Error checking wheel status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred checking your spin status.'
        }), 500

@app.route('/api/test/hp-depletion', methods=['POST'])
@api_login_required
def test_hp_depletion():
    """Test route to simulate HP depletion (only for testing)"""
    try:
        # Set HP to 0 to trigger depletion logic
        prev_hp = current_user.hp
        prev_exp = current_user.exp

        # Check ChromaDB exp before depletion
        result = user_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )
        chroma_stats_before = result['metadatas'][0] if result and result['metadatas'] else {}
        monthly_exp_before = chroma_stats_before.get('monthly_exp', 0)
        lifetime_exp_before = chroma_stats_before.get('lifetime_exp', 0)

        # Force HP to 0 to trigger depletion
        current_user.hp = 0
        current_user.handle_hp_depletion()

        # Get updated stats after depletion
        result = user_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )
        chroma_stats_after = result['metadatas'][0] if result and result['metadatas'] else {}
        monthly_exp_after = chroma_stats_after.get('monthly_exp', 0)
        lifetime_exp_after = chroma_stats_after.get('lifetime_exp', 0)

        return jsonify({
            'status': 'success',
            'message': 'HP depletion test executed successfully',
            'data': {
                'before': {
                    'hp': prev_hp,
                    'exp': prev_exp,
                    'monthly_exp': monthly_exp_before,
                    'lifetime_exp': lifetime_exp_before
                },
                'after': {
                    'hp': current_user.hp,
                    'exp': current_user.exp,
                    'monthly_exp': monthly_exp_after,
                    'lifetime_exp': lifetime_exp_after
                },
                'changes': {
                    'hp_change': current_user.hp - prev_hp,
                    'exp_change': current_user.exp - prev_exp,
                    'monthly_exp_change': monthly_exp_after - monthly_exp_before,
                    'lifetime_exp_change': lifetime_exp_after - lifetime_exp_before
                }
            }
        })
    except Exception as e:
        logger.error(f"Error in HP depletion test: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/check-incomplete-tasks', methods=['POST'])
@api_login_required
def test_check_incomplete_tasks():
    """Test endpoint to manually trigger the midnight HP penalty check for incomplete tasks"""
    try:
        from main import check_incomplete_tasks
        # Call the check_incomplete_tasks function
        check_incomplete_tasks()

        return jsonify({
            'status': 'success',
            'message': 'Incomplete tasks check triggered successfully',
            'current_hp': current_user.hp,
            'max_hp': current_user.max_hp
        })
    except Exception as e:
        logger.error(f"Error in test_check_incomplete_tasks: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error triggering incomplete tasks check: {str(e)}'
        }), 500

@app.route('/api/achievements')
@api_login_required
def get_achievements():
    try:
        result = achievement_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )
        user_achievements = [eval(doc) for doc in result['metadatas']] if result['metadatas'] else []
        return jsonify(user_achievements)
    except Exception as e:
        logger.error(f"Error fetching achievements: {str(e)}")
        return jsonify({'error': 'Failed to fetch achievements'}), 500

@app.route('/api/tasks/recent')
@api_login_required
def get_recent_completed_tasks():
    try:
        # Get tasks from ChromaDB
        result = task_collection.get(
            where={"user_id": str(current_user.id)},
            include=['metadatas']
        )

        # Filter completed tasks and format them
        completed_tasks = []
        for task in result['metadatas']:
            if task.get('completed', False):
                try:
                    timestamp = task.get('updated_at', task.get('created_at'))
                    if timestamp:
                        completed_tasks.append({
                            'title': task.get('title', 'Untitled Task'),
                            'completed_at': timestamp
                        })
                except Exception as e:
                    logger.error(f"Error processing task: {e}")
                    continue

        # Sort by completion time and return the most recent ones
        completed_tasks.sort(key=lambda x: x['completed_at'], reverse=True)
        return jsonify(completed_tasks[:5])
    except Exception as e:
        logger.error(f"Error fetching recent tasks: {str(e)}")
        return jsonify({'error': 'Failed to fetch recent tasks'}), 500

@app.route('/leaderboard')
@login_required
def leaderboard():
    try:
        logger.debug("Starting leaderboard data fetch")

        # Get all users from database to ensure accurate rank information
        all_users = User.query.all()
        user_dict = {user.id: user for user in all_users}
        logger.debug(f"Found {len(all_users)} users in database")

        ## Get all users' stats for leaderboards
        try:
            result = user_collection.get(include=['metadatas'])
            logger.debug(f"Retrieved statsfrom ChromaDB: {result}")
        except Exception as e:
            logger.error(f"Error fetching from ChromaDB: {str(e)}")
            raise

        monthly_leaders = []
        lifetime_leaders = []
        processed_users = set()  # Track processed users

        if result and result['metadatas']:
            # First pass: Find highest exp values for each user
            user_exp_data = {}
            for user_stats in result['metadatas']:
                try:
                    if not isinstance(user_stats, dict) or 'user_id' not in user_stats:
                        continue

                    try:
                        user_id = int(user_stats['user_id'])
                    except (ValueError, TypeError):
                        continue

                    monthly_exp = user_stats.get('monthly_exp', 0)
                    lifetime_exp = user_stats.get('lifetime_exp', 0)

                    # Update only if this entry has higher exp values
                    if user_id not in user_exp_data or monthly_exp > user_exp_data[user_id]['monthly_exp']:
                        user_exp_data[user_id] = {
                            'monthly_exp': monthly_exp,
                            'lifetime_exp': lifetime_exp
                        }

                except Exception as e:
                    logger.error(f"Error processing user stats: {str(e)}")
                    continue

            # Second pass: Process users with their highest exp values
            for user_id, exp_data in user_exp_data.items():
                try:
                    if user_id not in user_dict:
                        continue

                    user = user_dict[user_id]
                    monthly_exp = exp_data['monthly_exp']
                    lifetime_exp = exp_data['lifetime_exp']

                    # Skip users with no EXP (dummy accounts)
                    if monthly_exp == 0 and lifetime_exp == 0:
                        continue

                    # Skip users we've already processed
                    if user_id in processed_users:
                        continue
                    processed_users.add(user_id)

                    # Skip users with no EXP (dummy accounts)
                    monthly_exp = exp_data['monthly_exp']
                    lifetime_exp = exp_data['lifetime_exp']

                    if monthly_exp == 0 and lifetime_exp == 0:
                        logger.debug(f"Skipping user {user.username} with no EXP")
                        continue

                    # Calculate rank based on monthly EXP
                    rank = 'E'  # Default rank
                    if monthly_exp >= 2500:
                        rank = 'S+'
                    elif monthly_exp >= 2000:
                        rank = 'S'
                    elif monthly_exp >= 1400:
                        rank = 'A'
                    elif monthly_exp >= 900:
                        rank = 'B'
                    elif monthly_exp >= 500:
                        rank = 'C'
                    elif monthly_exp >= 200:
                        rank = 'D'

                    # Calculate level based on lifetime EXP:
                    # Level 1: 0+ EXP
                    # Level 2: 50+ EXP
                    # Level 3: 100+ EXP (and so on)
                    level = (lifetime_exp // 50) + 1

                    logger.debug(f"Processing user {user.username}: monthly_exp={monthly_exp}, rank={rank}, level={level}")

                    # Add to monthly leaders with calculated rank
                    monthly_leaders.append({
                        'username': user.username,
                        'exp': monthly_exp,
                        'rank': rank,  # Use calculated rank instead of stored rank
                        'avatar_url': user.avatar_url or '/static/default-avatar.png'
                    })

                    # Add to lifetime leaders
                    lifetime_leaders.append({
                        'username': user.username,
                        'lifetime_exp': lifetime_exp,
                        'level': level,
                        'avatar_url': user.avatar_url or '/static/default-avatar.png'
                    })
                except Exception as e:
                    logger.error(f"Error processing user stats: {str(e)}")
                    continue

            # Sort leaders by EXP
            monthly_leaders.sort(key=lambda x: x['exp'], reverse=True)
            lifetime_leaders.sort(key=lambda x: x['lifetime_exp'], reverse=True)

            logger.debug(f"Final monthly leaders: {monthly_leaders}")
            logger.debug(f"Final lifetime leaders: {lifetime_leaders}")

        return render_template('leaderboard.html', 
                            monthly_leaders=monthly_leaders,
                            lifetime_leaders=lifetime_leaders)
    except Exception as e:
        logger.error(f"Error in leaderboard: {str(e)}")
        flash('Error loading leaderboard')
        return redirect(url_for('home'))

@app.route('/api/user/rank', methods=['POST'])
@api_login_required
def update_user_rank():
    try:
        data = request.json
        user_id = data.get('user_id')
        new_rank = data.get('rank')

        # Validate rank
        valid_ranks = ['E', 'D', 'C', 'B', 'A', 'S', 'S+']
        if new_rank not in valid_ranks:
            return jsonify({'error': 'Invalid rank provided'}), 400

        # Only admin or self can update rank
        if str(current_user.id) != str(user_id) and not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get the user
        user = User.query.get(int(user_id))
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Update rank
        user.rank = new_rank
        db.session.commit()

        # Also update in ChromaDB if using it
        try:
            result = user_collection.get(
                where={"user_id": str(user_id)},
                include=['metadatas']
            )

            if result['ids']:
                user_stats = result['metadatas'][0]
                user_stats['user_rank'] = new_rank

                user_collection.update(
                    ids=[f"stats_{user_id}"],
                    documents=["user_stats"],
                    metadatas=[user_stats],
                    embeddings=[[0.0] * 384]
                )
        except Exception as e:
            logger.error(f"Error updating user rank in ChromaDB: {str(e)}")

        return jsonify({
            'status': 'success',
            'new_rank': new_rank
        })
    except Exception as e:
        logger.error(f"Error updating user rank: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update user rank'}), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

# Add game route after other routes but before database initialization
# Add this temporary route to update User J's exp
@app.route('/temp_update_exp')
def temp_update_exp():
    try:
        # Get User J's stats
        user_stats = {
            'user_id': '1',  # User J's ID
            'monthly_exp': 1200,
            'lifetime_exp': 1200,
            'last_reset': datetime.datetime.now(IST).strftime('%Y-%m')
        }

        # Update in ChromaDB
        user_collection.update(
            ids=[f"stats_1"],  # User J's stats ID
            documents=["user_stats"],
            metadatas=[user_stats],
            embeddings=[[0.0] * 384]  # Provide dummy embedding
        )

        return 'Updated successfully'
    except Exception as e:
        return str(e)

# Database initialization at the end of app.py
def init_database():
    try:
        with app.app_context():
            # Only create tables if they don't exist
            db.create_all()

            # Check if last_spin_date column exists in user table
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                columns = [column['name'] for column in inspector.get_columns('user')]

                # Add last_spin_date column if it doesn't exist
                if 'last_spin_date' not in columns:
                    logger.info("Adding last_spin_date column to user table...")
                    from sqlalchemy import text
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE user ADD COLUMN last_spin_date DATE'))
                        conn.commit()
                    logger.info("last_spin_date column added successfully")
            except Exception as schema_error:
                logger.error(f"Error updating schema: {str(schema_error)}")

            logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

# Import models before database initialization
from models import User, Task, Achievement, UserAchievement, StoreItem, UserInventory, UserBuff, UserTransaction

# Store route
@app.route('/store')
@login_required
def store():
    """Render the store page where users can buy items."""
    # Get items by type
    healing_items = StoreItem.query.filter_by(item_type='healing').all()
    buff_items = StoreItem.query.filter_by(item_type='buff').all()
    debuff_items = StoreItem.query.filter_by(item_type='debuff').all()
    recovery_items = StoreItem.query.filter_by(item_type='recovery').all()
    
    # Get new items
    shield_items = StoreItem.query.filter_by(item_type='shield').all()
    domain_items = StoreItem.query.filter_by(item_type='domain').all()
    
    # Add shields to recovery items since they provide protection
    recovery_items.extend(shield_items)
    
    # Add domain expansion to debuff items since it's an offensive item
    debuff_items.extend(domain_items)

    return render_template('store.html', 
                           healing_items=healing_items,
                           buff_items=buff_items,
                           debuff_items=debuff_items,
                           recovery_items=recovery_items,
                           user_coins=current_user.coins)

# API endpoint to buy an item
@app.route('/api/store/buy/<int:item_id>', methods=['POST'])
@login_required
def buy_item(item_id):
    """Handle purchasing an item from the store."""
    try:
        # Get the item
        item = StoreItem.query.get_or_404(item_id)

        # Check if user has enough coins
        if current_user.coins < item.price:
            return jsonify({
                'error': 'Not enough coins',
                'message': 'You do not have enough coins to purchase this item.'
            }), 400

        # Deduct coins
        current_user.coins -= item.price

        # Add item to user's inventory (or increase quantity if already owned)
        inventory_item = UserInventory.query.filter_by(
            user_id=current_user.id, 
            item_id=item.id
        ).first()

        if inventory_item:
            # User already has this item, increase quantity
            inventory_item.quantity += 1
        else:
            # Add new item to inventory
            inventory_item = UserInventory(
                user_id=current_user.id,
                item_id=item.id,
                quantity=1
            )
            db.session.add(inventory_item)

        # Record transaction
        transaction = UserTransaction(
            user_id=current_user.id,
            transaction_type='purchase',
            item_id=item.id,
            amount=-item.price,
            description=f"Purchased {item.name} for {item.price} coins."
        )
        db.session.add(transaction)

        # Commit changes
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Successfully purchased {item.name}!',
            'coins': current_user.coins,
            'item_name': item.name
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error purchasing item: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your purchase.'}), 500

# Inventory route
@app.route('/hp-test')
@login_required
def hp_test_page():
    """Render the HP depletion test page."""
    return render_template('hp_test.html')

@app.route('/inventory')
@login_required
def inventory():
    """Render the inventory page where users can see and use their items."""
    try:
        # Get user's inventory items
        inventory_items = UserInventory.query.filter_by(user_id=current_user.id).all()

        # Get active buffs (filter out expired buffs)
        current_time = datetime.datetime.now(IST)
        active_buffs = UserBuff.query.filter(
            UserBuff.user_id == current_user.id,
            (UserBuff.expires_at > current_time) | (UserBuff.expires_at.is_(None))
        ).all()

        # Calculate total buff effect
        buff_effect = current_user.get_active_buff_effect()

        return render_template('inventory.html',
                           inventory_items=inventory_items,
                           active_buffs=active_buffs,
                           buff_effect=buff_effect,
                           user_hp=current_user.hp,
                           user_max_hp=current_user.max_hp)
    except Exception as e:
        app.logger.error(f"Error accessing inventory: {str(e)}")
        flash('Error loading inventory. Please try again.', 'error')
        return redirect(url_for('home'))

# API endpoint to use an item
@app.route('/api/inventory/use/<int:item_id>', methods=['POST'])
@login_required
def use_item(item_id):
    """Handle using an item from the inventory."""
    try:
        # Get the inventory item
        inventory_item = UserInventory.query.filter_by(
            id=item_id, 
            user_id=current_user.id
        ).first_or_404()

        item = inventory_item.item

        result = {
            'message': f'Used {item.name}!',
            'hp': current_user.hp,
            'max_hp': current_user.max_hp,
            'buff_effect': current_user.get_active_buff_effect()
        }

        # Apply item effect based on type
        if item.item_type == 'healing':
            # Healing potions restore HP
            if item.effect_value > 0:
                # Normal healing
                current_user.heal(item.effect_value)
                result['message'] = f'Restored {item.effect_value} HP!'
            else:
                # Full restoration
                healed = current_user.max_hp - current_user.hp
                current_user.hp = current_user.max_hp
                result['message'] = f'Fully restored your HP! (+{healed} HP)'

            result['hp'] = current_user.hp

        elif item.item_type == 'buff':
            # Buff potions increase EXP gain
            # Check if user already has a buff
            existing_buff = UserBuff.query.filter_by(
                user_id=current_user.id,
                buff_type='buff'
            ).first()

            if existing_buff:
                # Update existing buff
                existing_buff.effect_value = item.effect_value
                # Reset expiration if needed
                # Note: In a real implementation, you might want to set an expiration time
            else:
                # Add new buff
                new_buff = UserBuff(
                    user_id=current_user.id,
                    buff_type='buff',
                    effect_value=item.effect_value
                    # Note: In a real implementation, you'd set expires_at
                )
                db.session.add(new_buff)

            result['message'] = f'Applied +{item.effect_value}% EXP gain buff!'
            result['buff_effect'] = current_user.get_active_buff_effect()
        
        elif item.item_type == 'shield':
            # Shield protects against debuffs for a period of time
            from datetime import datetime, timedelta
            
            # Calculate expiration time based on effect_value (hours)
            expires_at = datetime.now(IST) + timedelta(hours=item.effect_value)
            
            # Check if user already has a shield
            existing_shield = UserBuff.query.filter_by(
                user_id=current_user.id,
                buff_type='shield'
            ).first()
            
            if existing_shield:
                # Update existing shield with new expiration time and tier
                existing_shield.expires_at = expires_at
                existing_shield.effect_value = item.item_tier == 'ultimate'  # 1 for ultimate (can block domain), 0 for others
                result['message'] = f'Shield refreshed! Protected against debuffs for {item.effect_value} hours.'
            else:
                # Add new shield
                new_shield = UserBuff(
                    user_id=current_user.id,
                    buff_type='shield',
                    effect_value=1 if item.item_tier == 'ultimate' else 0,  # Can block domain expansion?
                    expires_at=expires_at
                )
                db.session.add(new_shield)
                result['message'] = f'Shield activated! Protected against debuffs for {item.effect_value} hours.'
                
                if item.item_tier == 'ultimate':
                    result['message'] += ' This shield can also protect against Domain Expansion.'
            
        elif item.item_type == 'domain':
            # Domain Expansion - affects all other users with HP damage
            from datetime import datetime, timedelta
            from models import User
            
            # Set up the domain expiration (24 minutes)
            expires_at = datetime.now(IST) + timedelta(minutes=24)
            
            # First check if user already has an active domain
            existing_domain = UserBuff.query.filter_by(
                user_id=current_user.id,
                buff_type='domain'
            ).first()
            
            # Check if any other user has an active domain expansion
            other_active_domains = UserBuff.query.filter(
                UserBuff.buff_type == 'domain',
                UserBuff.user_id != current_user.id,
                UserBuff.expires_at > datetime.now(IST)
            ).first()
            
            if existing_domain:
                result['message'] = 'You already have an active Domain Expansion!'
                return jsonify(result)
            elif other_active_domains:
                # Get the domain owner's username
                domain_owner = User.query.get(other_active_domains.user_id)
                owner_name = domain_owner.username if domain_owner else "Another user"
                result['message'] = f"Cannot activate Domain Expansion! {owner_name}'s Domain is still active. Try again when their domain expires."
                return jsonify(result)
            else:
                # Add domain buff to the user
                domain_buff = UserBuff(
                    user_id=current_user.id,
                    buff_type='domain',
                    effect_value=item.effect_value,  # 40 HP damage per minute
                    expires_at=expires_at
                )
                db.session.add(domain_buff)
                
                # Apply initial damage to all users except current user and those with ultimate shields
                all_users = User.query.filter(User.id != current_user.id).all()
                affected_users = 0
                
                for user in all_users:
                    # Check if user has an ultimate shield
                    has_shield = UserBuff.query.filter_by(
                        user_id=user.id,
                        buff_type='shield',
                        effect_value=1  # ultimate shield has effect_value=1
                    ).filter(UserBuff.expires_at > datetime.now(IST)).first()
                    
                    if not has_shield:
                        # Apply 40 HP damage
                        user.lose_hp(40)
                        affected_users += 1
                        
                        # Record transaction for the damage
                        domain_damage = UserTransaction(
                            user_id=user.id,
                            transaction_type='hp_change',
                            amount=-item.effect_value,
                            description=f"Hit by {current_user.username}'s Domain Expansion"
                        )
                        db.session.add(domain_damage)
                
                result['message'] = f'Domain Expansion activated! {affected_users} users took {item.effect_value} HP damage. The domain will last for 24 minutes, dealing {item.effect_value} HP damage per minute.'
                # Note: The scheduler is set up to apply damage every minute
                # Domain expires after 24 minutes

        elif item.item_type == 'recovery':
            # Recovery potions have special effects
            if item.name == "Clarity Potion":
                # Remove all debuffs
                debuffs = UserBuff.query.filter_by(
                    user_id=current_user.id,
                    buff_type='debuff'
                ).all()

                if debuffs:
                    for debuff in debuffs:
                        db.session.delete(debuff)
                    result['message'] = 'All debuffs have been removed!'
                else:
                    result['message'] = 'You have no debuffs to remove.'

                result['buff_effect'] = current_user.get_active_buff_effect()
            else:
                # Other recovery items would be implemented here
                result['message'] = f'Used {item.name}!'

        # Record transaction
        transaction = UserTransaction(
            user_id=current_user.id,
            transaction_type='use',
            item_id=item.id,
            amount=0,
            description=f"Used {item.name}."
        )
        db.session.add(transaction)

        # Decrease quantity
        inventory_item.quantity -= 1
        if inventory_item.quantity <= 0:
            db.session.delete(inventory_item)

        # Commit changes
        db.session.commit()

        return jsonify(result)

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error using item: {str(e)}")
        return jsonify({'error': 'An error occurred while using the item.'}), 500

# API endpoint to apply a debuff to another user
@app.route('/api/inventory/apply_debuff/<int:item_id>', methods=['POST'])
@login_required
def apply_debuff(item_id):
    """Apply a debuff to another user."""
    try:
        data = request.json
        target_user_id = data.get('target_user_id')

        if not target_user_id:
            return jsonify({'error': 'Target user is required.'}), 400

        # Get the target user
        target_user = User.query.get_or_404(target_user_id)

        # Cannot apply debuff to self
        if target_user.id == current_user.id:
            return jsonify({'error': 'You cannot apply a debuff to yourself.'}), 400

        # Get the inventory item
        inventory_item = UserInventory.query.filter_by(
            id=item_id, 
            user_id=current_user.id
        ).first_or_404()

        item = inventory_item.item

        # Ensure item is a debuff type
        if item.item_type != 'debuff':
            return jsonify({'error': 'This item cannot be used as a debuff.'}), 400

        # Check if target user has an active shield
        from datetime import datetime, timedelta
        shield = UserBuff.query.filter_by(
            user_id=target_user.id,
            buff_type='shield'
        ).filter(UserBuff.expires_at > datetime.now(IST)).first()
        
        if shield:
            # Ultimate shield blocks everything, normal/advanced shields block regular debuffs
            if shield.effect_value == 1 or item.item_tier != 'ultimate':
                # Return message about shield blocking the debuff
                return jsonify({
                    'message': f'{target_user.username} is protected by a shield! Debuff was blocked.'
                })
            # If it's a domain expansion and not an ultimate shield, the shield breaks
            elif item.item_tier == 'ultimate':
                db.session.delete(shield)
            
        # Only allow domain-wide effects if item is domain type and user has active domain
        if item.item_type == 'domain':
            return jsonify({
                'error': 'You must activate Domain Expansion before using it.',
                'message': 'Please use Domain Expansion from your inventory first.'
            }), 400
            
        # Check if current user has an active domain expansion
        active_domain = UserBuff.query.filter_by(
            user_id=current_user.id,
            buff_type='domain'
        ).filter(UserBuff.expires_at > datetime.now(IST)).first()
        
        # If domain is active, apply debuff to all users without shields
        affected_users = []
        
        if active_domain:
            # Apply to all users except current user and those with shields
            all_users = User.query.filter(User.id != current_user.id).all()
            
            for user in all_users:
                # Skip users with active shields
                user_shield = UserBuff.query.filter_by(
                    user_id=user.id,
                    buff_type='shield'
                ).filter(UserBuff.expires_at > datetime.now(IST)).first()
                
                # If user has ultimate shield (effect_value=1), they are protected from all effects including domain
                if user_shield and user_shield.effect_value == 1:
                    continue
                # If user has regular shield and this isn't a domain effect, they are still protected
                elif user_shield and item.item_tier != 'ultimate':
                    continue
                # If user has regular shield, break it but still apply the debuff
                elif user_shield:
                    db.session.delete(user_shield)
                    
                # Apply debuff to this user
                existing_debuff = UserBuff.query.filter_by(
                    user_id=user.id,
                    buff_type='debuff',
                    applied_by_user_id=current_user.id
                ).first()
                
                if existing_debuff:
                    # Update existing debuff
                    existing_debuff.effect_value = item.effect_value
                    # Set expiration to 24 hours
                    existing_debuff.expires_at = datetime.now(IST) + timedelta(hours=24)
                else:
                    # Add new debuff
                    new_debuff = UserBuff(
                        user_id=user.id,
                        buff_type='debuff',
                        effect_value=item.effect_value,
                        applied_by_user_id=current_user.id,
                        expires_at=datetime.now(IST) + timedelta(hours=24)
                    )
                    db.session.add(new_debuff)
                    
                affected_users.append(user.username)
                
            # Record transaction for domain-wide debuff
            transaction = UserTransaction(
                user_id=current_user.id,
                transaction_type='use',
                item_id=item.id,
                amount=0,
                description=f"Applied {item.name} to all users through Domain Expansion."
            )
            db.session.add(transaction)
            
        else:
            # Normal debuff application to single target
            existing_debuff = UserBuff.query.filter_by(
                user_id=target_user.id,
                buff_type='debuff',
                applied_by_user_id=current_user.id
            ).first()

            if existing_debuff:
                # Update existing debuff
                existing_debuff.effect_value = item.effect_value
                # Set expiration to 24 hours
                existing_debuff.expires_at = datetime.now(IST) + timedelta(hours=24)
            else:
                # Add new debuff
                new_debuff = UserBuff(
                    user_id=target_user.id,
                    buff_type='debuff',
                    effect_value=item.effect_value,
                    applied_by_user_id=current_user.id,
                    expires_at=datetime.now(IST) + timedelta(hours=24)
                )
                db.session.add(new_debuff)
                
            affected_users = [target_user.username]

            # Record transaction for single debuff
            transaction = UserTransaction(
                user_id=current_user.id,
                transaction_type='use',
                item_id=item.id,
                amount=0,
                description=f"Applied {item.name} to {target_user.username}."
            )
            db.session.add(transaction)

        # Decrease quantity
        inventory_item.quantity -= 1
        if inventory_item.quantity <= 0:
            db.session.delete(inventory_item)

        # Commit changes
        db.session.commit()
        
        # Determine appropriate message based on domain status
        if active_domain and len(affected_users) > 1:
            message = f'Successfully applied {item.name} to {len(affected_users)} users through Domain Expansion!'
        elif len(affected_users) == 1:
            message = f'Successfully applied {item.name} to {affected_users[0]}!'
        else:
            message = 'No users were affected by the debuff.'

        return jsonify({
            'message': message,
            'affected_users': affected_users
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error applying debuff: {str(e)}")
        return jsonify({'error': 'An error occurred while applying the debuff.'}), 500

# Initialize database after all configurations
init_database()

# Initialize store items
from init_store_items import init_store_items
with app.app_context():
    init_store_items()
    
# Add new store items (Domain Expansion and Shield)
from add_new_store_items import add_new_store_items
with app.app_context():
    add_new_store_items()