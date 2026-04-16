"""Redis helpers for caching API key metadata."""

import redis.asyncio as redis
from datetime import datetime
from config.config import settings
from common.logger import get_logger

logger = get_logger(__name__)

# Redis Connection (using CELERY_RESULT_BACKEND which is the Redis URL)
redis_client = redis.from_url(
    settings.CELERY_RESULT_BACKEND,
    decode_responses=True
)

# Default TTL to keep recent entries hot (seconds)
CACHE_TTL_SECONDS = settings.CACHE_TTL_SECONDS

#  Cache API key using private key
async def cache_api_key(hashed_private_key: str, expires_at: str, is_active: bool, ttl_seconds: int = CACHE_TTL_SECONDS):
    """Store key metadata in Redis with TTL/expiry."""
    try:
        key_name = f"api_key:{hashed_private_key}"
        mapping = {
            "expires_at": expires_at,
            "is_active": "true" if is_active else "false"
        }
        await redis_client.hset(
            key_name,
            mapping=mapping
        )
        # Set TTL to keep only recent/frequent keys
        try:
            if ttl_seconds and ttl_seconds > 0:
                await redis_client.expire(key_name, ttl_seconds)
            # If expires_at is sooner, prefer absolute expiry
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            await redis_client.expireat(key_name, int(expires_dt.timestamp()))
        except Exception:
            logger.warning(f" [Redis] Unable to set TTL for key (hash={hashed_private_key[:8]}...)")
        logger.info(f" Cached API key (hash={hashed_private_key[:8]}...) (active={is_active}, expires_at={expires_at})")

    except Exception as e:
        logger.error(f" [Redis] Failed to cache API key: {str(e)}")

#  Retrieve API key from Redis using private key
async def get_api_key_from_cache(hashed_private_key: str, refresh_ttl: bool = True, ttl_seconds: int = CACHE_TTL_SECONDS):
    """Fetch key metadata from Redis, optionally refreshing TTL."""
    try:
        key_name = f"api_key:{hashed_private_key}"
        data = await redis_client.hgetall(key_name)
        if not data:
            logger.warning(f" API key (hash={hashed_private_key[:8]}...) not found in Redis")
            return None

        # Refresh TTL to keep frequently used entries hot
        if refresh_ttl and ttl_seconds and ttl_seconds > 0:
            await redis_client.expire(key_name, ttl_seconds)
        logger.info(f" Retrieved API key from Redis (hash={hashed_private_key[:8]}...) (active={data['is_active']})")
        return data

    except Exception as e:
        logger.error(f" [Redis] Failed to get API key: {str(e)}")
        return None

# Deactivate a single API key in Redis using hashed private key
async def deactivate_api_key_in_cache(hashed_private_key: str):
    """Mark cached key as inactive if present."""
    try:
        key_name = f"api_key:{hashed_private_key}"
        exists = await redis_client.exists(key_name)
        if exists:
            await redis_client.hset(key_name, "is_active", "false")
            logger.info(f" Deactivated API key in Redis (hash={hashed_private_key[:8]}...)")
        else:
            logger.warning(f" API key (hash={hashed_private_key[:8]}...) not found in Redis")
    except Exception as e:
        logger.error(f" [Redis] Failed to deactivate API key: {str(e)}")
