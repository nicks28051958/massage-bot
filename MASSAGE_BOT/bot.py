import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import admin, calendar, client

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

admin.register_admin_handlers(dp)
calendar.register_calendar_handlers(dp)
client.register_client_handlers(dp)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print('Бот запущен!')
    async def main():
        await dp.start_polling(bot)
    asyncio.run(main())
