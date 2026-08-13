import json
import logging
from typing import Optional
import redis.asyncio as redis
from datetime import datetime

from shared.config import settings
from shared.models import SessionState, ConversationState

logger = logging.getLogger("orchestrator.session_store")

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)


class SessionStore:
    def __init__(self):
        self.ttl = settings.SESSION_TTL_SECONDS

    async def get_or_create(self, user_phone: str, forced_lang: Optional[str] = None) -> SessionState:
        session_key = f"session:{user_phone}"
        try:
            raw_data = await redis_client.get(session_key)
            if raw_data:
                data = json.loads(raw_data)
                session = SessionState(**data)
                session.last_active = datetime.utcnow().isoformat()
                if forced_lang:
                    session.language = forced_lang
                return session
        except Exception as e:
            logger.error(f"Error loading session for {user_phone}: {e}")

        # Create new session
        new_session = SessionState(
            session_id=f"sess_{user_phone[-4:]}_{int(datetime.utcnow().timestamp())}",
            user_phone=user_phone,
            language=forced_lang or "hi-IN",
            state=ConversationState.IDLE,
        )
        await self.save(new_session)
        return new_session

    async def save(self, session: SessionState) -> None:
        session_key = f"session:{session.user_phone}"
        session.last_active = datetime.utcnow().isoformat()

        # Prune conversation history to last 10 turns
        if len(session.conversation_history) > 10:
            session.conversation_history = session.conversation_history[-10:]

        try:
            raw_data = session.model_dump_json()
            await redis_client.set(session_key, raw_data, ex=self.ttl)
        except Exception as e:
            logger.error(f"Failed to save session to Redis for {session.user_phone}: {e}")


session_store = SessionStore()
