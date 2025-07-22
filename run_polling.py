import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quest_bot.settings')
import django
django.setup()

import asyncio
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot.bot import dp, register_handlers

load_dotenv(override=True)
token = os.getenv('TELEGRAM_BOT_TOKEN')
if not token:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не найден в .env")

bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
register_handlers(dp)

async def main():
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main()) 