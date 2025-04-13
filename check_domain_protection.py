
from app import app, db
from models import User, UserBuff
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def check_protected_users():
    with app.app_context():
        # Get all users with active Ultimate Shields
        protected_users = User.query.join(UserBuff).filter(
            UserBuff.buff_type == 'shield',
            UserBuff.effect_value == 1,  # Ultimate Shield
            UserBuff.expires_at > datetime.now(IST)
        ).all()
        
        print("\nUsers protected from Domain Expansion:")
        print("=====================================")
        if protected_users:
            for user in protected_users:
                shield = UserBuff.query.filter_by(
                    user_id=user.id,
                    buff_type='shield',
                    effect_value=1
                ).first()
                print(f"User: {user.username}")
                print(f"Shield expires at: {shield.expires_at}")
                print("-------------------------------------")
        else:
            print("No users are currently protected from Domain Expansion")

if __name__ == "__main__":
    check_protected_users()
