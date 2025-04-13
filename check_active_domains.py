
from app import app, db
from models import User, UserBuff
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def check_active_domains():
    with app.app_context():
        # Get all active Domain Expansions
        active_domains = UserBuff.query.filter(
            UserBuff.buff_type == 'domain',
            UserBuff.expires_at > datetime.now(IST)
        ).all()
        
        print("\nActive Domain Expansions:")
        print("========================")
        if active_domains:
            for domain in active_domains:
                user = User.query.get(domain.user_id)
                print(f"User: {user.username}")
                print(f"Effect: {domain.effect_value} HP damage per minute")
                print(f"Expires at: {domain.expires_at}")
                print("------------------------")
        else:
            print("No active Domain Expansions at the moment")

if __name__ == "__main__":
    check_active_domains()
