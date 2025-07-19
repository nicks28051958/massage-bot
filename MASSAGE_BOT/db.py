from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from config import DB_PATH
from models import Base

DATABASE_URL = f'sqlite+aiosqlite:///{DB_PATH}'
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Ensure database schema is up to date."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        result = await conn.execute(text("PRAGMA table_info(massage_types)"))
        columns = [row[1] for row in result.fetchall()]
        if "image" not in columns:
            await conn.execute(text("ALTER TABLE massage_types ADD COLUMN image VARCHAR"))

