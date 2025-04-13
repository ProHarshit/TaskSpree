from app import app, db
from models import StoreItem
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def add_new_store_items():
    """
    Add the new Domain Expansion and Shield items to the store
    """
    from app import app, db, logger
    from models import StoreItem
    
    try:
        with app.app_context():
            # Check if the items already exist
            domain_expansion = StoreItem.query.filter_by(name='Domain Expansion').first()
            if domain_expansion:
                logger.info("Domain Expansion item already exists, skipping.")
            else:
                # Create Domain Expansion item
                domain_expansion = StoreItem(
                    name='Domain Expansion',
                    description='Activates a domain that deals 40 HP damage every minute for 24 minutes to all users except you. Any debuffs you apply during this period affect all users.',
                    price=500,
                    item_type='domain',  # New item type
                    item_tier='ultimate',
                    effect_value=40,  # Hourly damage
                    icon='target'  # Feather icon for target/domain
                )
                db.session.add(domain_expansion)
                db.session.commit()
                logger.info("Added Domain Expansion item to store")
            
            # Check if shield items already exist
            normal_shield = StoreItem.query.filter_by(name='Normal Shield').first()
            advanced_shield = StoreItem.query.filter_by(name='Advanced Shield').first()
            ultimate_shield = StoreItem.query.filter_by(name='Ultimate Shield').first()
            
            # Add shield items if they don't exist
            if not normal_shield:
                normal_shield = StoreItem(
                    name='Normal Shield',
                    description='Protects against all debuffs for 1 day. Cannot protect against Domain Expansion.',
                    price=50,
                    item_type='shield',  # New item type
                    item_tier='normal',
                    effect_value=24,  # Hours of protection
                    icon='shield'
                )
                db.session.add(normal_shield)
                logger.info("Added Normal Shield item to store")
            
            if not advanced_shield:
                advanced_shield = StoreItem(
                    name='Advanced Shield',
                    description='Protects against all debuffs for 2 days. Cannot protect against Domain Expansion.',
                    price=100,
                    item_type='shield',
                    item_tier='advanced',
                    effect_value=48,  # Hours of protection
                    icon='shield'
                )
                db.session.add(advanced_shield)
                logger.info("Added Advanced Shield item to store")
            
            if not ultimate_shield:
                ultimate_shield = StoreItem(
                    name='Ultimate Shield',
                    description='Protects against all debuffs for 3 days, including Domain Expansion effects.',
                    price=300,
                    item_type='shield',
                    item_tier='ultimate',
                    effect_value=72,  # Hours of protection
                    icon='shield'
                )
                db.session.add(ultimate_shield)
                logger.info("Added Ultimate Shield item to store")
            
            # Commit all changes
            db.session.commit()
            logger.info("Successfully added new store items")
            
            # Return the number of items added
            return {
                'domain_expansion': domain_expansion is None,
                'normal_shield': normal_shield is None,
                'advanced_shield': advanced_shield is None,
                'ultimate_shield': ultimate_shield is None
            }
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding new store items: {str(e)}")
        raise

if __name__ == "__main__":
    add_new_store_items()