from app import user_collection
import datetime
import pytz
import logging

# Set ChromaDB logging to ERROR level to reduce noise
logging.getLogger('chromadb').setLevel(logging.ERROR)

IST = pytz.timezone('Asia/Kolkata')

def update_user_j_exp():
    try:
        print('\n' + '='*50)
        print('Starting User J exp update...')
        print('='*50 + '\n')

        # Update User J's stats
        user_stats = {
            'user_id': '1',  # User J's ID
            'monthly_exp': 1200,
            'lifetime_exp': 1200,
            'last_reset': datetime.datetime.now(IST).strftime('%Y-%m')
        }

        # Update in ChromaDB
        user_collection.update(
            ids=['stats_1'],  # User J's stats ID
            documents=['user_stats'],
            metadatas=[user_stats],
            embeddings=[[0.0] * 384]  # Provide dummy embedding
        )
        print('Updated User J\'s monthly exp to 1200 successfully')

        # Verify the update
        print('\nVerifying update...')
        result = user_collection.get(
            where={"user_id": "1"},
            include=['metadatas']
        )
        if result and result['metadatas']:
            updated_stats = result['metadatas'][0]
            print(f'\nVerification - Current User J stats:')
            print(f'Monthly EXP: {updated_stats.get("monthly_exp")}')
            print(f'Lifetime EXP: {updated_stats.get("lifetime_exp")}')
            print(f'Last Reset: {updated_stats.get("last_reset")}')

            if updated_stats.get('monthly_exp') == 1200:
                print('\n✓ Monthly exp successfully set to 1200')
            else:
                print('\n✗ Monthly exp update failed')
        else:
            print('\n✗ Could not verify update - User stats not found')

        print('\n' + '='*50)

    except Exception as e:
        print(f'\nError updating exp: {str(e)}')

if __name__ == '__main__':
    update_user_j_exp()