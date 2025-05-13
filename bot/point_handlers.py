from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from django.core.files.base import ContentFile
import io

from core.models import Point, User, Route, RoutePoint
from bot.states import PointStates

router = Router()

# Клавиатура для выбора типа контента
content_type_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Текст", callback_data="content_text"),
            InlineKeyboardButton(text="🎵 Аудио", callback_data="content_audio"),
            InlineKeyboardButton(text="📸 Фото + текст", callback_data="content_photo")
        ],
        [
            InlineKeyboardButton(text="✅ Готово", callback_data="content_done")
        ]
    ]
)

# Клавиатура для управления точкой
point_management_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_point"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data="delete_point")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_points")
        ]
    ]
)

# Клавиатура для управления маршрутом
route_management_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить точку", callback_data="add_point_to_route"),
            InlineKeyboardButton(text="➖ Удалить точку", callback_data="remove_point_from_route")
        ],
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_route"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data="delete_route")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_routes")
        ]
    ]
)

@router.message(Command("create_point"))
async def cmd_create_point(message: Message, state: FSMContext):
    """Начало создания новой точки"""
    try:
        user = await User.objects.aget(telegram_id=message.from_user.id)
        if not user.is_admin:
            return  # Просто игнорируем команду от неадмина
    except User.DoesNotExist:
        return  # Игнорируем команду от незарегистрированного пользователя

    await state.set_state(PointStates.waiting_for_name)
    await message.answer("Введите название точки:")

@router.message(PointStates.waiting_for_name)
async def handle_point_name(message: Message, state: FSMContext):
    """Обработка названия точки"""
    try:
        user = await User.objects.aget(telegram_id=message.from_user.id)
        if not user.is_admin:
            await state.clear()
            return
    except User.DoesNotExist:
        await state.clear()
        return

    await state.update_data(name=message.text)
    await state.set_state(PointStates.waiting_for_description)
    await message.answer("Введите описание точки:")

@router.message(PointStates.waiting_for_description)
async def handle_point_description(message: Message, state: FSMContext):
    """Обработка описания точки"""
    try:
        user = await User.objects.aget(telegram_id=message.from_user.id)
        if not user.is_admin:
            await state.clear()
            return
    except User.DoesNotExist:
        await state.clear()
        return

    await state.update_data(description=message.text)
    await state.set_state(PointStates.waiting_for_location)
    await message.answer("Отправьте локацию точки:")

@router.message(PointStates.waiting_for_location, F.location)
async def handle_point_location(message: Message, state: FSMContext):
    """Обработка локации точки"""
    try:
        user = await User.objects.aget(telegram_id=message.from_user.id)
        if not user.is_admin:
            await state.clear()
            return
    except User.DoesNotExist:
        await state.clear()
        return

    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude
    )
    
    # Создаем точку сразу после получения локации
    data = await state.get_data()
    point = await Point.objects.acreate(
        name=data['name'],
        description=data['description'],
        latitude=data['latitude'],
        longitude=data['longitude'],
        created_by=user
    )
    
    # Сохраняем ID точки для последующих обновлений
    await state.update_data(point_id=point.id)
    await state.set_state(PointStates.waiting_for_content_type)
    
    await message.answer(
        "Точка создана! Теперь добавьте контент. Выберите тип контента или нажмите 'Готово':",
        reply_markup=content_type_keyboard
    )

