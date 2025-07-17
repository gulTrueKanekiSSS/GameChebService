import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quest_bot.settings')

import django
django.setup()

import asyncio
from bot.bot import start_bot
asyncio.run(start_bot())