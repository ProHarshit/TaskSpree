"""
Script to manually run a full database synchronization between ChromaDB and SQL
"""

import logging
from sync_databases import sync_all_databases

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting manual database synchronization...")
    
    # Run the synchronization
    sync_all_databases()
    
    logger.info("Manual database synchronization completed")