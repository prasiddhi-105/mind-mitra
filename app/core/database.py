from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global database client
client: Optional[AsyncIOMotorClient] = None
database = None


async def init_db():
    """Initialize database connection"""
    global client, database
    
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        database = client[settings.DATABASE_NAME]
        
        # Test connection
        await client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Create indexes
        await create_indexes()
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise


async def create_indexes():
    """Create database indexes"""
    try:
        # Users collection indexes
        await database.users.create_index("email", unique=True)
        await database.users.create_index("created_at")
        
        # Journal entries indexes
        await database.journal_entries.create_index("user_id")
        await database.journal_entries.create_index([("user_id", 1), ("created_at", -1)])
        await database.journal_entries.create_index("created_at")
        await database.journal_entries.create_index([("user_id", 1), ("emotion_label", 1)])
        
        # SOS alerts indexes
        await database.sos_alerts.create_index("user_id")
        await database.sos_alerts.create_index([("user_id", 1), ("created_at", -1)])
        await database.sos_alerts.create_index("status")
        
        # Chat history indexes
        await database.chat_history.create_index("user_id")
        await database.chat_history.create_index([("user_id", 1), ("created_at", -1)])
        
        # Emergency contacts indexes
        await database.emergency_contacts.create_index("user_id")

        # Depression flags indexes
        await database.depression_flags.create_index("user_id")
        await database.depression_flags.create_index([("user_id", 1), ("created_at", -1)])
        await database.depression_flags.create_index("created_at")
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        raise


async def close_db():
    """Close database connection"""
    global client
    if client:
        client.close()
        logger.info("Database connection closed")


def get_database():
    """Get database instance"""
    return database


def get_collection(collection_name: str):
    """Get collection instance"""
    if database is None:
        raise RuntimeError("Database not initialized")
    return database[collection_name]


def get_db():
    """Dependency returning the database instance"""
    if database is None:
        raise RuntimeError("Database not initialized")
    return database 