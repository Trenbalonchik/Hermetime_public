import asyncio, os
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import Message
from dotenv import load_dotenv
from db import link_telegram_chat

load_dotenv()
bot = Bot(token=os.getenv("NOTIFY_BOT_TOKEN"))
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message, command: CommandObject):
    token = command.args
    if not token:
        await message.answer("Цей бот лише для підписки на нагадування із сайту Parlour.")
        return
    if link_telegram_chat(token, message.chat.id):
        await message.answer("✅ Підписка активована!")
    else:
        await message.answer("⚠️ Посилання недійсне. Спробуйте ще раз із сайту.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())