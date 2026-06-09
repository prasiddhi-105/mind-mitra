import asyncio
import logging
from app.core.database import init_db, close_db, get_collection
from app.core.logging import setup_logging
import uuid
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

async def migrate():
    setup_logging()
    await init_db()
    
    collection = get_collection("journal_entries")
    cursor = collection.find({})
    
    migrated_count = 0
    total_count = 0
    
    async for doc in cursor:
        total_count += 1
        updates = {}
        
        # 1. Ensure `id` is a string
        # Older SQL docs had integer `id`, Mongo typically uses `_id`
        if "id" not in doc:
            updates["id"] = str(uuid.uuid4())
        elif isinstance(doc["id"], int):
            updates["id"] = str(doc["id"])
            
        # 2. Ensure `user_id` is a string
        if "user_id" in doc and isinstance(doc["user_id"], int):
            updates["user_id"] = str(doc["user_id"])
            
        # 3. Ensure `created_at` exists
        if "created_at" not in doc:
            if "date" in doc and doc["date"]:
                updates["created_at"] = doc["date"]
            else:
                updates["created_at"] = doc["_id"].generation_time.replace(tzinfo=None)
                
        # 4. Ensure `emotion_analyzed` exists
        if "emotion_analyzed" not in doc:
            updates["emotion_analyzed"] = False
            
        if updates:
            await collection.update_one(
                {"_id": doc["_id"]},
                {"$set": updates}
            )
            migrated_count += 1
            
    logger.info(f"Migration complete. Migrated {migrated_count} out of {total_count} documents.")
    await close_db()

if __name__ == "__main__":
    asyncio.run(migrate())
