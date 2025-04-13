from app import app, db, user_collection
from models import User

def fix_exp_sync():
    """
    Sync EXP values between SQL database and ChromaDB,
    prioritizing the higher value to avoid losing progress.
    """
    with app.app_context():
        users = User.query.all()
        
        print("\nBeginning EXP sync between SQL database and ChromaDB...")
        print("======================================================")
        
        try:
            # Get all user stats from ChromaDB
            result = user_collection.get(include=['metadatas'])
            
            for user in users:
                print(f"\nProcessing user: {user.username} (ID: {user.id})")
                print(f"Current SQL DB values: Level {user.level}, EXP {user.exp}, Max HP {user.max_hp}")
                
                # Find all entries for this user in ChromaDB
                user_entries = [entry for entry in result['metadatas'] 
                              if entry.get('user_id') == str(user.id)]
                
                if not user_entries:
                    print(f"No ChromaDB entries found for user {user.username}")
                    continue
                
                # Find entry with highest lifetime EXP
                highest_entry = max(user_entries, key=lambda x: x.get('lifetime_exp', 0))
                chroma_exp = highest_entry.get('lifetime_exp', 0)
                
                print(f"Highest ChromaDB EXP value: {chroma_exp}")
                
                # Compare and update to the higher value
                if chroma_exp > user.exp:
                    print(f"Updating SQL database: EXP {user.exp} → {chroma_exp}")
                    user.exp = chroma_exp
                    # Recalculate level
                    calculated_level = (user.exp // 50) + 1
                    if user.level != calculated_level:
                        print(f"Updating level: {user.level} → {calculated_level}")
                        user.level = calculated_level
                    
                    # Update max_hp based on new level
                    new_max_hp = 500 + (user.level - 1) * 10
                    if user.max_hp != new_max_hp:
                        print(f"Updating max HP: {user.max_hp} → {new_max_hp}")
                        user.max_hp = new_max_hp
                        # Cap current HP at max_hp if needed
                        if user.hp > user.max_hp:
                            print(f"Capping HP: {user.hp} → {user.max_hp}")
                            user.hp = user.max_hp
                
                elif user.exp > chroma_exp:
                    print(f"Updating ChromaDB: EXP {chroma_exp} → {user.exp}")
                    # Update all entries for this user in ChromaDB
                    for entry in user_entries:
                        # Only update if lower than SQL value
                        if entry.get('lifetime_exp', 0) < user.exp:
                            entry['lifetime_exp'] = user.exp
                            if 'monthly_exp' in entry and entry['monthly_exp'] < user.exp:
                                entry['monthly_exp'] = user.exp
                            
                            try:
                                user_collection.update(
                                    ids=[f"user_{user.id}" if entry.get('id') is None else entry.get('id')],
                                    metadatas=[entry]
                                )
                                print(f"Updated ChromaDB entry ID: {entry.get('id', f'user_{user.id}')}")
                            except Exception as e:
                                print(f"Error updating ChromaDB: {str(e)}")
                else:
                    print("EXP values are already in sync")
        
            # Commit SQL changes
            db.session.commit()
            print("\nEXP sync completed successfully.")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during EXP sync: {str(e)}")

if __name__ == "__main__":
    fix_exp_sync()