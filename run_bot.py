import asyncio
import os
import logging
from pathlib import Path
from aiohttp import web, hdrs
from django.core.wsgi import get_wsgi_application
from aiohttp_wsgi import WSGIHandler
import drf_yasg
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1) Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quest_bot.settings')
import django  # noqa: E402
django.setup()

# 2) Инициализация бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    logger.error('TELEGRAM_TOKEN не найден в окружении')
    raise SystemExit(1)

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
# Импорт диспетчера с зарегистрированными хендлерами
from bot.bot import dp

# Monkey-patch Request.host, чтобы убрать ":порт"
def _strip_port_host(self):
    raw = self._message.headers.get(hdrs.HOST, '')
    return raw.split(':', 1)[0]
web.Request.host = property(_strip_port_host)

# WSGI обёртка для Django
class FixedWSGIHandler(WSGIHandler):
    def prepare_environ(self, request):
        environ = super().prepare_environ(request)
        raw_host = request.headers.get(hdrs.HOST, '')
        host = raw_host.split(':', 1)[0]
        environ['HTTP_HOST'] = host
        environ['SERVER_NAME'] = host
        environ['SERVER_PORT'] = os.getenv('PORT', '8000')
        return environ

django_app = get_wsgi_application()
wsgi_handler = FixedWSGIHandler(django_app)

# Статика DRF-YASG
DRF_YASG_STATIC = Path(drf_yasg.__file__).resolve().parent / 'static' / 'drf-yasg'
# Статика SPA
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "webapp_static"
INDEX_HTML = STATIC_DIR / "index.html"

async def simple_web_server():
    app = web.Application()

    # Health-check
    async def handle_root(request):
        return web.Response(text="Bot is running")
    app.router.add_get('/', handle_root)

    # Swagger UI
    docs_app = web.Application()
    docs_app.router.add_static(
        '/static/drf-yasg/', str(DRF_YASG_STATIC), show_index=False
    )
    docs_app.router.add_route('*', '/{path_info:.*}', wsgi_handler)
    app.add_subapp('/docs', docs_app)

    # API-приложение
    api_app = web.Application()
    api_app.router.add_route('*', '/{path_info:.*}', wsgi_handler)
    app.add_subapp('/api', api_app)

    # Телеграм webhook
    from aiogram import types

    async def handle_telegram_webhook(request):
        payload = await request.json()
        # Преобразуем dict в Update
        update = types.Update(**payload)
        await dp.process_update(update, bot=bot)
        return web.Response(text="OK")

    app.router.add_post('/telegram/webhook/', handle_telegram_webhook)

    # Catch-all для SPA
    async def handle_webapp(request):
        init_data = request.query.get('initData')
        if not init_data:
            return web.Response(text="❌ Не все параметры получены!", content_type='text/html')
        return web.FileResponse(INDEX_HTML)
    app.router.add_route('*', '/{tail:.*}', handle_webapp)

    return app

async def main():
    # Установка webhook
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    if not WEBHOOK_URL:
        logger.error('WEBHOOK_URL не задан в окружении')
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        logger.info(f'Webhook установлен на {WEBHOOK_URL}')

    # Запуск HTTP-сервера
    port = int(os.getenv('PORT', 8000))
    runner = web.AppRunner(await simple_web_server())
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f'aiohttp proxy запущен на 0.0.0.0:{port}')

    # Keep alive
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass

if __name__ == '__main__':
    asyncio.run(main())
