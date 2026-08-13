import hashlib
import json
import logging
from typing import Optional, Tuple
import redis.asyncio as redis

from shared.config import settings

logger = logging.getLogger("tts.cache")

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=False  # Binary for audio bytes
)

# 7 Days TTL for cached voice audio
CACHE_TTL = 7 * 24 * 3600


class TTSCache:
    def _compute_key(self, text: str, voice_id: str, voice_settings: dict) -> str:
        data_str = f"{text}:{voice_id}:{json.dumps(voice_settings, sort_keys=True)}"
        hashed = hashlib.sha256(data_str.encode("utf-8")).hexdigest()
        return f"tts_cache:{hashed}"

    async def get(self, text: str, voice_id: str, voice_settings: dict) -> Optional[bytes]:
        if not settings.ELEVENLABS_CACHE_ENABLED:
            return None
        key = self._compute_key(text, voice_id, voice_settings)
        try:
            audio_bytes = await redis_client.get(key)
            if audio_bytes:
                logger.info(f"TTS Cache HIT for text hash {key[:15]}")
                return audio_bytes
        except Exception as e:
            logger.error(f"Redis TTS cache get error: {e}")
        return None

    async def set(self, text: str, voice_id: str, voice_settings: dict, audio_bytes: bytes) -> None:
        if not settings.ELEVENLABS_CACHE_ENABLED:
            return
        key = self._compute_key(text, voice_id, voice_settings)
        try:
            await redis_client.set(key, audio_bytes, ex=CACHE_TTL)
            logger.info(f"TTS Cache STORED for text hash {key[:15]}")
        except Exception as e:
            logger.error(f"Redis TTS cache set error: {e}")


tts_cache = TTSCache()
