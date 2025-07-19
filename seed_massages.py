import asyncio
from sqlalchemy import select
from MASSAGE_BOT.db import async_session, init_db
from MASSAGE_BOT.models import MassageType

# Базовые виды массажа
basic_massages = [
    {
        "name": "Классический массаж",
        "duration": 60,
        "price": 1500.0,
        "description": "Расслабляющий общий массаж"
    },
    {
        "name": "Массаж спины",
        "duration": 45,
        "price": 1200.0,
        "description": "Проработка мышц спины"
    },
    {
        "name": "Антицеллюлитный массаж",
        "duration": 40,
        "price": 1700.0,
        "description": "Улучшает тонус кожи"
    },
]

async def seed():
    async with async_session() as session:
        for massage in basic_massages:
            result = await session.execute(
                select(MassageType).where(MassageType.name == massage["name"])
            )
            if result.scalar_one_or_none() is None:
                session.add(MassageType(**massage))
        await session.commit()

if __name__ == "__main__":
    async def main():
        await init_db()
        await seed()

    asyncio.run(main())
