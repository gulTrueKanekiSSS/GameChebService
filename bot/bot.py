import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from core.models import User
from dotenv import load_dotenv
from asgiref.sync import sync_to_async
from aiogram.types import WebAppInfo
from django.conf import settings

# Импортируем административные команды
from . import admin_commands
from . import route_handlers

# Явно загружаем переменные окружения
load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен напрямую из переменных окружения
token = os.getenv('TELEGRAM_BOT_TOKEN')

# Инициализируем бота и диспетчер с новым синтаксисом
bot = Bot(
    token=token,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# Регистрируем административные команды
dp.message.register(admin_commands.handle_approve, Command("approve"))
dp.message.register(admin_commands.handle_reject, Command("reject"))


def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎯 Получить квест"),
                KeyboardButton(text="🎁 Мои промокоды")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🗺 Маршруты"),
                KeyboardButton(text="📍 Точки")
            ],
            [
                KeyboardButton(text="🎯 Получить квест"),
                KeyboardButton(text="🎁 Мои промокоды")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard


WEBAPP_URL = "https://280e96efed85bc66d099b6f91fe347d6.serveo.net"


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_or_create = sync_to_async(User.objects.get_or_create)
    user, created = await get_or_create(
        telegram_id=message.from_user.id,
        defaults={
            'name': message.from_user.full_name,
            'is_admin': message.from_user.id in settings.ADMIN_IDS  # Автоматически назначаем администратором
        }
    )

    # Если пользователь уже существовал, проверяем его права администратора
    if not created and not user.is_admin:
        user.is_admin = message.from_user.id in settings.ADMIN_IDS
        await sync_to_async(user.save)()

    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer(
        "Добро пожаловать! Для начала работы, пожалуйста, поделитесь своим номером телефона.",
        reply_markup=contact_keyboard
    )

@dp.message(lambda message: message.contact is not None)
async def handle_contact(message: types.Message):
    get_user = sync_to_async(User.objects.get)
    user = await get_user(telegram_id=message.from_user.id)
    user.phone_number = message.contact.phone_number
    user.is_verified = True
    save_user = sync_to_async(user.save)
    await save_user()

    params = f"?id={user.telegram_id}&name={user.name}&phone={user.phone_number}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть Web App", web_app=WebAppInfo(url=WEBAPP_URL+params))]
    ])

    # Используем админскую клавиатуру, если пользователь админ
    reply_markup = get_admin_keyboard() if user.is_admin else get_main_keyboard()

    await message.answer(
        "Спасибо! Теперь вы можете начать выполнять квесты.",
        reply_markup=reply_markup
    )

async def start_bot():
    # Регистрируем хендлеры
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(handle_contact, lambda message: message.contact is not None)
    
    # Регистрируем обработчики для управления маршрутами и точками
    dp.message.register(route_handlers.handle_routes_menu, F.text == "🗺 Маршруты")
    dp.message.register(route_handlers.handle_points_menu, F.text == "📍 Точки")
    
    # Регистрируем все роутеры
    register_handlers(dp)
    
    try:
        # Запускаем бота
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise

from bot.admin_commands import router as admin_router
from bot.route_handlers import router as route_router

def register_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    dp.include_router(admin_router)
    dp.include_router(route_router) 