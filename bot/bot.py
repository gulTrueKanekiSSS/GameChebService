import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from core.models import User
from dotenv import load_dotenv
from asgiref.sync import sync_to_async
from aiogram.types import WebAppInfo

# Импортируем административные команды
from . import admin_commands

# Явно загружаем переменные окружения
load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен напрямую из переменных окружения
token = os.getenv('TELEGRAM_BOT_TOKEN')
print(f"Используемый токен из переменных окружения: {token}")

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
            [KeyboardButton(text="🎯 Получить квест")],
            [KeyboardButton(text="🎁 Мои промокоды")],
        ],
        resize_keyboard=True
    )
    return keyboard


WEBAPP_URL = "https://52e8e396cdbd2607c69dd56f4482cd58.serveo.net/"

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # keyboard = InlineKeyboardMarkup(inline_keyboard=[
    #     [InlineKeyboardButton(text="Открыть Web App", web_app=WebAppInfo(url=WEBAPP_URL))]
    # ])
    # await message.answer("Нажми кнопку ниже, чтобы открыть Web App 👇", reply_markup=keyboard)
    get_or_create = sync_to_async(User.objects.get_or_create)
    user, created = await get_or_create(
        telegram_id=message.from_user.id,
        defaults={
            'name': message.from_user.full_name,
        }
    )


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

    await message.answer(
        "Спасибо! Теперь вы можете начать выполнять квесты.",
        reply_markup=keyboard
    )

async def start_bot():
    # Регистрируем хендлеры
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(handle_contact, lambda message: message.contact is not None)
    
    try:
        # Запускаем бота
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise 