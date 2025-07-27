import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from core.models import User, Route, RoutePoint, Point, PointPhoto, PointAudio, PointVideo
from django.conf import settings
import logging

from bot.states import RouteStates

class BaseHandler:
    """Базовый класс для всех обработчиков"""
    
    def __init__(self):
        self.router = Router()
        self.logger = logging.getLogger(__name__)
    
    async def check_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        try:
            user = await User.objects.aget(telegram_id=user_id)
            return user.is_admin
        except User.DoesNotExist:
            return False
    
    def get_admin_keyboard(self):
        """Клавиатура для админа"""
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="🗺 Маршруты"),
                    KeyboardButton(text="📍 Точки")
                ],
                [
                    KeyboardButton(text="🎯 Получить маршрут"),
                    KeyboardButton(text="🎁 Мои промокоды")
                ]
            ],
            resize_keyboard=True
        )
        return keyboard
    
    def get_points_management_keyboard(self):
        """Клавиатура для управления точками"""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📋 Список точек", callback_data="list_points"),
                    InlineKeyboardButton(text="➕ Создать точку", callback_data="create_point")
                ],
                [
                    InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
                ]
            ]
        )
        return keyboard
    
    def get_routes_management_keyboard(self):
        """Клавиатура для управления маршрутами"""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📋 Список маршрутов", callback_data="list_routes"),
                    InlineKeyboardButton(text="➕ Создать маршрут", callback_data="create_route")
                ],
                [
                    InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
                ]
            ]
        )
        return keyboard
    
    async def find_point_by_short_id(self, short_point_id: str):
        """Поиск точки по короткому ID"""
        try:
            all_points = await sync_to_async(list)(
                Point.objects.filter(id__icontains=short_point_id)
            )
            if not all_points:
                raise Point.DoesNotExist
            elif len(all_points) > 1:
                return None, "Найдено несколько точек с таким ID. Уточните ID."
            
            return all_points[0], None
        except Point.DoesNotExist:
            return None, "Точка не найдена."
    
    async def find_route_by_short_id(self, short_route_id: str):
        """Поиск маршрута по короткому ID"""
        try:
            route = await Route.objects.aget(id__startswith=short_route_id)
            return route, None
        except Route.DoesNotExist:
            return None, "Маршрут не найден."
    
    def get_router(self):
        """Возвращает роутер для регистрации"""
        return self.router 