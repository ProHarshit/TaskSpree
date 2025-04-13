from app import app, db, user_collection
from models import User

def debug_max_hp():
    with app.app_context():
        # Get all users
        users = User.query.all()
        
        print("Username, Level, Max HP, Expected Max HP, EXP, Calculated Level:")
        print("===============================================================")
        
        for user in users:
            # Check current level calculation
            calculated_level = (user.exp // 50) + 1
            expected_max_hp = 500 + (calculated_level - 1) * 10
            
            print(f"{user.username}: Level {user.level}, Max HP {user.max_hp}, Expected HP {expected_max_hp}, EXP {user.exp}, Calculated Level {calculated_level}")
            
            # Fix level if it doesn't match calculation
            if user.level != calculated_level:
                print(f"Fixing level for {user.username} from {user.level} to {calculated_level}")
                user.level = calculated_level
            
            # Update the max HP based on the correct level
            new_max_hp = 500 + (user.level - 1) * 10
            if user.max_hp != new_max_hp:
                print(f"Fixing max HP for {user.username} from {user.max_hp} to {new_max_hp}")
                user.max_hp = new_max_hp
                # Update HP to not exceed max HP
                if user.hp > user.max_hp:
                    user.hp = user.max_hp
        
        # Commit changes
        db.session.commit()
        print("Level and Max HP values fixed successfully!")
        
        # Check ChromaDB stats
        print("\nChecking ChromaDB stats:")
        print("=======================")
        
        try:
            result = user_collection.get(include=['metadatas'])
            for stats in result['metadatas']:
                if 'user_id' in stats:
                    user_id = stats['user_id']
                    lifetime_exp = stats.get('lifetime_exp', 0)
                    monthly_exp = stats.get('monthly_exp', 0)
                    
                    # Calculate expected level from lifetime EXP
                    calc_level = (lifetime_exp // 50) + 1
                    
                    print(f"User ID: {user_id}, Monthly EXP: {monthly_exp}, Lifetime EXP: {lifetime_exp}, Calculated Level: {calc_level}")
                    
                    # Find the user in the database
                    user = User.query.filter_by(id=int(user_id)).first()
                    if user:
                        print(f"  Database User: {user.username}, Level: {user.level}, EXP: {user.exp}")
                        
                        # Check if database EXP matches ChromaDB lifetime EXP
                        if user.exp != lifetime_exp:
                            print(f"  EXP mismatch: DB={user.exp}, ChromaDB={lifetime_exp}")
        except Exception as e:
            print(f"Error checking ChromaDB stats: {str(e)}")

if __name__ == "__main__":
    debug_max_hp()