# initializations for mongodb client and also contains the lifeSpan
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from utils.logger import logger
from model import Nsesa_model as all_models
from core.config import get_db_config


@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager for FastAPI app"""
    mongo_client = None
    try:
        db_cfg = get_db_config()
        mongo_client = AsyncIOMotorClient(db_cfg.mongo_url)
        await init_beanie(
            database=mongo_client.get_default_database(),
            document_models=all_models,
        )
        logger.info(
            f"Connected to MongoDB with {len(all_models)} document models for FJ PAY"
        )

        yield

    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise
    finally:
        if mongo_client is not None:
            logger.info("Disconnecting from MongoDB...")
            mongo_client.close()
            logger.info("Disconnected from MongoDB")
