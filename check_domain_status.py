
from app import app, db
from models import User, UserBuff
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def check_and_clean_domain_status(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"User {username} not found")
            return

        # Check for active domain expansions
        active_domains = UserBuff.query.filter_by(
            user_id=user.id,
            buff_type='domain'
        ).filter(UserBuff.expires_at > datetime.now(IST)).all()
        
        print(f"\nDomain Status for {username}:")
        print("========================")
        
        if active_domains:
            print("Active Domain Expansions found:")
            for domain in active_domains:
                print(f"Effect: {domain.effect_value} HP damage per minute")
                print(f"Expires at: {domain.expires_at}")
                
                # Clean up the domain effect
                db.session.delete(domain)
            
            db.session.commit()
            print("\nCleaned up all domain effects.")
        else:
            print("No active Domain Expansions found.")

if __name__ == "__main__":
    check_and_clean_domain_status("Q")  # Replace with actual username if different
