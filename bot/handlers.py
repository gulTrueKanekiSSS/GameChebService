from aiogram import Router
from . import route_handlers
from . import admin_commands

def get_main_router():
    """Создает и возвращает главный роутер со всеми обработчиками"""
    main_router = Router()
    
    # Подключаем роутеры для маршрутов и админских команд
    main_router.include_router(route_handlers.router)
    main_router.include_router(admin_commands.router)
    
    return main_router 