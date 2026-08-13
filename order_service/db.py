import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from shared.config import settings

logger = logging.getLogger("order.db")

Base = declarative_base()

# Attempt connection to Postgres Async Engine
try:
    engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
except Exception as e:
    logger.warning(f"PostgreSQL async engine init deferred: {e}")
    engine = None
    async_session = None


async def init_db():
    if engine:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("PostgreSQL database tables created/verified")
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed at startup: {e}. Using in-memory storage fallback.")
