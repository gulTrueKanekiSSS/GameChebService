"""
Главный файл для объединения всех обработчиков
"""
from aiogram import Router
from bot.point_handlers import PointHandler
from bot.route_handlers import RouteHandler

def get_main_router():
    """Создает и возвращает главный роутер со всеми обработчиками"""
    main_router = Router()
    
    # Создаем экземпляры обработчиков
    point_handler = PointHandler()
    route_handler = RouteHandler()
    
    # Включаем роутеры обработчиков в главный роутер
    main_router.include_router(point_handler.get_router())
    main_router.include_router(route_handler.get_router())
    
    return main_router 