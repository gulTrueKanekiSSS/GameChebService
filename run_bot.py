import asyncio
import os
import sys
import signal
import logging
import psutil

from pathlib import Path
from aiohttp import web, hdrs
from django.core.wsgi import get_wsgi_application
from aiohttp_wsgi import WSGIHandler
import drf_yasg

# 1) Настроим Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quest_bot.settings')
import django  # noqa: E402
django.setup()

# 2) Monkey-patch Request.host, чтобы strip’ить ":порт" в любых случаях
def _strip_port_host(self):
    raw = self._message.headers.get(hdrs.HOST, '')
    return raw.split(':', 1)[0]

web.Request.host = property(_strip_port_host)

class FixedWSGIHandler(WSGIHandler):
    def prepare_environ(self, request):
        """
        Убираем порт из HTTP_HOST для Django
        """
        environ = super().prepare_environ(request)
        raw_host = request.headers.get(hdrs.HOST, '')
        host = raw_host.split(':', 1)[0]
        environ['HTTP_HOST'] = host
        environ['SERVER_NAME'] = host
        environ['SERVER_PORT'] = os.getenv('PORT', '8000')
        return environ

# Получаем WSGI-приложение Django и обёртку для aiohttp
django_app = get_wsgi_application()
wsgi_handler = FixedWSGIHandler(django_app)

# Путь до static drf-yasg (для Swagger UI)
DRF_YASG_STATIC = Path(drf_yasg.__file__).resolve().parent / 'static' / 'drf-yasg'

# Путь до вашего index.html WebApp
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "webapp_static"
INDEX_HTML = STATIC_DIR / "index.html"

from bot.bot import start_bot  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def terminate_existing_process():
    """Завершает уже запущенные копии run_bot.py."""
    current_pid = os.getpid()
    current_script = sys.argv[0]
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            pid = proc.info.get('pid')
            cmdline = proc.info.get('cmdline') or []
            if pid != current_pid and isinstance(cmdline, list) and current_script in cmdline:
                logger.warning(f"Завершаем старый процесс {pid}")
                os.kill(pid, signal.SIGTERM)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

async def simple_web_server():
    app = web.Application()

    # 1) Health-check
    async def handle_root(request):
        return web.Response(text="Bot is running")
    app.router.add_get('/', handle_root)

    # 2) Mount Django WSGI under /docs
    docs_app = web.Application()
    # Serve static files for Swagger UI
    docs_app.router.add_static(
        '/static/drf-yasg/',
        str(DRF_YASG_STATIC),
        show_index=False
    )
    docs_app.router.add_route('*', '/{path_info:.*}', wsgi_handler)
    app.add_subapp('/docs', docs_app)

    # 3) Mount API router under /api
    api_app = web.Application()
    api_app.router.add_route('*', '/{path_info:.*}', wsgi_handler)
    app.add_subapp('/api', api_app)

    # 4) Catch-all for SPA
    async def handle_webapp(request):
        init_data = request.query.get('initData')
        if not init_data:
            return web.Response(text="❌ Не все параметры получены!", content_type='text/html')
        return web.FileResponse(INDEX_HTML)
    app.router.add_route('*', '/{tail:.*}', handle_webapp)

    return app

async def main():
    terminate_existing_process()
    # 1) Start bot in background
    asyncio.create_task(start_bot())

    # 2) Start aiohttp server
    port = int(os.getenv('PORT', 8000))
    runner = web.AppRunner(await simple_web_server())
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"aiohttp proxy запущен на 0.0.0.0:{port}")

    # 3) Keep alive
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass



if __name__ == '__main__':
    asyncio.run(main())
