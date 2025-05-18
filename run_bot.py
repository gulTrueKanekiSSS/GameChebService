import asyncio
import os
import django
<<<<<<< HEAD
from aiohttp import web
import logging
import psutil
import sys
import signal

logging.basicConfig(level=logging.INFO)
=======
import sys
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
>>>>>>> feature/fix-callback-query
logger = logging.getLogger(__name__)

# Указываем путь к settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from bot.bot import start_bot

<<<<<<< HEAD
def terminate_existing_process():
    """Завершает уже запущенные процессы run_bot.py."""
    current_pid = os.getpid()
    current_script = sys.argv[0]

    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['pid'] != current_pid and current_script in proc.info['cmdline']:
                logger.warning(f"Завершаем процесс {proc.info['pid']}.")
                os.kill(proc.info['pid'], signal.SIGTERM)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

async def simple_web_server():
    """Простой HTTP-сервер для Render."""
    async def handle(request):
        return web.Response(text="Bot is running")

    app = web.Application()
    app.router.add_get("/", handle)
    return app

async def main():
    """Основная точка входа."""
    terminate_existing_process()

    try:
        # Запуск бота как фоновая задача
        asyncio.create_task(start_bot())

        # Запуск HTTP-сервера
        port = int(os.getenv("PORT", 8000))
        runner = web.AppRunner(await simple_web_server())
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()

        logger.info(f"HTTP сервер запущен на порту {port}")

        while True:
            await asyncio.sleep(3600)

    except Exception as e:
        logger.error(f"Ошибка в main(): {e}")

if __name__ == "__main__":
    asyncio.run(main())
=======
def create_lock_file():
    """Создает файл блокировки для предотвращения повторного запуска"""
    lock_file = Path("bot.lock")
    if lock_file.exists():
        logger.error("Бот уже запущен. Выход...")
        sys.exit(1)
    lock_file.touch()
    return lock_file

def remove_lock_file(lock_file):
    """Удаляет файл блокировки при завершении работы"""
    try:
        lock_file.unlink()
    except Exception as e:
        logger.error(f"Ошибка при удалении файла блокировки: {e}")

async def main():
    lock_file = create_lock_file()
    try:
        await start_bot()
    except Exception as e:
        logger.error(f"Критическая ошибка в работе бота: {e}")
    finally:
        remove_lock_file(lock_file)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
>>>>>>> feature/fix-callback-query
