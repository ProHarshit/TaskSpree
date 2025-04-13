from app import db
from models import StoreItem
import logging

logger = logging.getLogger(__name__)

def init_store_items():
    """Initialize store items with potions of different types and tiers"""
    try:
        # Check if store items already exist
        existing_items = StoreItem.query.count()
        if existing_items > 0:
            logger.info(f"Store items already exist ({existing_items} items found). Skipping initialization.")
            return
        
        logger.info("Initializing store items...")
        
        # Define healing potions (restore HP)
        healing_items = [
            {
                'name': 'Minor Healing Potion',
                'description': 'Restore 50 HP when used.',
                'price': 20,
                'item_type': 'healing',
                'item_tier': 'normal',
                'effect_value': 50,
                'icon': 'heart'
            },
            {
                'name': 'Standard Healing Potion',
                'description': 'Restore 100 HP when used.',
                'price': 40,
                'item_type': 'healing',
                'item_tier': 'normal',
                'effect_value': 100,
                'icon': 'heart'
            },
            {
                'name': 'Greater Healing Potion',
                'description': 'Restore 200 HP when used.',
                'price': 75,
                'item_type': 'healing',
                'item_tier': 'advanced',
                'effect_value': 200,
                'icon': 'award'
            },
            {
                'name': 'Supreme Healing Potion',
                'description': 'Restore 400 HP when used.',
                'price': 125,
                'item_type': 'healing',
                'item_tier': 'ultimate',
                'effect_value': 400,
                'icon': 'zap'
            }
        ]
        
        # Define buff potions (increase EXP gain temporarily)
        buff_items = [
            {
                'name': 'Minor Focus Potion',
                'description': 'Increase EXP gain by 10% for 24 hours.',
                'price': 30,
                'item_type': 'buff',
                'item_tier': 'normal',
                'effect_value': 10,
                'icon': 'trending-up'
            },
            {
                'name': 'Standard Focus Potion',
                'description': 'Increase EXP gain by 25% for 24 hours.',
                'price': 60,
                'item_type': 'buff',
                'item_tier': 'normal',
                'effect_value': 25,
                'icon': 'trending-up'
            },
            {
                'name': 'Greater Focus Potion',
                'description': 'Increase EXP gain by 50% for 24 hours.',
                'price': 100,
                'item_type': 'buff',
                'item_tier': 'advanced',
                'effect_value': 50,
                'icon': 'zap'
            },
            {
                'name': 'Supreme Focus Potion',
                'description': 'Increase EXP gain by 100% for 24 hours.',
                'price': 175,
                'item_type': 'buff',
                'item_tier': 'ultimate',
                'effect_value': 100,
                'icon': 'star'
            }
        ]
        
        # Define debuff potions (decrease EXP gain temporarily for other users)
        debuff_items = [
            {
                'name': 'Minor Distraction Potion',
                'description': 'Decrease target user\'s EXP gain by 10% for 24 hours.',
                'price': 40,
                'item_type': 'debuff',
                'item_tier': 'normal',
                'effect_value': 10,
                'icon': 'trending-down'
            },
            {
                'name': 'Standard Distraction Potion',
                'description': 'Decrease target user\'s EXP gain by 20% for 24 hours.',
                'price': 75,
                'item_type': 'debuff',
                'item_tier': 'normal',
                'effect_value': 20,
                'icon': 'trending-down'
            },
            {
                'name': 'Greater Distraction Potion',
                'description': 'Decrease target user\'s EXP gain by 35% for 24 hours.',
                'price': 120,
                'item_type': 'debuff',
                'item_tier': 'advanced',
                'effect_value': 35,
                'icon': 'cloud-rain'
            },
            {
                'name': 'Supreme Distraction Potion',
                'description': 'Decrease target user\'s EXP gain by 50% for 24 hours.',
                'price': 200,
                'item_type': 'debuff',
                'item_tier': 'ultimate',
                'effect_value': 50,
                'icon': 'cloud-lightning'
            }
        ]
        
        # Define recovery items (fully restore HP and remove debuffs)
        recovery_items = [
            {
                'name': 'Revival Potion',
                'description': 'Fully restore HP and remove all debuffs.',
                'price': 150,
                'item_type': 'recovery',
                'item_tier': 'advanced',
                'effect_value': 0,  # Special case - restores to max HP
                'icon': 'shield'
            },
            {
                'name': 'Phoenix Potion',
                'description': 'Fully restore HP, remove all debuffs and grant a 10% EXP buff for 24 hours.',
                'price': 250,
                'item_type': 'recovery',
                'item_tier': 'ultimate',
                'effect_value': 10,  # For the buff effect
                'icon': 'feather'
            }
        ]
        
        # Combine all items
        all_items = healing_items + buff_items + debuff_items + recovery_items
        
        # Add items to database
        for item_data in all_items:
            item = StoreItem(**item_data)
            db.session.add(item)
        
        db.session.commit()
        logger.info(f"Successfully initialized {len(all_items)} store items")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error initializing store items: {str(e)}")
        raise

if __name__ == "__main__":
    init_store_items()