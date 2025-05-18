import asyncio
import os
import django
import sys
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Указываем путь к settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from bot.bot import start_bot

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
