import  asyncio
from aiogram import Bot, Dispatcher
from handlers.business import router
from dotenv import load_dotenv
import os
from scheduler import start_scheduler

load_dotenv()

BOT_TOKEN = os.getenv("TG_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)

async def main():
    start_scheduler(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
