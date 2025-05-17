import asyncio
import os
import django
from aiohttp import web

# Указываем путь к settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from bot.bot import start_bot  # Импорт твоей start_bot функции

async def simple_web_server():
    """Простой HTTP-сервер для Render."""
    async def handle(request):
        return web.Response(text="Bot is running")

    app = web.Application()
    app.router.add_get("/", handle)
    return app

async def main():
    """Основная точка входа."""
    # Запуск бота
    asyncio.create_task(start_bot())

    # Запуск HTTP-сервера
    port = int(os.getenv("PORT", 8000))
    runner = web.AppRunner(await simple_web_server())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # Поддерживаем приложение в живом состоянии
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
