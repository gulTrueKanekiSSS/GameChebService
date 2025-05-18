import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from core.models import User, RoutePoint, Route, Point
from dotenv import load_dotenv
from asgiref.sync import sync_to_async
from aiogram.types import WebAppInfo
from django.conf import settings
from aiogram.types.input_file import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

class RouteState(StatesGroup):
    waiting_for_next_point = State()

# Явно загружаем переменные окружения
load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен напрямую из переменных окружения
token = os.getenv('TELEGRAM_BOT_TOKEN')

# Инициализируем бота и диспетчер с новым синтаксисом
dp = Dispatcher()
bot = None

# Регистрируем административные команды
from . import admin_commands
from . import route_handlers
dp.message.register(admin_commands.handle_approve, Command("approve"))
dp.message.register(admin_commands.handle_reject, Command("reject"))

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎯 Получить маршрут"),
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
                KeyboardButton(text="🎯 Получить маршрут"),
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
            'is_admin': message.from_user.id in settings.ADMIN_IDS
        }
    )

    # Если пользователь уже верифицирован, не запрашиваем номер телефона повторно
    if user.is_verified:
        reply_markup = get_admin_keyboard() if user.is_admin else get_main_keyboard()
        await message.answer("Добро пожаловать обратно! Чем могу помочь?", reply_markup=reply_markup)
        # Отправляем инструкцию
        await message.answer(
            "Надевай наушники и наслаждайся прогулкой в современном формате от GameCheb 😌\n\n"
            "Инструкция по маршруту:\n\n"
            "1. Заходи в бота.\n"
            "2. Жми \"получить маршрут\".\n"
            "3. Выбирай \"Квест по Чебоксарам\".\n"
            "4. Следуй по точкам маршрута.\n"
            "5. Когда дойдешь до указанной локации — слушай аудио.\n"
            "6. Насладился объектом или локацией? Жми кнопку \"Я прошёл точку\" и двигайся дальше!\n\n"
            "Всего маршрут включает 11 локаций, а вся прогулка займет не больше 1 часа.\n\n"
            "🎁 После прохождения маршрута тебя ждет крутая возможность и секретный приз — мы ждем тебя в конце пути!\n\n"
            "В случае любых сложностей или ошибок, пишите @dstepanv. Мы все починим и сделаем ваш опыт использования лучше)"
        )
        return

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

    # Отправляем инструкцию
    await message.answer(
        "Надевай наушники и наслаждайся прогулкой в современном формате от GameCheb 😌\n\n"
        "Инструкция по маршруту:\n\n"
        "1. Заходи в бота.\n"
        "2. Жми \"получить маршрут\".\n"
        "3. Выбирай \"Квест по Чебоксарам\".\n"
        "4. Следуй по точкам маршрута.\n"
        "5. Когда дойдешь до указанной локации — слушай аудио.\n"
        "6. Насладился объектом или локацией? Жми кнопку \"Я прошёл точку\" и двигайся дальше!\n\n"
        "Всего маршрут включает 11 локаций, а вся прогулка займет не больше 1 часа.\n\n"
        "🎁 После прохождения маршрута тебя ждет крутая возможность и секретный приз — мы ждем тебя в конце пути!\n\n"
        "В случае любых сложностей или ошибок, пишите @dstepanv. Мы все починим и сделаем ваш опыт использования лучше)"
    )