@router.callback_query(PointStates.waiting_for_content_type)
async def handle_content_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа контента"""
    try:
        user = await User.objects.aget(telegram_id=callback.from_user.id)
        if not user.is_admin:
            await state.clear()
            return
    except User.DoesNotExist:
        await state.clear()
        return

    if callback.data == "content_done":
        await state.clear()
        await callback.message.answer("✅ Точка успешно создана!")
        return

    content_type = callback.data.split('_')[1]
    await state.update_data(content_type=content_type)
    
    if content_type == "text":
        await state.set_state(PointStates.waiting_for_text)
        await callback.message.answer("Введите текст для точки:")
    elif content_type == "audio":
        await state.set_state(PointStates.waiting_for_audio)
        await callback.message.answer("Отправьте аудиофайл:")
    else:  # photo
        await state.set_state(PointStates.waiting_for_photo)
        await callback.message.answer("Отправьте фото:")

@router.message(PointStates.waiting_for_text)
async def handle_point_text(message: Message, state: FSMContext):
    """Обработка текстового контента"""
    try:
        user = await User.objects.aget(telegram_id=message.from_user.id)
        if not user.is_admin:
            await state.clear()
            return
    except User.DoesNotExist:
        await state.clear()
        return

    data = await state.get_data()
    point = await Point.objects.aget(id=data['point_id'])
    point.text_content = message.text
    await point.asave()
    
    await state.set_state(PointStates.waiting_for_content_type)
    await message.answer(
        "Текст добавлен! Выберите следующий тип контента или нажмите 'Готово':",
        reply_markup=content_type_keyboard
    )

@router.message(PointStates.waiting_for_audio)
async def handle_point_audio(message: Message, state: FSMContext, bot):
    """Обработка аудио контента"""
    try:
        user = await User.objects.aget(telegram_id=message.from_user.id)
        if not user.is_admin:
            await state.clear()
            return
    except User.DoesNotExist:
        await state.clear()
        return

    if not message.audio:
        await message.answer("Пожалуйста, отправьте аудиофайл.")
        return

    data = await state.get_data()
    point = await Point.objects.aget(id=data['point_id'])
    
    # Сохраняем аудиофайл
    audio_file = await bot.get_file(message.audio.file_id)
    audio_bytes_io = await bot.download_file(audio_file.file_path)
    audio_bytes = audio_bytes_io.getvalue()
    
    point.audio_file = ContentFile(audio_bytes, name=f"{message.audio.file_id}.mp3")
    await point.asave()
    
    await state.set_state(PointStates.waiting_for_content_type)
    await message.answer(
        "Аудио добавлено! Выберите следующий тип контента или нажмите 'Готово':",
        reply_markup=content_type_keyboard
    )

@router.message(PointStates.waiting_for_photo)
async def handle_point_photo(message: Message, state: FSMContext, bot):
    """Обработка фото контента"""
    try:
        user = await User.objects.aget(telegram_id=message.from_user.id)
        if not user.is_admin:
            await state.clear()
            return
    except User.DoesNotExist:
        await state.clear()
        return

    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото.")
        return

    data = await state.get_data()
    point = await Point.objects.aget(id=data['point_id'])
    
    # Сохраняем фото
    photo = message.photo[-1]  # Берем самое большое фото
    photo_file = await bot.get_file(photo.file_id)
    photo_bytes_io = await bot.download_file(photo_file.file_path)
    photo_bytes = photo_bytes_io.getvalue()
    point.photo = ContentFile(photo_bytes, name=f"{photo.file_id}.jpg")
    await point.asave()
    
    await state.set_state(PointStates.waiting_for_photo_text)
    await state.update_data(point_id=point.id)
    await message.answer("Теперь введите текст для фото:")

@router.message(PointStates.waiting_for_photo_text)
async def handle_point_photo_text(message: Message, state: FSMContext):
    """Обработка текста для фото"""
    try:
        user = await User.objects.aget(telegram_id=message.from_user.id)
        if not user.is_admin:
            await state.clear()
            return
    except User.DoesNotExist:
        await state.clear()
        return

    data = await state.get_data()
    point = await Point.objects.aget(id=data['point_id'])
    point.text_content = message.text
    await point.asave()
    
    await state.set_state(PointStates.waiting_for_content_type)
    await message.answer(
        "Фото и текст добавлены! Выберите следующий тип контента или нажмите 'Готово':",
        reply_markup=content_type_keyboard
    )

@router.message(Command("list_points"))
async def cmd_list_points(message: Message):
    """Показать список всех точек"""
    try:
        user = await User.objects.aget(telegram_id=message.from_user.id)
        if not user.is_admin:
            return  # Просто игнорируем команду от неадмина
    except User.DoesNotExist:
        return  # Игнорируем команду от незарегистрированного пользователя

    points = await Point.objects.all().order_by('-created_at')
    if not points:
        await message.answer("Список точек пуст.")
        return

    text = "📋 Список точек:\n\n"
    for point in points:
        text += f"• {point.name}\n"
        text += f"  ID: {point.id}\n"
        text += f"  Описание: {point.description}\n"
        text += f"  Создана: {point.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    await message.answer(text)

@router.message(Command("view_point"))
async def cmd_view_point(message: Message):
    """Просмотр конкретной точки"""
    try:
        user = await User.objects.aget(telegram_id=message.from_user.id)
        if not user.is_admin:
            return
    except User.DoesNotExist:
        return

    # Ожидаем формат: /view_point ID
    try:
        point_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("Используйте формат: /view_point ID")
        return

    try:
        point = await Point.objects.aget(id=point_id)
    except Point.DoesNotExist:
        await message.answer("Точка не найдена.")
        return

    text = f"📌 Точка: {point.name}\n"
    text += f"ID: {point.id}\n"
    text += f"Описание: {point.description}\n"
    text += f"Координаты: {point.latitude}, {point.longitude}\n"
    text += f"Создана: {point.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    if point.text_content:
        text += f"Текст: {point.text_content}\n"
    if point.photo:
        text += "📸 Есть фото\n"
    if point.audio_file:
        text += "🎵 Есть аудио\n"

    await message.answer(text, reply_markup=point_management_keyboard)

@router.callback_query(F.data == "edit_point")
async def handle_edit_point(callback: CallbackQuery, state: FSMContext):
    """Редактирование точки"""
    # TODO: Реализовать редактирование точки
    await callback.message.answer("Функция редактирования точки будет доступна в следующем обновлении.")

@router.callback_query(F.data == "delete_point")
async def handle_delete_point(callback: CallbackQuery):
    """Удаление точки"""
    # TODO: Реализовать удаление точки
    await callback.message.answer("Функция удаления точки будет доступна в следующем обновлении.")

@router.callback_query(F.data == "back_to_points")
async def handle_back_to_points(callback: CallbackQuery):
    """Возврат к списку точек"""
    await cmd_list_points(callback.message) 