@dp.message(F.text == "🎯 Получить маршрут")
async def handle_get_routes(message: types.Message):
    get_routes = sync_to_async(lambda: list(Route.objects.filter(is_active=True)))
    routes = await get_routes()

    if not routes:
        await message.answer("Нет доступных маршрутов на данный момент.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for route in routes:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=route.name, callback_data=f"route_{route.id}")])

    await message.answer("Выберите маршрут:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("route_"))
async def handle_route_selection(callback_query: types.CallbackQuery, state: FSMContext):
    route_id = callback_query.data.split("_")[1]
    get_route_points = sync_to_async(lambda: list(RoutePoint.objects.filter(route_id=route_id)))
    route_points = await get_route_points()

    if not route_points:
        await callback_query.message.answer("Нет доступных точек для этого маршрута.")
        return

    # Сохраняем данные маршрута и текущий индекс
    await state.update_data(current_index=1, route_points=route_points)

    # Сразу отправляем первую точку
    first_point = route_points[0]
    get_point = sync_to_async(lambda: Point.objects.get(id=first_point.point_id))
    point = await get_point()

    # Отправляем локацию точки
    await callback_query.message.answer_location(latitude=point.latitude, longitude=point.longitude)

    if point.photo:
        try:
            await callback_query.message.answer_photo(
                photo=FSInputFile(point.photo.path),
                caption=f"📍 {point.name}"
            )
            # Отправляем описание и текст отдельным сообщением
            description_text = f"{point.description}\n\n{point.text_content if point.text_content else ''}"
            if description_text.strip():
                await callback_query.message.answer(description_text)
        except Exception as e:
            logging.error(f"Ошибка при отправке фото: {e}")

    if point.audio_file:
        try:
            await callback_query.message.answer_audio(
                audio=FSInputFile(point.audio_file.path),
                caption=f"🎵 {point.name}"
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке аудио: {e}")

    if point.video_file and point.video_file.name:
        try:
            await callback_query.message.answer_video(
                video=FSInputFile(point.video_file.path),
                caption=f"🎥 {point.name}",
                width=None,
                height=None
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке видео: {e}")

    await callback_query.message.answer(
        "Начинаем маршрут. Нажмите 'Я прошел точку' для продолжения.",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Я прошел точку")]], resize_keyboard=True)
    )
    await state.set_state(RouteState.waiting_for_next_point)

async def send_completion_messages(message: types.Message):
    """Отправка сообщений о завершении маршрута"""
    try:
        await message.answer("Маршрут завершен.", reply_markup=get_main_keyboard())
        await message.answer(
            "Ты это сделал!\n"
            "Ты прошёл весь маршрут от GameCheb — и это не просто прогулка, это путь. Ты — из тех, кто не стоит на месте. И теперь у тебя есть шанс сделать следующий шаг.\n\n"
            "Мы приглашаем тебя туда, где создаётся будущее.\n"
            "Это — эксклюзивная экскурсия по самому современному образовательному кампусу в Чувашии. Здесь учатся, создают, запускают свои проекты и меняют мир. И ты можешь стать частью этого.\n\n"
            "Чтобы попасть на экскурсию, просто оставь заявку в форме по ссылке ниже. Мест не так много, так что не откладывай.\n"
            "Пройди ещё один шаг — к своим возможностям.\n\n"
            "Регистрация на экскурсию:\n"
            "https://forms.gle/Tkb3YpWUx3w1Dg427"
        )
        
        # Ждем 10 секунд перед отправкой формы обратной связи
        await asyncio.sleep(120)
        
        await message.answer(
            "Оставь пожалуйста обратную связь о прохождении маршрута. Нам очень важно твое мнение, чтобы становится лучше каждый день)\n\n"
            "Форма обратной связи:\n"
            "https://forms.gle/RzJkY2u1ESKNZBW26"
        )
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщений о завершении маршрута: {e}")

@dp.message(F.text == "Я прошел точку")
async def handle_next_point(message: types.Message, state: FSMContext):
    # Проверка состояния FSM
    current_state = await state.get_state()
    if current_state != RouteState.waiting_for_next_point.state:
        await message.answer("Вы не в маршруте. Нажмите 'Я прошел точку' для продолжения.")
        return
    data = await state.get_data()
    route_points = data.get('route_points', [])
    current_index = data.get('current_index', 0)

    route_point = route_points[current_index]
    get_point = sync_to_async(lambda: Point.objects.get(id=route_point.point_id))
    point = await get_point()

    # Отправляем локацию точки
    await message.answer_location(latitude=point.latitude, longitude=point.longitude)

    # Отправляем фото, если оно есть
    if point.photo:
        try:
            await message.answer_photo(
                photo=FSInputFile(point.photo.path),
                caption=f"📍 {point.name}"
            )
            # Отправляем описание и текст отдельным сообщением
            description_text = f"{point.description}\n\n{point.text_content if point.text_content else ''}"
            if description_text.strip():
                await message.answer(description_text)
        except Exception as e:
            logging.error(f"Ошибка при отправке фото: {e}")
            await message.answer("Не удалось загрузить фото точки.")

    # Отправляем видео, если оно есть
    if point.video_file and point.video_file.name:
        try:
            await message.answer_video(
                video=FSInputFile(point.video_file.path),
                caption=f"🎥 {point.name}",
                width=None,
                height=None
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке видео: {e}")
            await message.answer("Не удалось загрузить видео точки.")

    # Отправляем аудио, если оно есть
    if point.audio_file:
        try:
            await message.answer_audio(
                audio=FSInputFile(point.audio_file.path),
                caption=f"🎵 {point.name}"
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке аудио: {e}")
            await message.answer("Не удалось загрузить аудио точки.")

    # Увеличиваем индекс для следующей точки
    current_index += 1
    await state.update_data(current_index=current_index)

    if current_index >= len(route_points):
        # Запускаем отправку сообщений в отдельной задаче
        asyncio.create_task(send_completion_messages(message))
        await state.clear()
        return

    # Отправляем сообщение о следующей точке
    await message.answer(
        "Нажмите 'Я прошел точку' для продолжения.",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Я прошел точку")]], resize_keyboard=True)
    )

async def start_bot():
    """Функция запуска бота."""
    global bot

    # Явно загружаем переменные окружения
    load_dotenv(override=True)
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    # Проверка наличия токена
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в .env")
        return

    # Инициализация бота и диспетчера
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))

    # Регистрируем хендлеры
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(handle_contact, lambda message: message.contact is not None)
    dp.message.register(route_handlers.handle_routes_menu, F.text == "🗺 Маршруты")
    dp.message.register(route_handlers.handle_points_menu, F.text == "📍 Точки")

    register_handlers(dp)
    
    max_retries = 3
    retry_delay = 5  # секунды
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Запуск бота (попытка {attempt + 1}/{max_retries})")
            await dp.start_polling(bot, skip_updates=True)
        except Exception as e:
            logger.error(f"Ошибка при запуске бота (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Повторная попытка через {retry_delay} секунд...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Достигнуто максимальное количество попыток. Бот остановлен.")
                raise

from bot.admin_commands import router as admin_router
from bot.route_handlers import router as route_router

def register_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    dp.include_router(admin_router)
    dp.include_router(route_router) 