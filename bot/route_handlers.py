import uuid
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Video, URLInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from core.models import User, Route, RoutePoint, Point, PointPhoto, PointAudio, PointVideo
from django.conf import settings
from django.core.paginator import Paginator
import logging

from bot.states import RouteStates

router = Router()

# Константы для пагинации
POINTS_PER_PAGE = 10

async def get_points_by_routes():
    """Группирует точки по маршрутам"""
    routes = await sync_to_async(list)(Route.objects.filter(is_active=True).order_by('name'))
    grouped_points = {}
    
    for route in routes:
        route_points = await sync_to_async(list)(
            RoutePoint.objects.filter(route=route).order_by('order').select_related('point')
        )
        if route_points:
            grouped_points[route] = route_points
    
    # Получаем неиспользуемые точки
    used_point_ids = await sync_to_async(list)(
        RoutePoint.objects.values_list('point_id', flat=True)
    )
    unused_points = await sync_to_async(list)(
        Point.objects.exclude(id__in=used_point_ids).order_by('-created_at')
    )
    
    return grouped_points, unused_points

async def get_filtered_points(filter_type="all", search_query=None, page=1):
    """Получает отфильтрованные точки с пагинацией"""
    if filter_type == "unused":
        # Только неиспользуемые точки
        used_point_ids = await sync_to_async(list)(
            RoutePoint.objects.values_list('point_id', flat=True)
        )
        points = await sync_to_async(list)(
            Point.objects.exclude(id__in=used_point_ids).order_by('-created_at')
        )
    elif filter_type == "search" and search_query:
        # Поиск по названию (нечувствительный к регистру)
        print(f"DEBUG: Поиск по запросу '{search_query}' (регистр не учитывается)")
        points = await sync_to_async(list)(
            Point.objects.filter(name__icontains=search_query).order_by('-created_at')
        )
        print(f"DEBUG: Найдено {len(points)} точек")
        for point in points:
            print(f"DEBUG: Точка: '{point.name}' (запрос: '{search_query}')")
    else:
        # Все точки
        points = await sync_to_async(list)(Point.objects.all().order_by('-created_at'))
    
    # Пагинация
    paginator = Paginator(points, POINTS_PER_PAGE)
    page_obj = paginator.get_page(page)
    
    return page_obj, paginator.num_pages

def get_points_filter_keyboard():
    """Клавиатура для фильтрации точек"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗺 Все точки", callback_data="filter_points:all"),
                InlineKeyboardButton(text="📍 Неиспользуемые", callback_data="filter_points:unused")
            ],
            [
                InlineKeyboardButton(text="🔍 Поиск", callback_data="search_points"),
                InlineKeyboardButton(text="📅 По дате", callback_data="filter_points:by_date")
            ],
            [
                InlineKeyboardButton(text="🗺 По маршрутам", callback_data="group_points_by_routes")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_points_menu")
            ]
        ]
    )
    return keyboard

def get_points_pagination_keyboard(current_page, total_pages, filter_type="all", search_query=None):
    """Клавиатура для пагинации точек"""
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"page_points:{filter_type}:{current_page-1}:{search_query or ''}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="current_page")
    )
    
    if current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"page_points:{filter_type}:{current_page+1}:{search_query or ''}")
        )
    
    keyboard.append(nav_buttons)
    
    # Кнопка возврата к фильтрам
    keyboard.append([
        InlineKeyboardButton(text="🔙 К фильтрам", callback_data="list_points")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def check_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    try:
        user = await User.objects.aget(telegram_id=user_id)
        return user.is_admin
    except User.DoesNotExist:
        return False


def get_admin_keyboard():
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


def get_points_management_keyboard():
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


def get_routes_management_keyboard():
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


@router.message(F.text == "📍 Точки")
async def handle_points_menu(message: Message):
    """Обработка нажатия на кнопку 'Точки'"""
    if not await check_admin(message.from_user.id):
        return

    await message.answer(
        "Управление точками:",
        reply_markup=get_points_management_keyboard()
    )


@router.message(F.text == "🗺 Маршруты")
async def handle_routes_menu(message: Message):
    """Обработка нажатия на кнопку 'Маршруты'"""
    if not await check_admin(message.from_user.id):
        return

    await message.answer(
        "Управление маршрутами:",
        reply_markup=get_routes_management_keyboard()
    )


@router.callback_query(F.data == "list_points")
async def handle_list_points_callback(callback: CallbackQuery):
    """Показать меню фильтрации точек"""
    if not await check_admin(callback.from_user.id):
        return

    await callback.message.answer(
        "🔍 Выберите способ просмотра точек:",
        reply_markup=get_points_filter_keyboard()
    )


@router.callback_query(F.data == "list_routes")
async def handle_list_routes_callback(callback: CallbackQuery):
    """Показать список маршрутов"""
    if not await check_admin(callback.from_user.id):
        return

    routes = await sync_to_async(list)(Route.objects.all().order_by('-created_at'))
    if not routes:
        await callback.message.answer("Список маршрутов пуст.")
        return

    text = "🗺 Список маршрутов:\n\n"
    for route in routes:
        points_count = await sync_to_async(RoutePoint.objects.filter(route=route).count)()
        text += f"• {route.name}\n"
        text += f"  ID: {route.id}\n"
        text += f"  Описание: {route.description}\n"
        text += f"  Количество точек: {points_count}\n"
        text += f"  Создан: {route.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    keyboard = []
    for route in routes:
        keyboard.append([
            InlineKeyboardButton(
                text=f"✏️ {route.name}",
                callback_data=f"view_route:{route.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_routes_menu")])

    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(F.data == "back_to_points_menu")
async def handle_back_to_points_menu(callback: CallbackQuery):
    """Возврат в меню точек"""
    await callback.message.answer(
        "Управление точками:",
        reply_markup=get_points_management_keyboard()
    )


@router.callback_query(F.data == "back_to_routes_menu")
async def handle_back_to_routes_menu(callback: CallbackQuery):
    """Возврат в меню маршрутов"""
    await callback.message.answer(
        "Управление маршрутами:",
        reply_markup=get_routes_management_keyboard()
    )


@router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_admin_keyboard()
    )


@router.callback_query(F.data == "create_point")
async def handle_create_point(callback: CallbackQuery, state: FSMContext):
    """Начало создания новой точки"""
    if not await check_admin(callback.from_user.id):
        return

    await state.set_state(RouteStates.waiting_for_point_name)
    await callback.message.answer("Введите название точки:")


@router.callback_query(F.data == "create_route")
async def handle_create_route(callback: CallbackQuery, state: FSMContext):
    """Начало создания нового маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    await state.set_state(RouteStates.waiting_for_route_name)
    await callback.message.answer("Введите название маршрута:")


@router.message(RouteStates.waiting_for_point_name)
async def handle_point_name(message: Message, state: FSMContext):
    """Обработка названия точки"""
    await state.update_data(name=message.text)
    await state.set_state(RouteStates.waiting_for_point_description)
    await message.answer("Введите описание точки:")


@router.message(RouteStates.waiting_for_point_description)
async def handle_point_description(message: Message, state: FSMContext):
    """Обработка описания точки"""
    await state.update_data(description=message.text)
    await state.set_state(RouteStates.waiting_for_point_location)
    await message.answer(
        "Отправьте локацию точки.\n"
        "Нажмите на кнопку 📎 и выберите 'Локация'"
    )


@router.message(RouteStates.waiting_for_point_location, F.location)
async def handle_point_location(message: Message, state: FSMContext):
    """Обработка локации точки"""
    data = await state.get_data()
    name = data['name']
    description = data['description']
    latitude = message.location.latitude
    longitude = message.location.longitude

    user = await sync_to_async(User.objects.get)(telegram_id=message.from_user.id)

    point = await sync_to_async(Point.objects.create)(
        name=name,
        description=description,
        latitude=latitude,
        longitude=longitude,
        created_by=user
    )

    await state.clear()
    await message.answer(
        f"✅ Точка '{point.name}' создана!\n\n"
        "Теперь вы можете добавить дополнительную информацию:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📝 Добавить текст", callback_data=f"edit_pt_text:{str(point.id)}"),
                    InlineKeyboardButton(text="📸 Добавить фото", callback_data=f"add_pt_photo:{str(point.id)}")
                ],
                [
                    InlineKeyboardButton(text="🎵 Добавить аудио", callback_data=f"add_pt_audio:{str(point.id)}"),
                    InlineKeyboardButton(text="🎥 Добавить видео", callback_data=f"add_pt_video:{str(point.id)}")
                ],
                [
                    InlineKeyboardButton(text="✅ Готово", callback_data="list_points")
                ]
            ]
        )
    )


@router.message(RouteStates.waiting_for_route_name)
async def handle_route_name(message: Message, state: FSMContext):
    """Обработка названия маршрута"""
    data = await state.get_data()
    if 'route_id' in data:
        try:
            route = await Route.objects.aget(id=data['route_id'])
            route.name = message.text
            await route.asave()
            await message.answer("Название маршрута успешно обновлено.")
            await state.clear()
            callback = CallbackQuery(
                id=str(message.message_id),
                from_user=message.from_user,
                chat_instance=str(message.chat.id),
                message=message,
                data=f"view_route:{route.id}"
            )
            await handle_view_route(callback)
        except Route.DoesNotExist:
            await message.answer("Маршрут не найден.")
            await state.clear()
    else:
        await state.update_data(route_name=message.text)
        await state.set_state(RouteStates.waiting_for_route_description)
        await message.answer("Введите описание маршрута:")


@router.message(RouteStates.waiting_for_route_description)
async def handle_route_description(message: Message, state: FSMContext):
    """Обработка описания маршрута"""
    data = await state.get_data()
    if 'route_id' in data:
        try:
            route = await Route.objects.aget(id=data['route_id'])
            route.description = message.text
            await route.asave()
            await message.answer("Описание маршрута успешно обновлено.")
            await state.clear()
            callback = CallbackQuery(
                id=str(message.message_id),
                from_user=message.from_user,
                chat_instance=str(message.chat.id),
                message=message,
                data=f"view_route:{route.id}"
            )
            await handle_view_route(callback)
        except Route.DoesNotExist:
            await message.answer("Маршрут не найден.")
            await state.clear()
    else:
        name = data.get('route_name')
        if not name:
            await message.answer("Ошибка: название маршрута не найдено. Начните создание маршрута заново.")
            await state.clear()
            return

        description = message.text

        user = await sync_to_async(User.objects.get)(telegram_id=message.from_user.id)

        route = await sync_to_async(Route.objects.create)(
            name=name,
            description=description,
            created_by=user
        )

        await state.clear()
        await message.answer(
            f"✅ Маршрут '{route.name}' создан!\n\n"
            "Теперь вы можете добавить точки в маршрут:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="📸 Добавить фото", callback_data=f"add_route_photo:{str(route.id)}"),
                        InlineKeyboardButton(text="➕ Добавить точку", callback_data=f"add_pt:{str(route.id)[:8]}")
                    ],
                    [
                        InlineKeyboardButton(text="✅ Готово", callback_data="list_routes")
                    ]
                ]
            )
        )


@router.callback_query(F.data.startswith("add_pt:"))
async def handle_add_point_to_route(callback: CallbackQuery, state: FSMContext):
    """Добавление точки в маршрут"""
    if not await check_admin(callback.from_user.id):
        return

    route_id = callback.data.split(":")[1]

    try:
        route = await Route.objects.aget(id=uuid.UUID(route_id))
    except (Route.DoesNotExist, ValueError):
        await callback.message.answer("Маршрут не найден.")
        return

    existing_points = await sync_to_async(list)(
        RoutePoint.objects.filter(route=route).values_list('point_id', flat=True))
    available_points = await sync_to_async(list)(Point.objects.exclude(id__in=existing_points))

    if not available_points:
        await callback.message.answer("Нет доступных точек для добавления в маршрут.")
        return

    # Группируем доступные точки по категориям
    text = f"➕ Добавление точки в маршрут '{route.name}'\n\n"
    text += f"📋 Доступно точек: {len(available_points)}\n\n"
    
    # Показываем первые 15 точек с группировкой
    for i, point in enumerate(available_points[:15], 1):
        text += f"{i}. {point.name}\n"
        text += f"   📍 {point.description[:50]}{'...' if len(point.description) > 50 else ''}\n"
        text += f"   📅 {point.created_at.strftime('%d.%m.%Y')}\n\n"
    
    if len(available_points) > 15:
        text += f"... и еще {len(available_points) - 15} точек\n"
        text += "Используйте поиск для быстрого нахождения нужной точки."

    # Создаем клавиатуру с пагинацией
    keyboard = []
    
    # Показываем первые 10 точек
    for point in available_points[:10]:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📍 {point.name}",
                callback_data=f"sel_pt:{str(route.id)}:{str(point.id)}"
            )
        ])
    
    # Добавляем навигацию если точек много
    if len(available_points) > 10:
        keyboard.append([
            InlineKeyboardButton(text="◀️", callback_data="current_page"),
            InlineKeyboardButton(text="1", callback_data="current_page"),
            InlineKeyboardButton(text="▶️", callback_data=f"add_pt_page:{str(route.id)}:2")
        ])
    
    # Дополнительные опции
    keyboard.append([
        InlineKeyboardButton(text="🔍 Поиск точки", callback_data=f"search_for_route:{str(route.id)}"),
        InlineKeyboardButton(text="📍 Только неиспользуемые", callback_data=f"filter_unused_for_route:{str(route.id)}")
    ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Отмена", callback_data=f"view_route:{str(route.id)}")])

    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("sel_pt:"))
async def handle_select_point_for_route(callback: CallbackQuery):
    """Обработка выбора точки для добавления в маршрут"""
    if not await check_admin(callback.from_user.id):
        return

    _, route_id, point_id = callback.data.split(":")

    try:
        route = await Route.objects.aget(id=uuid.UUID(route_id))
        point = await Point.objects.aget(id=uuid.UUID(point_id))
    except (Route.DoesNotExist, Point.DoesNotExist, ValueError):
        await callback.message.answer("Маршрут или точка не найдены.")
        return

    max_order = await sync_to_async(
        lambda: RoutePoint.objects.filter(route=route).order_by('-order').values_list('order', flat=True).first())()
    new_order = (max_order or 0) + 1

    await sync_to_async(RoutePoint.objects.create)(
        route=route,
        point=point,
        order=new_order
    )

    await callback.message.answer(f"Точка '{point.name}' добавлена в маршрут '{route.name}'.")
    await handle_view_route(callback)


@router.callback_query(F.data.startswith("view_route:"))
async def handle_view_route(callback: CallbackQuery):
    """Просмотр конкретного маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    route_id = callback.data.split(":")[1]
    try:
        route = await Route.objects.aget(id=uuid.UUID(route_id))
    except (Route.DoesNotExist, ValueError):
        await callback.message.answer("Маршрут не найден.")
        return

    if route.photo:
        await callback.message.answer_photo(
            photo=URLInputFile(route.photo.url),
            caption=f"🗺 {route.name}"
        )

    text = f"🗺 Маршрут: {route.name}\n"
    text += f"ID: {route.id}\n"
    text += f"Описание: {route.description}\n"
    text += f"Создан: {route.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    route_points = await sync_to_async(list)(
        RoutePoint.objects.filter(route=route).order_by('order').select_related('point'))
    if route_points:
        text += "📍 Точки маршрута:\n"
        for i, route_point in enumerate(route_points, 1):
            text += f"{i}. {route_point.point.name}\n"
    else:
        text += "В маршруте пока нет точек.\n"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_rt:{str(route.id)}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_rt:{str(route.id)}")
            ],
            [
                InlineKeyboardButton(text="➕ Добавить точку", callback_data=f"add_pt:{str(route.id)}"),
                InlineKeyboardButton(text="➖ Удалить точку", callback_data=f"remove_point_from_route:{str(route.id)}")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад к списку", callback_data="list_routes")
            ]
        ]
    )

    await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("remove_point_from_route:"))
async def handle_remove_point_from_route(callback: CallbackQuery):
    """Удаление точки из маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    route_id = callback.data.split(":")[1]
    try:
        route = await Route.objects.aget(id=uuid.UUID(route_id))
    except (Route.DoesNotExist, ValueError):
        await callback.message.answer("Маршрут не найден.")
        return

    route_points = await sync_to_async(list)(
        RoutePoint.objects.filter(route=route).select_related('point').order_by('order'))
    if not route_points:
        await callback.message.answer("В маршруте нет точек.")
        return

    keyboard = []
    for route_point in route_points:
        keyboard.append([
            InlineKeyboardButton(
                text=route_point.point.name,
                callback_data=f"rm_pt:{str(route.id)}:{str(route_point.point.id)}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Отмена", callback_data=f"view_route:{str(route.id)}")])

    await callback.message.answer(
        "Выберите точку для удаления из маршрута:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("rm_pt:"))
async def handle_remove_point_from_route_confirm(callback: CallbackQuery):
    """Подтверждение удаления точки из маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    _, route_id, point_id = callback.data.split(":")
    try:
        route = await Route.objects.aget(id=uuid.UUID(route_id))
        point = await Point.objects.aget(id=uuid.UUID(point_id))
        route_point = await sync_to_async(RoutePoint.objects.get)(route=route, point=point)
    except (Route.DoesNotExist, Point.DoesNotExist, RoutePoint.DoesNotExist):
        await callback.message.answer("Маршрут или точка не найдены.")
        return

    await sync_to_async(route_point.delete)()

    await callback.message.answer(
        f"✅ Точка '{point.name}' успешно удалена из маршрута '{route.name}'",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 Вернуться к маршруту",
                        callback_data=f"view_route:{route_id}"
                    )
                ]
            ]
        )
    )


@router.callback_query(F.data.startswith("edit_rt:"))
async def handle_edit_route(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    route_id = callback.data.split(":")[1]
    try:
        route = await Route.objects.aget(id=uuid.UUID(route_id))
    except (Route.DoesNotExist, ValueError):
        await callback.message.answer("Маршрут не найден.")
        return

    await state.set_state(RouteStates.editing_route)
    await state.update_data(route_id=str(route.id))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Название", callback_data="edit_route_name"),
                InlineKeyboardButton(text="📄 Описание", callback_data="edit_route_description")
            ],
            [
                InlineKeyboardButton(text="📸 Фото", callback_data="edit_route_photo")
            ],
            [
                InlineKeyboardButton(text="🔙 Отмена", callback_data=f"view_route:{str(route.id)}")
            ]
        ]
    )

    await callback.message.answer(
        "Выберите, что хотите отредактировать:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "edit_route_name")
async def handle_edit_route_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    data = await state.get_data()
    route_id = data.get('route_id')
    if not route_id:
        await callback.message.answer("Ошибка: маршрут не найден.")
        await state.clear()
        return

    await state.set_state(RouteStates.waiting_for_route_name)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")
            ]
        ]
    )
    await callback.message.answer("Введите новое название маршрута:", reply_markup=keyboard)


@router.callback_query(F.data == "edit_route_description")
async def handle_edit_route_description(callback: CallbackQuery, state: FSMContext):
    """Редактирование описания маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    data = await state.get_data()
    route_id = data.get('route_id')
    if not route_id:
        await callback.message.answer("Ошибка: маршрут не найден.")
        await state.clear()
        return

    await state.set_state(RouteStates.waiting_for_route_description)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")
            ]
        ]
    )
    await callback.message.answer("Введите новое описание маршрута:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("edit_pt:"))
async def handle_edit_point(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования точки"""
    if not await check_admin(callback.from_user.id):
        return

    short_point_id = callback.data.split(":")[1]

    try:
        # Поиск UUID по startswith вручную (медленно, но работает)
        all_points = await sync_to_async(list)(
            Point.objects.filter(id__icontains=short_point_id)
        )
        if not all_points:
            raise Point.DoesNotExist
        elif len(all_points) > 1:
            await callback.message.answer("Найдено несколько точек с таким ID. Уточните ID.")
            return

        point = all_points[0]

    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    await state.set_state(RouteStates.editing_point)
    await state.update_data(point_id=str(point.id))

    short_id = str(point.id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Название", callback_data="edit_point_name"),
                InlineKeyboardButton(text="📄 Описание", callback_data="edit_point_description")
            ],
            [
                InlineKeyboardButton(text="📍 Локация", callback_data="edit_point_location"),
                InlineKeyboardButton(text="📝 Текст", callback_data=f"edit_pt_text:{short_id}")
            ],
            [
                InlineKeyboardButton(text="🔄 Изменить фото", callback_data=f"edit_pt_photo:{short_id}"),
                InlineKeyboardButton(text="➕ Добавить фото", callback_data=f"add_pt_photo:{short_id}")
            ],
            [
                InlineKeyboardButton(text="🔄 Изменить аудио", callback_data=f"edit_pt_audio:{short_id}"),
                InlineKeyboardButton(text="➕ Добавить аудио", callback_data=f"add_pt_audio:{short_id}")
            ],
            [
                InlineKeyboardButton(text="🔄 Изменить видео", callback_data=f"edit_pt_video:{short_id}"),
                InlineKeyboardButton(text="➕ Добавить видео", callback_data=f"add_pt_video:{short_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 Отмена", callback_data=f"view_pt:{short_id}")
            ]
        ]
    )

    await callback.message.answer(
        "Выберите, что хотите отредактировать:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("del_pt:"))
async def handle_delete_point(callback: CallbackQuery):
    """Удаление точки"""
    if not await check_admin(callback.from_user.id):
        return

    short_point_id = callback.data.split(":")[1]
    logging.info(short_point_id)
    try:
        point = await Point.objects.aget(id=uuid.UUID(short_point_id))
    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    route_points = await sync_to_async(RoutePoint.objects.filter(point=point).count)()
    if route_points > 0:
        await callback.message.answer(
            "Нельзя удалить точку, так как она используется в маршрутах. "
            "Сначала удалите точку из всех маршрутов."
        )
        return

    await point.adelete()
    await callback.message.answer("Точка успешно удалена.")
    await handle_list_points_callback(callback)


@router.callback_query(F.data.startswith("edit_pt_text:"))
async def handle_edit_point_text(callback: CallbackQuery, state: FSMContext):
    """Редактирование текста точки"""
    if not await check_admin(callback.from_user.id):
        return

    short_point_id = callback.data.split(":")[1]
    try:
        point = await Point.objects.aget(id=uuid.UUID(short_point_id))
    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    await state.set_state(RouteStates.waiting_for_point_text)
    await state.update_data(point_id=str(point.id))
    await callback.message.answer("Введите новый текст для точки:")


@router.callback_query(F.data.startswith("edit_pt_photo:"))
async def handle_edit_point_photo(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования фото точки"""
    if not await check_admin(callback.from_user.id):
        return

    short_point_id = callback.data.split(":")[1]
    try:
        all_points = await sync_to_async(list)(
            Point.objects.filter(id__icontains=short_point_id)
        )
        if not all_points:
            raise Point.DoesNotExist
        elif len(all_points) > 1:
            await callback.message.answer("Найдено несколько точек с таким ID. Уточните ID.")
            return

        point = all_points[0]
    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    photos = await sync_to_async(list)(point.photos.all())
    has_old_photo = bool(point.photo)
    
    total_photos = len(photos) + (1 if has_old_photo else 0)
    
    if total_photos == 0:
        await callback.message.answer("У этой точки нет фото для редактирования.")
        return
    elif total_photos == 1:
        if has_old_photo:
            await state.set_state(RouteStates.waiting_for_point_photo)
            await state.update_data(point_id=str(point.id), mode="edit", photo_type="old")
        else:
            await state.set_state(RouteStates.waiting_for_point_photo)
            await state.update_data(point_id=str(point.id), mode="edit", photo_type="new", photo_id=str(photos[0].id))
        
        await callback.message.answer(
            "Отправьте новое фото для замены существующего.\n"
            "Нажмите на кнопку 📎 и выберите 'Фото'"
        )
    else:
        keyboard = []
        
        if has_old_photo:
            keyboard.append([
                InlineKeyboardButton(
                    text="📸 Основное фото (старое)",
                    callback_data=f"edit_photo_old:{short_point_id}"
                )
            ])
        
        for i, photo in enumerate(photos, 1):
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📸 Дополнительное фото {i}",
                    callback_data=f"edit_photo_new:{short_point_id}:{str(photo.id)[:8]}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(text="🔙 Отмена", callback_data=f"view_pt:{short_point_id}")
        ])
        
        await callback.message.answer(
            "Выберите, какое фото хотите заменить:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.message(RouteStates.waiting_for_point_photo, F.photo)
async def handle_point_photo_edit(message: Message, state: FSMContext, bot):
    """Сохранение/добавление фото точки"""
    if not await check_admin(message.from_user.id):
        return

    data = await state.get_data()
    point_id = data.get('point_id')
    mode = data.get('mode', 'add')
    photo_type = data.get('photo_type', 'old')
    photo_id = data.get('photo_id')
    
    if not point_id:
        await message.answer("Ошибка: точка не найдена.")
        await state.clear()
        return

    try:
        if len(point_id) <= 8:
            all_points = await sync_to_async(list)(
                Point.objects.filter(id__icontains=point_id)
            )
            if not all_points:
                raise Point.DoesNotExist
            point = all_points[0]
        else:
            point = await Point.objects.aget(id=point_id)
    except Point.DoesNotExist:
        await message.answer("Точка не найдена.")
        await state.clear()
        return

    photo = message.photo[-1]
    try:
        photo_file = await bot.get_file(photo.file_id)
        photo_bytes_io = await bot.download_file(photo_file.file_path)
        photo_bytes = photo_bytes_io.getvalue()
    except Exception as e:
        if "file is too big" in str(e):
            await message.answer("❌ Файл слишком большой! Максимальный размер фото: 10 МБ")
        else:
            await message.answer(f"❌ Ошибка при загрузке файла: {e}")
        await state.clear()
        return

    from django.core.files.base import ContentFile
    
    if mode == "edit":
        if photo_type == "old":
            @sync_to_async
            def update_photo():
                point.photo.save(f"{point.name}.jpg", ContentFile(photo_bytes), save=True)
                return point
            
            await update_photo()
            await message.answer("Основное фото точки успешно обновлено.")
        else:
            @sync_to_async
            def update_specific_photo():
                try:
                    photo_obj = PointPhoto.objects.get(id__icontains=photo_id, point=point)
                    photo_obj.image.save(f"{point.name}_{photo.file_id}.jpg", ContentFile(photo_bytes), save=True)
                    return photo_obj
                except PointPhoto.DoesNotExist:
                    return None
            
            result = await update_specific_photo()
            if result:
                await message.answer("Дополнительное фото точки успешно обновлено.")
            else:
                await message.answer("Ошибка: выбранное фото не найдено.")
    else:
        @sync_to_async
        def create_photo():
            photo_obj = PointPhoto(point=point)
            photo_obj.image.save(f"{point.name}_{photo.file_id}.jpg", ContentFile(photo_bytes), save=True)
            return photo_obj
        
        await create_photo()
        await message.answer("Фото точки успешно добавлено.")

    await state.clear()

    new_callback = CallbackQuery(
        id=str(message.message_id),
        from_user=message.from_user,
        chat_instance=str(message.chat.id),
        message=message,
        data=f"view_pt:{str(point.id)[:8]}"
    )
    await handle_view_point(new_callback)

@router.message(RouteStates.waiting_for_point_audio, F.audio)
async def handle_point_audio_edit(message: Message, state: FSMContext, bot):
    """Сохранение нового аудио точки (теперь можно несколько)"""
    if not await check_admin(message.from_user.id):
        return

    data = await state.get_data()
    point_id = data.get('point_id')
    mode = data.get('mode', 'add')
    if not point_id:
        await message.answer("Ошибка: точка не найдена.")
        await state.clear()
        return

    try:
        point = await Point.objects.aget(id=point_id)
    except Point.DoesNotExist:
        await message.answer("Точка не найдена.")
        await state.clear()
        return

    audio = message.audio
    try:
        audio_file = await bot.get_file(audio.file_id)
        audio_bytes_io = await bot.download_file(audio_file.file_path)
        audio_bytes = audio_bytes_io.getvalue()
    except Exception as e:
        if "file is too big" in str(e):
            await message.answer("❌ Файл слишком большой! Максимальный размер аудио: 50 МБ")
        else:
            await message.answer(f"❌ Ошибка при загрузке файла: {e}")
        await state.clear()
        return

    from django.core.files.base import ContentFile
    
    if mode == "edit":
        @sync_to_async
        def update_audio():
            point.audio_file.save(f"{point.name}.mp3", ContentFile(audio_bytes), save=True)
            return point
        
        await update_audio()
        await message.answer("Аудио точки успешно обновлено.")
    else:
        @sync_to_async
        def create_audio():
            audio_obj = PointAudio(point=point)
            audio_obj.file.save(f"{point.name}_{audio.file_id}.mp3", ContentFile(audio_bytes), save=True)
            return audio_obj
        
        await create_audio()
        await message.answer("Аудио точки успешно добавлено.")

    await state.clear()

    new_callback = CallbackQuery(
        id=str(message.message_id),
        from_user=message.from_user,
        chat_instance=str(message.chat.id),
        message=message,
        data=f"view_pt:{str(point.id)[:8]}"
    )
    await handle_view_point(new_callback)

@router.message(RouteStates.waiting_for_point_video, F.video)
async def handle_point_video_edit(message: Message, state: FSMContext):
    """Сохранение нового видео точки (теперь можно несколько)"""
    if not await check_admin(message.from_user.id):
        return

    data = await state.get_data()
    point_id = data.get('point_id')
    mode = data.get('mode', 'add')

    try:
        point = await Point.objects.aget(id=point_id)
    except Point.DoesNotExist:
        await message.answer("Точка не найдена.")
        await state.clear()
        return

    video = message.video
    try:
        file = await message.bot.get_file(video.file_id)
        file_path = file.file_path
        video_bytes = await message.bot.download_file(file_path)
    except Exception as e:
        if "file is too big" in str(e):
            await message.answer("❌ Файл слишком большой! Максимальный размер видео: 50 МБ")
        else:
            await message.answer(f"❌ Ошибка при загрузке файла: {e}")
        await state.clear()
        return

    from django.core.files.base import ContentFile
    
    if mode == "edit":
        @sync_to_async
        def update_video():
            point.video_file.save(f"{point.name}.mp4", ContentFile(video_bytes.read()), save=True)
            return point
        
        await update_video()
        await message.answer("Видео успешно обновлено!")
    else:
        @sync_to_async
        def create_video():
            video_obj = PointVideo(point=point)
            video_obj.file.save(f"{point.name}_{video.file_id}.mp4", ContentFile(video_bytes.read()), save=True)
            return video_obj
        
        await create_video()
        await message.answer("Видео успешно добавлено!")

    await state.clear()

    short_point_id = str(point.id)[:8]
    await handle_view_point(CallbackQuery(
        id=str(message.message_id),
        from_user=message.from_user,
        chat_instance=str(message.chat.id),
        message=message,
        data=f"view_pt:{short_point_id}"
    ))


@router.callback_query(F.data == "edit_point_name")
async def handle_edit_point_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия точки"""
    if not await check_admin(callback.from_user.id):
        return

    data = await state.get_data()
    point_id = data.get('point_id')
    if not point_id:
        await callback.message.answer("Ошибка: точка не найдена.")
        await state.clear()
        return

    await state.set_state(RouteStates.editing_point_name)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")
            ]
        ]
    )
    await callback.message.answer("Введите новое название точки:", reply_markup=keyboard)


@router.callback_query(F.data == "edit_point_description")
async def handle_edit_point_description(callback: CallbackQuery, state: FSMContext):
    """Редактирование описания точки"""
    if not await check_admin(callback.from_user.id):
        return

    data = await state.get_data()
    point_id = data.get('point_id')
    if not point_id:
        await callback.message.answer("Ошибка: точка не найдена.")
        await state.clear()
        return

    await state.set_state(RouteStates.editing_point_description)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")
            ]
        ]
    )
    await callback.message.answer("Введите новое описание точки:", reply_markup=keyboard)


@router.callback_query(F.data == "edit_point_location")
async def handle_edit_point_location(callback: CallbackQuery, state: FSMContext):
    """Редактирование локации точки"""
    if not await check_admin(callback.from_user.id):
        return

    data = await state.get_data()
    point_id = data.get('point_id')
    if not point_id:
        await callback.message.answer("Ошибка: точка не найдена.")
        await state.clear()
        return

    await state.set_state(RouteStates.editing_point_location)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")
            ]
        ]
    )
    await callback.message.answer(
        "Отправьте новую локацию точки.\n"
        "Нажмите на кнопку 📎 и выберите 'Локация'",
        reply_markup=keyboard
    )


@router.message(RouteStates.editing_point_name)
async def handle_point_name_edit(message: Message, state: FSMContext):
    """Сохранение нового названия точки"""
    if not await check_admin(message.from_user.id):
        return

    data = await state.get_data()
    point_id = data.get('point_id')
    if not point_id:
        await message.answer("Ошибка: точка не найдена.")
        await state.clear()
        return

    try:
        point = await Point.objects.aget(id=point_id)
    except Point.DoesNotExist:
        await message.answer("Точка не найдена.")
        await state.clear()
        return

    point.name = message.text
    await point.asave()

    await message.answer("Название точки успешно обновлено.")
    await state.clear()

    new_callback = CallbackQuery(
        id=str(message.message_id),
        from_user=message.from_user,
        chat_instance=str(message.chat.id),
        message=message,
        data=f"view_pt:{str(point.id)[:8]}"
    )
    await handle_view_point(new_callback)


@router.message(RouteStates.editing_point_description)
async def handle_point_description_edit(message: Message, state: FSMContext):
    """Сохранение нового описания точки"""
    if not await check_admin(message.from_user.id):
        return

    data = await state.get_data()
    point_id = data.get('point_id')
    if not point_id:
        await message.answer("Ошибка: точка не найдена.")
        await state.clear()
        return

    try:
        point = await Point.objects.aget(id=point_id)
    except Point.DoesNotExist:
        await message.answer("Точка не найдена.")
        await state.clear()
        return

    point.description = message.text
    await point.asave()

    await message.answer("Описание точки успешно обновлено.")
    await state.clear()

    new_callback = CallbackQuery(
        id=str(message.message_id),
        from_user=message.from_user,
        chat_instance=str(message.chat.id),
        message=message,
        data=f"view_pt:{str(point.id)[:8]}"
    )
    await handle_view_point(new_callback)


@router.message(RouteStates.editing_point_location, F.location)
async def handle_point_location_edit(message: Message, state: FSMContext):
    """Сохранение новой локации точки"""
    if not await check_admin(message.from_user.id):
        return

    data = await state.get_data()
    point_id = data.get('point_id')
    if not point_id:
        await message.answer("Ошибка: точка не найдена.")
        await state.clear()
        return

    try:
        point = await Point.objects.aget(id=point_id)
    except Point.DoesNotExist:
        await message.answer("Точка не найдена.")
        await state.clear()
        return

    point.latitude = message.location.latitude
    point.longitude = message.location.longitude
    await point.asave()

    await message.answer("Локация точки успешно обновлена.")
    await state.clear()

    new_callback = CallbackQuery(
        id=str(message.message_id),
        from_user=message.from_user,
        chat_instance=str(message.chat.id),
        message=message,
        data=f"view_pt:{str(point.id)[:8]}"
    )
    await handle_view_point(new_callback)


@router.callback_query(F.data.startswith("view_pt:"))
async def handle_view_point(callback: CallbackQuery):
    """Просмотр конкретной точки (теперь все медиа)"""
    if not await check_admin(callback.from_user.id):
        return

    short_point_id = callback.data.split(":")[1]
    try:
        all_points = await sync_to_async(list)(
            Point.objects.filter(id__icontains=short_point_id)
        )
        if not all_points:
            raise Point.DoesNotExist
        elif len(all_points) > 1:
            await callback.message.answer("Найдено несколько точек с таким ID. Уточните ID.")
            return

        point = all_points[0]
    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    point_id = str(point.id)

    photos = await sync_to_async(list)(point.photos.all())
    print(f"DEBUG: Point {point.name} has {len(photos)} photos in PointPhoto table")
    if point.photo:
        print(f"DEBUG: Point {point.name} also has old photo field: {point.photo.url}")
    
    if photos:
        from aiogram.types import InputMediaPhoto
        media_group = []
        for i, photo in enumerate(photos):
            print(f"DEBUG: Adding photo {i+1}: {photo.image.url}")
            media_group.append(InputMediaPhoto(
                media=URLInputFile(photo.image.url),
                caption=f"📍 {point.name}" if i == 0 else None
            ))
        print(f"DEBUG: Sending media group with {len(media_group)} photos")
        try:
            await callback.message.answer_media_group(media_group)
            print(f"DEBUG: Media group sent successfully")
        except Exception as e:
            print(f"DEBUG: Error sending media group: {e}")
            for i, photo in enumerate(photos):
                try:
                    await callback.message.answer_photo(
                        photo=URLInputFile(photo.image.url),
                        caption=f"📍 {point.name} (фото {i+1}/{len(photos)})"
                    )
                except Exception as photo_error:
                    print(f"DEBUG: Error sending individual photo {i+1}: {photo_error}")
    elif point.photo:
        print(f"DEBUG: Sending old photo field")
        await callback.message.answer_photo(
            photo=URLInputFile(point.photo.url),
            caption=f"📍 {point.name}"
        )
    else:
        print(f"DEBUG: No photos found, sending text message")
        await callback.message.answer(
            f"📍 Точка: {point.name}\n"
            f"ID: {point.id}\n"
            f"Описание: {point.description}\n"
            f"Создана: {point.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"Координаты: {point.latitude}, {point.longitude}\n"
            f"Текст: {point.text_content if point.text_content else 'Нет'}\n"
            f"Аудио: {'Есть' if point.audio_file else 'Нет'}\n"
            f"Видео: {'Есть' if point.video_file else 'Нет'}"
        )

    if point.description or point.text_content:
        text = ""
        if point.description:
            text += f"📝 {point.description}\n\n"
        if point.text_content:
            text += f"📄 {point.text_content}"
        await callback.message.answer(text)

    audios = await sync_to_async(list)(point.audios.all())
    for audio in audios:
        await callback.message.answer_audio(
            audio=URLInputFile(audio.file.url),
            caption=f"🎵 {point.name}"
        )
    if point.audio_file and not audios:
        await callback.message.answer_audio(
            audio=URLInputFile(point.audio_file.url),
            caption=f"🎵 {point.name}"
        )

    videos = await sync_to_async(list)(point.videos.all())
    for video in videos:
        try:
            await callback.message.answer_video(
                video=URLInputFile(video.file.url),
                caption=f"🎥 {point.name}",
                width=None,
                height=None
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке видео: {e}")
            await callback.message.answer("Не удалось загрузить видео точки.")
    if point.video_file and point.video_file.name and not videos:
        try:
            await callback.message.answer_video(
                video=URLInputFile(point.video_file.url),
                caption=f"🎥 {point.name}",
                width=None,
                height=None
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке видео: {e}")
            await callback.message.answer("Не удалось загрузить видео точки.")



    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_pt:{point_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_pt:{point_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад к списку", callback_data="list_points")
            ]
        ]
    )

    await callback.message.answer(
        "Выберите действие:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("del_rt:"))
async def handle_delete_route(callback: CallbackQuery):
    """Удаление маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    route_id = callback.data.split(":")[1]
    try:
        route = await Route.objects.aget(id=uuid.UUID(route_id))
    except (Route.DoesNotExist, ValueError):
        await callback.message.answer("Маршрут не найден.")
        return

    await route.adelete()
    await callback.message.answer("Маршрут успешно удален.")
    await handle_list_routes_callback(callback)


@router.callback_query(F.data == "cancel_edit")
async def handle_cancel_edit(callback: CallbackQuery, state: FSMContext):
    """Отмена редактирования"""
    if not await check_admin(callback.from_user.id):
        return

    try:
        data = await state.get_data()
        point_id = data.get('point_id')
        route_id = data.get('route_id')

        await state.clear()

        if point_id:
            await handle_view_point(CallbackQuery(message=callback.message, data=f"view_pt:{str(point_id)}"))
        elif route_id:
            await handle_view_route(CallbackQuery(message=callback.message, data=f"view_route:{str(route_id)}"))
    except Exception as e:
        await callback.message.answer("Произошла ошибка при отмене редактирования.")
        await state.clear()


@router.callback_query(F.data.startswith("edit_pt_audio:"))
async def handle_edit_point_audio(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования аудио точки"""
    if not await check_admin(callback.from_user.id):
        return

    short_point_id = callback.data.split(":")[1]
    try:
        point = await Point.objects.aget(id=uuid.UUID(short_point_id))
    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    await state.set_state(RouteStates.waiting_for_point_audio)
    await state.update_data(point_id=str(point.id), mode="edit")
    await callback.message.answer(
        "Отправьте новое аудио для замены существующего.\nНажмите на скрепку и выберите 'Аудио'."
    )


@router.callback_query(F.data.startswith("edit_pt_video:"))
async def handle_edit_point_video(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования видео точки"""
    if not await check_admin(callback.from_user.id):
        return

    short_point_id = callback.data.split(":")[1]
    try:
        point = await Point.objects.aget(id=uuid.UUID(short_point_id))
    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    await state.set_state(RouteStates.waiting_for_point_video)
    await state.update_data(point_id=str(point.id), mode="edit")
    await callback.message.answer(
        "Отправьте новое видео для замены существующего (или отправьте /cancel для отмены)."
    )

@router.callback_query(F.data == "edit_route_photo")
async def handle_edit_route_photo(callback: CallbackQuery, state: FSMContext):
    """Редактирование фото маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    data = await state.get_data()
    route_id = data.get('route_id')
    if not route_id:
        await callback.message.answer("Ошибка: маршрут не найден.")
        await state.clear()
        return

    try:
        route = await Route.objects.aget(id=route_id)
    except Route.DoesNotExist:
        await callback.message.answer("Маршрут не найден.")
        await state.clear()
        return

    if route.photo:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Заменить фото", callback_data="replace_route_photo"),
                    InlineKeyboardButton(text="🗑 Удалить фото", callback_data="delete_route_photo")
                ],
                [
                    InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")
                ]
            ]
        )
        await callback.message.answer_photo(
            photo=URLInputFile(route.photo.url),
            caption="Текущее фото маршрута. Выберите действие:",
            reply_markup=keyboard
        )
    else:
        await state.set_state(RouteStates.editing_route_photo)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")
                ]
            ]
        )
        await callback.message.answer(
            "Отправьте фото для маршрута.\nНажмите на кнопку 📎 и выберите 'Фото'",
            reply_markup=keyboard
        )

@router.message(RouteStates.editing_route_photo, F.photo)
async def handle_route_photo_save(message: Message, state: FSMContext, bot):
    """Сохранение фото маршрута"""
    if not await check_admin(message.from_user.id):
        return

    data = await state.get_data()
    route_id = data.get('route_id')
    if not route_id:
        await message.answer("Ошибка: маршрут не найден.")
        await state.clear()
        return

    try:
        route = await Route.objects.aget(id=route_id)
    except Route.DoesNotExist:
        await message.answer("Маршрут не найден.")
        await state.clear()
        return

    photo = message.photo[-1]
    try:
        photo_file = await bot.get_file(photo.file_id)
        photo_bytes_io = await bot.download_file(photo_file.file_path)
        photo_bytes = photo_bytes_io.getvalue()
    except Exception as e:
        if "file is too big" in str(e):
            await message.answer("❌ Файл слишком большой! Максимальный размер фото: 10 МБ")
        else:
            await message.answer(f"❌ Ошибка при загрузке файла: {e}")
        await state.clear()
        return

    from django.core.files.base import ContentFile
    
    @sync_to_async
    def save_photo():
        route.photo.save(f"{route.name}.jpg", ContentFile(photo_bytes), save=True)
        return route
    
    await save_photo()
    await message.answer("Фото маршрута успешно сохранено.")
    await state.clear()

    new_callback = CallbackQuery(
        id=str(message.message_id),
        from_user=message.from_user,
        chat_instance=str(message.chat.id),
        message=message,
        data=f"view_route:{str(route.id)}"
    )
    await handle_view_route(new_callback)

@router.callback_query(F.data == "replace_route_photo")
async def handle_replace_route_photo(callback: CallbackQuery, state: FSMContext):
    """Замена фото маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    await state.set_state(RouteStates.editing_route_photo)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")
            ]
        ]
    )
    await callback.message.answer(
        "Отправьте новое фото для замены.\nНажмите на кнопку 📎 и выберите 'Фото'",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "delete_route_photo")
async def handle_delete_route_photo(callback: CallbackQuery, state: FSMContext):
    """Удаление фото маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    data = await state.get_data()
    route_id = data.get('route_id')
    if not route_id:
        await callback.message.answer("Ошибка: маршрут не найден.")
        await state.clear()
        return

    try:
        route = await Route.objects.aget(id=route_id)
        
        @sync_to_async
        def delete_photo():
            if route.photo:
                route.photo.delete()
                route.save()
                return True
            return False
        
        result = await delete_photo()
        
        if result:
            await callback.message.answer("Фото маршрута успешно удалено.")
        else:
            await callback.message.answer("У маршрута нет фото для удаления.")
        
        await state.clear()
        
        new_callback = CallbackQuery(
            id=str(callback.id),
            from_user=callback.from_user,
            chat_instance=callback.chat_instance,
            message=callback.message,
            data=f"view_route:{str(route.id)}"
        )
        await handle_view_route(new_callback)
        
    except Route.DoesNotExist:
        await callback.message.answer("Маршрут не найден.")
        await state.clear()


@router.callback_query(F.data.startswith("add_pt_photo:"))
async def handle_add_point_photo(callback: CallbackQuery, state: FSMContext):
    """Добавление нового фото к точке"""
    if not await check_admin(callback.from_user.id):
        return

    point_id = callback.data.split(":")[1]
    try:
        point = await Point.objects.aget(id=point_id)
    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    await state.set_state(RouteStates.waiting_for_point_photo)
    await state.update_data(point_id=str(point.id), mode="add")
    await callback.message.answer(
        "Отправьте новое фото для добавления к точке.\n"
        "Нажмите на кнопку 📎 и выберите 'Фото'"
    )

@router.callback_query(F.data.startswith("add_pt_audio:"))
async def handle_add_point_audio(callback: CallbackQuery, state: FSMContext):
    """Добавление нового аудио к точке"""
    if not await check_admin(callback.from_user.id):
        return

    point_id = callback.data.split(":")[1]
    try:
        point = await Point.objects.aget(id=point_id)
    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    await state.set_state(RouteStates.waiting_for_point_audio)
    await state.update_data(point_id=str(point.id), mode="add")
    await callback.message.answer(
        "Отправьте новое аудио для добавления к точке.\nНажмите на скрепку и выберите 'Аудио'."
    )

@router.callback_query(F.data.startswith("add_pt_video:"))
async def handle_add_point_video(callback: CallbackQuery, state: FSMContext):
    """Добавление нового видео к точке"""
    if not await check_admin(callback.from_user.id):
        return

    point_id = callback.data.split(":")[1]
    try:
        point = await Point.objects.aget(id=point_id)
    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    await state.set_state(RouteStates.waiting_for_point_video)
    await state.update_data(point_id=str(point.id), mode="add")
    await callback.message.answer(
        "Отправьте новое видео для добавления к точке (или отправьте /cancel для отмены)."
    )

@router.callback_query(F.data.startswith("edit_photo_old:"))
async def handle_edit_old_photo(callback: CallbackQuery, state: FSMContext):
    """Редактирование старого фото точки"""
    if not await check_admin(callback.from_user.id):
        return

    short_point_id = callback.data.split(":")[1]
    await state.set_state(RouteStates.waiting_for_point_photo)
    await state.update_data(point_id=short_point_id, mode="edit", photo_type="old")
    await callback.message.answer(
        "Отправьте новое фото для замены основного фото.\n"
        "Нажмите на кнопку 📎 и выберите 'Фото'"
    )

@router.callback_query(F.data.startswith("edit_photo_new:"))
async def handle_edit_new_photo(callback: CallbackQuery, state: FSMContext):
    """Редактирование нового фото точки"""
    if not await check_admin(callback.from_user.id):
        return

    parts = callback.data.split(":")
    short_point_id = parts[1]
    photo_id = parts[2]
    
    await state.set_state(RouteStates.waiting_for_point_photo)
    await state.update_data(point_id=short_point_id, mode="edit", photo_type="new", photo_id=photo_id)
    await callback.message.answer(
        "Отправьте новое фото для замены выбранного дополнительного фото.\n"
        "Нажмите на кнопку 📎 и выберите 'Фото'"
    )

@router.callback_query(F.data.startswith("add_route_photo:"))
async def handle_add_route_photo(callback: CallbackQuery, state: FSMContext):
    """Добавление фото к новому маршруту"""
    if not await check_admin(callback.from_user.id):
        return

    route_id = callback.data.split(":")[1]
    try:
        route = await Route.objects.aget(id=route_id)
    except Route.DoesNotExist:
        await callback.message.answer("Маршрут не найден.")
        return

    await state.set_state(RouteStates.editing_route_photo)
    await state.update_data(route_id=str(route.id))
    await callback.message.answer(
        "Отправьте фото для маршрута.\n"
        "Нажмите на кнопку 📎 и выберите 'Фото'"
    )

@router.callback_query(F.data.startswith("filter_points:"))
async def handle_filter_points(callback: CallbackQuery):
    """Обработка фильтрации точек"""
    if not await check_admin(callback.from_user.id):
        return

    filter_type = callback.data.split(":")[1]
    
    if filter_type == "by_date":
        # Сортировка по дате создания
        points = await sync_to_async(list)(Point.objects.all().order_by('-created_at'))
        if not points:
            await callback.message.answer("Список точек пуст.")
            return
        
        text = "📅 Точки по дате создания:\n\n"
        for i, point in enumerate(points[:20], 1):  # Показываем первые 20
            text += f"{i}. {point.name}\n"
            text += f"   📅 {point.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            text += f"   📍 {point.description[:50]}{'...' if len(point.description) > 50 else ''}\n\n"
        
        if len(points) > 20:
            text += f"... и еще {len(points) - 20} точек"
        
        keyboard = []
        for point in points[:20]:
            short_point_id = str(point.id)[:8]
            keyboard.append([
                InlineKeyboardButton(
                    text=f"👁️ {point.name}",
                    callback_data=f"view_pt:{short_point_id}"
                )
            ])
        keyboard.append([InlineKeyboardButton(text="🔙 К фильтрам", callback_data="list_points")])
        
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        return
    
    # Получаем отфильтрованные точки с пагинацией
    page_obj, total_pages = await get_filtered_points(filter_type, page=1)
    
    if not page_obj:
        await callback.message.answer("По выбранному фильтру точки не найдены.")
        return
    
    # Формируем текст с информацией о точках
    text = f"📋 Точки (страница 1/{total_pages})\n\n"
    
    for point in page_obj:
        # Проверяем, используется ли точка в маршрутах
        route_info = await sync_to_async(lambda: list(RoutePoint.objects.filter(point=point).select_related('route')))()
        
        if route_info:
            routes_text = ", ".join([f"'{rp.route.name}'" for rp in route_info])
            text += f"📍 {point.name}\n"
            text += f"   🗺 В маршрутах: {routes_text}\n"
        else:
            text += f"📍 {point.name} 🆕\n"
            text += f"   🆕 Не используется\n"
        
        text += f"   📝 {point.description[:60]}{'...' if len(point.description) > 60 else ''}\n\n"
    
    # Создаем клавиатуру для точек
    keyboard = []
    for point in page_obj:
        short_point_id = str(point.id)[:8]
        keyboard.append([
            InlineKeyboardButton(
                text=f"👁️ {point.name}",
                callback_data=f"view_pt:{short_point_id}"
            )
        ])
    
    # Добавляем пагинацию, если есть несколько страниц
    if total_pages > 1:
        keyboard.append([
            InlineKeyboardButton(text="◀️", callback_data="current_page"),
            InlineKeyboardButton(text="1", callback_data="current_page"),
            InlineKeyboardButton(text="▶️", callback_data=f"page_points:{filter_type}:2:")
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 К фильтрам", callback_data="list_points")])
    
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "search_points")
async def handle_search_points(callback: CallbackQuery, state: FSMContext):
    """Начало поиска точек по названию"""
    if not await check_admin(callback.from_user.id):
        return
    
    # Проверяем, есть ли последний поисковый запрос
    data = await state.get_data()
    last_search_query = data.get('last_search_query')
    
    if last_search_query:
        # Показываем последний запрос и предлагаем использовать его снова
        keyboard = [
            [InlineKeyboardButton(text=f"🔍 '{last_search_query}'", callback_data=f"repeat_search:{last_search_query}")],
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="new_search")],
            [InlineKeyboardButton(text="🔙 К фильтрам", callback_data="list_points")]
        ]
        
        await callback.message.answer(
            f"🔍 Последний поиск: '{last_search_query}'\n\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        # Первый поиск
        await state.set_state(RouteStates.waiting_for_point_search)
        await callback.message.answer("🔍 Введите название точки для поиска:")

@router.message(RouteStates.waiting_for_point_search)
async def handle_point_search_query(message: Message, state: FSMContext):
    """Обработка поискового запроса"""
    search_query = message.text.strip()
    print(f"DEBUG: Получен поисковый запрос: '{search_query}'")
    
    if len(search_query) < 2:
        await message.answer("❌ Поисковый запрос должен содержать минимум 2 символа.")
        return
    
    # Получаем данные о режиме поиска
    data = await state.get_data()
    mode = data.get('mode')
    route_id = data.get('route_id')
    
    # Получаем результаты поиска
    page_obj, total_pages = await get_filtered_points("search", search_query, page=1)
    
    if not page_obj:
        # Даже при неудачном поиске не очищаем состояние и даем возможность продолжить
        keyboard = [
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_points")],
            [InlineKeyboardButton(text="🔙 К фильтрам", callback_data="list_points")]
        ]
        
        await message.answer(
            f"🔍 По запросу '{search_query}' ничего не найдено.\n\nПопробуйте другой запрос или вернитесь к фильтрам.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        # Сохраняем неудачный запрос для истории
        await state.update_data(last_search_query=search_query)
        return
    
    # Формируем текст результатов
    if mode == "add_to_route":
        text = f"🔍 Результаты поиска по '{search_query}'\n"
        text += f"📋 Найдено: {len(page_obj)} точек для добавления в маршрут\n\n"
    else:
        text = f"🔍 Результаты поиска по '{search_query}'\n"
        text += f"📋 Найдено: {len(page_obj)} из {total_pages} результатов\n\n"
    
    for point in page_obj:
        # Проверяем использование в маршрутах
        route_info = await sync_to_async(lambda: list(RoutePoint.objects.filter(point=point).select_related('route')))()
        
        if route_info:
            routes_text = ", ".join([f"'{rp.route.name}'" for rp in route_info])
            text += f"📍 {point.name}\n"
            text += f"   🗺 В маршрутах: {routes_text}\n"
        else:
            text += f"📍 {point.name} 🆕\n"
            text += f"   🆕 Не используется\n"
        
        text += f"   📝 {point.description[:60]}{'...' if len(point.description) > 60 else ''}\n\n"
    
    # Создаем клавиатуру в зависимости от режима
    keyboard = []
    for point in page_obj:
        short_point_id = str(point.id)[:8]
        
        if mode == "add_to_route":
            # Режим добавления в маршрут
            keyboard.append([
                InlineKeyboardButton(
                    text=f"➕ {point.name}",
                    callback_data=f"sel_pt:{route_id}:{short_point_id}"
                )
            ])
        else:
            # Обычный режим просмотра
            keyboard.append([
                InlineKeyboardButton(
                    text=f"👁️ {point.name}",
                    callback_data=f"view_pt:{short_point_id}"
                )
            ])
    
    # Пагинация для результатов поиска
    if total_pages > 1:
        if mode == "add_to_route":
            keyboard.append([
                InlineKeyboardButton(text="◀️", callback_data="current_page"),
                InlineKeyboardButton(text="1", callback_data="current_page"),
                InlineKeyboardButton(text="▶️", callback_data=f"search_route_page:{route_id}:2:{search_query}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(text="◀️", callback_data="current_page"),
                InlineKeyboardButton(text="1", callback_data="current_page"),
                InlineKeyboardButton(text="▶️", callback_data=f"page_points:search:2:{search_query}")
            ])
    
    # Кнопка возврата в зависимости от режима
    if mode == "add_to_route":
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"add_pt:{route_id}")])
    else:
        # Добавляем кнопку для нового поиска
        keyboard.append([
            InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_points"),
            InlineKeyboardButton(text="🔙 К фильтрам", callback_data="list_points")
        ])
    
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    
    # Не очищаем состояние, чтобы пользователь мог продолжать поиск
    if mode != "add_to_route":
        await state.update_data(last_search_query=search_query)

@router.callback_query(F.data.startswith("page_points:"))
async def handle_points_pagination(callback: CallbackQuery):
    """Обработка пагинации точек"""
    if not await check_admin(callback.from_user.id):
        return
    
    try:
        parts = callback.data.split(":")
        filter_type = parts[1]
        page = int(parts[2])
        search_query = parts[3] if len(parts) > 3 else None
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка пагинации.")
        return
    
    # Получаем точки для указанной страницы
    page_obj, total_pages = await get_filtered_points(filter_type, search_query, page)
    
    if not page_obj:
        await callback.message.answer("На этой странице нет точек.")
        return
    
    # Формируем текст
    if filter_type == "search":
        text = f"🔍 Результаты поиска по '{search_query}'\n"
    else:
        text = f"📋 Точки (страница {page}/{total_pages})\n"
    
    text += f"📋 Найдено: {len(page_obj)} из {total_pages} результатов\n\n"
    
    for point in page_obj:
        # Проверяем использование в маршрутах
        route_info = await sync_to_async(lambda: list(RoutePoint.objects.filter(point=point).select_related('route')))()
        
        if route_info:
            routes_text = ", ".join([f"'{rp.route.name}'" for rp in route_info])
            text += f"📍 {point.name}\n"
            text += f"   🗺 В маршрутах: {routes_text}\n"
        else:
            text += f"📍 {point.name} 🆕\n"
            text += f"   🆕 Не используется\n"
        
        text += f"   📝 {point.description[:60]}{'...' if len(point.description) > 60 else ''}\n\n"
    
    # Создаем клавиатуру
    keyboard = []
    for point in page_obj:
        short_point_id = str(point.id)[:8]
        keyboard.append([
            InlineKeyboardButton(
                text=f"👁️ {point.name}",
                callback_data=f"view_pt:{short_point_id}"
            )
        ])
    
    # Пагинация
    keyboard.append(get_points_pagination_keyboard(page, total_pages, filter_type, search_query).inline_keyboard[0])
    keyboard.append([InlineKeyboardButton(text="🔙 К фильтрам", callback_data="list_points")])
    
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "group_points_by_routes")
async def handle_group_points_by_routes(callback: CallbackQuery):
    """Показать точки, сгруппированные по маршрутам"""
    if not await check_admin(callback.from_user.id):
        return
    
    grouped_points, unused_points = await get_points_by_routes()
    
    if not grouped_points and not unused_points:
        await callback.message.answer("📋 Список точек пуст.")
        return
    
    text = "🗺 Точки по маршрутам:\n\n"
    
    # Группируем по маршрутам
    for route, route_points in grouped_points.items():
        text += f"📍 Маршрут: {route.name}\n"
        text += f"   📝 {route.description[:50]}{'...' if len(route.description) > 50 else ''}\n"
        text += f"   🔢 Количество точек: {len(route_points)}\n\n"
        
        for i, route_point in enumerate(route_points, 1):
            point = route_point.point
            text += f"   {i}. {point.name}\n"
            text += f"      📍 {point.description[:40]}{'...' if len(point.description) > 40 else ''}\n"
        
        text += "\n"
    
    # Неиспользуемые точки
    if unused_points:
        text += f"🆕 Неиспользуемые точки ({len(unused_points)}):\n\n"
        for i, point in enumerate(unused_points[:10], 1):  # Показываем первые 10
            text += f"{i}. {point.name}\n"
            text += f"   📍 {point.description[:40]}{'...' if len(point.description) > 40 else ''}\n"
        
        if len(unused_points) > 10:
            text += f"\n... и еще {len(unused_points) - 10} точек"
    
    # Создаем клавиатуру для быстрого доступа к точкам
    keyboard = []
    
    # Кнопки для маршрутов
    for route in grouped_points.keys():
        keyboard.append([
            InlineKeyboardButton(
                text=f"🗺 {route.name}",
                callback_data=f"view_route_points:{str(route.id)}"
            )
        ])
    
    # Кнопка для неиспользуемых точек
    if unused_points:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🆕 Неиспользуемые ({len(unused_points)})",
                callback_data="filter_points:unused"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 К фильтрам", callback_data="list_points")])
    
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "current_page")
async def handle_current_page(callback: CallbackQuery):
    """Обработка нажатия на текущую страницу (ничего не делает)"""
    await callback.answer("Текущая страница")

@router.callback_query(F.data.startswith("search_for_route:"))
async def handle_search_for_route(callback: CallbackQuery, state: FSMContext):
    """Поиск точки для добавления в маршрут"""
    if not await check_admin(callback.from_user.id):
        return
    
    route_id = callback.data.split(":")[1]
    await state.set_state(RouteStates.waiting_for_point_search)
    await state.update_data(route_id=route_id, mode="add_to_route")
    await callback.message.answer("🔍 Введите название точки для поиска:")

@router.callback_query(F.data.startswith("filter_unused_for_route:"))
async def handle_filter_unused_for_route(callback: CallbackQuery):
    """Показать только неиспользуемые точки для добавления в маршрут"""
    if not await check_admin(callback.from_user.id):
        return
    
    route_id = callback.data.split(":")[1]
    
    try:
        route = await Route.objects.aget(id=uuid.UUID(route_id))
    except (Route.DoesNotExist, ValueError):
        await callback.message.answer("Маршрут не найден.")
        return
    
    # Получаем неиспользуемые точки
    used_point_ids = await sync_to_async(list)(
        RoutePoint.objects.values_list('point_id', flat=True)
    )
    unused_points = await sync_to_async(list)(
        Point.objects.exclude(id__in=used_point_ids).order_by('-created_at')
    )
    
    if not unused_points:
        await callback.message.answer("Нет неиспользуемых точек для добавления в маршрут.")
        return
    
    text = f"🆕 Неиспользуемые точки для маршрута '{route.name}'\n\n"
    text += f"📋 Найдено: {len(unused_points)} точек\n\n"
    
    # Показываем первые 15 точек
    for i, point in enumerate(unused_points[:15], 1):
        text += f"{i}. {point.name}\n"
        text += f"   📍 {point.description[:50]}{'...' if len(point.description) > 50 else ''}\n"
        text += f"   📅 {point.created_at.strftime('%d.%m.%Y')}\n\n"
    
    if len(unused_points) > 15:
        text += f"... и еще {len(unused_points) - 15} точек"
    
    # Создаем клавиатуру
    keyboard = []
    for point in unused_points[:10]:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📍 {point.name}",
                callback_data=f"sel_pt:{str(route.id)}:{str(point.id)}"
            )
        ])
    
    # Пагинация если нужно
    if len(unused_points) > 10:
        keyboard.append([
            InlineKeyboardButton(text="◀️", callback_data="current_page"),
            InlineKeyboardButton(text="1", callback_data="current_page"),
            InlineKeyboardButton(text="▶️", callback_data=f"unused_page:{str(route.id)}:2")
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"add_pt:{str(route.id)}")])
    
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("add_pt_page:"))
async def handle_add_point_page(callback: CallbackQuery):
    """Пагинация при добавлении точек в маршрут"""
    if not await check_admin(callback.from_user.id):
        return
    
    try:
        _, route_id, page = callback.data.split(":")
        page = int(page)
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка пагинации.")
        return
    
    try:
        route = await Route.objects.aget(id=uuid.UUID(route_id))
    except (Route.DoesNotExist, ValueError):
        await callback.message.answer("Маршрут не найден.")
        return
    
    existing_points = await sync_to_async(list)(
        RoutePoint.objects.filter(route=route).values_list('point_id', flat=True))
    available_points = await sync_to_async(list)(Point.objects.exclude(id__in=existing_points))
    
    if not available_points:
        await callback.message.answer("Нет доступных точек для добавления в маршрут.")
        return
    
    # Пагинация
    paginator = Paginator(available_points, 10)
    page_obj = paginator.get_page(page)
    
    text = f"➕ Добавление точки в маршрут '{route.name}'\n"
    text += f"📋 Страница {page}/{paginator.num_pages}\n\n"
    
    for i, point in enumerate(page_obj, 1):
        text += f"{i}. {point.name}\n"
        text += f"   📍 {point.description[:50]}{'...' if len(point.description) > 50 else ''}\n"
        text += f"   📅 {point.created_at.strftime('%d.%m.%Y')}\n\n"
    
    # Создаем клавиатуру
    keyboard = []
    for point in page_obj:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📍 {point.name}",
                callback_data=f"sel_pt:{str(route.id)}:{str(point.id)}"
            )
        ])
    
    # Навигация
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"add_pt_page:{str(route.id)}:{page-1}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page}", callback_data="current_page")
    )
    
    if page < paginator.num_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"add_pt_page:{str(route.id)}:{page+1}")
        )
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"add_pt:{str(route.id)}")])
    
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("search_route_page:"))
async def handle_search_route_page(callback: CallbackQuery):
    """Пагинация поиска при добавлении точек в маршрут"""
    if not await check_admin(callback.from_user.id):
        return
    
    try:
        _, route_id, page, search_query = callback.data.split(":")
        page = int(page)
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка пагинации.")
        return
    
    # Получаем результаты поиска для указанной страницы
    page_obj, total_pages = await get_filtered_points("search", search_query, page)
    
    if not page_obj:
        await callback.message.answer("На этой странице нет результатов.")
        return
    
    # Формируем текст
    text = f"🔍 Результаты поиска по '{search_query}'\n"
    text += f"📋 Страница {page}/{total_pages}\n\n"
    
    for point in page_obj:
        # Проверяем использование в маршрутах
        route_info = await sync_to_async(lambda: list(RoutePoint.objects.filter(point=point).select_related('route')))()
        
        if route_info:
            routes_text = ", ".join([f"'{rp.route.name}'" for rp in route_info])
            text += f"📍 {point.name}\n"
            text += f"   🗺 В маршрутах: {routes_text}\n"
        else:
            text += f"📍 {point.name} 🆕\n"
            text += f"   🆕 Не используется\n"
        
        text += f"   📝 {point.description[:60]}{'...' if len(point.description) > 60 else ''}\n\n"
    
    # Создаем клавиатуру
    keyboard = []
    for point in page_obj:
        short_point_id = str(point.id)[:8]
        keyboard.append([
            InlineKeyboardButton(
                text=f"➕ {point.name}",
                callback_data=f"sel_pt:{route_id}:{short_point_id}"
            )
        ])
    
    # Навигация
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"search_route_page:{route_id}:{page-1}:{search_query}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page}", callback_data="current_page")
    )
    
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"search_route_page:{route_id}:{page+1}:{search_query}")
        )
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"add_pt:{route_id}")])
    
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("view_route_points:"))
async def handle_view_route_points(callback: CallbackQuery):
    """Показать точки конкретного маршрута"""
    if not await check_admin(callback.from_user.id):
        return
    
    route_id = callback.data.split(":")[1]
    try:
        route = await Route.objects.aget(id=uuid.UUID(route_id))
    except (Route.DoesNotExist, ValueError):
        await callback.message.answer("Маршрут не найден.")
        return
    
    # Получаем точки маршрута
    route_points = await sync_to_async(list)(
        RoutePoint.objects.filter(route=route).order_by('order').select_related('point')
    )
    
    if not route_points:
        text = f"🗺 Маршрут: {route.name}\n"
        text += f"📝 {route.description}\n\n"
        text += "❌ В этом маршруте пока нет точек."
        
        keyboard = [
            [InlineKeyboardButton(text="➕ Добавить точку", callback_data=f"add_pt:{str(route.id)}")],
            [InlineKeyboardButton(text="🔙 К маршрутам", callback_data="group_points_by_routes")]
        ]
        
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        return
    
    # Формируем текст с точками маршрута
    text = f"🗺 Маршрут: {route.name}\n"
    text += f"📝 {route.description}\n"
    text += f"🔢 Количество точек: {len(route_points)}\n\n"
    text += "📍 Точки маршрута:\n\n"
    
    for i, route_point in enumerate(route_points, 1):
        point = route_point.point
        text += f"{i}. {point.name}\n"
        text += f"   📍 {point.description[:60]}{'...' if len(point.description) > 60 else ''}\n"
        
        # Проверяем наличие медиа-файлов
        media_info = []
        if point.photo:
            media_info.append("📸")
        if point.audio_file:
            media_info.append("🎵")
        if point.video_file:
            media_info.append("🎥")
        
        if media_info:
            text += f"   {' '.join(media_info)}\n"
        
        text += "\n"
    
    # Создаем клавиатуру для действий с точками
    keyboard = []
    
    # Кнопки для каждой точки
    for i, route_point in enumerate(route_points[:10], 1):  # Показываем первые 10
        point = route_point.point
        keyboard.append([
            InlineKeyboardButton(
                text=f"👁️ {i}. {point.name}",
                callback_data=f"view_pt:{str(point.id)}"
            )
        ])
    
    # Пагинация если точек много
    if len(route_points) > 10:
        keyboard.append([
            InlineKeyboardButton(text="◀️", callback_data="current_page"),
            InlineKeyboardButton(text="1", callback_data="current_page"),
            InlineKeyboardButton(text="▶️", callback_data=f"route_points_page:{str(route.id)}:2")
        ])
    
    # Дополнительные действия
    keyboard.append([
        InlineKeyboardButton(text="➕ Добавить точку", callback_data=f"add_pt:{str(route.id)}"),
        InlineKeyboardButton(text="✏️ Редактировать маршрут", callback_data=f"edit_rt:{str(route.id)}")
    ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 К маршрутам", callback_data="group_points_by_routes")])
    
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("route_points_page:"))
async def handle_route_points_pagination(callback: CallbackQuery):
    """Пагинация для точек маршрута"""
    if not await check_admin(callback.from_user.id):
        return
    
    try:
        _, route_id, page_str = callback.data.split(":")
        page = int(page_str)
        route = await Route.objects.aget(id=uuid.UUID(route_id))
    except (ValueError, Route.DoesNotExist):
        await callback.message.answer("Маршрут не найден.")
        return
    
    # Получаем точки маршрута
    route_points = await sync_to_async(list)(
        RoutePoint.objects.filter(route=route).order_by('order').select_related('point')
    )
    
    if not route_points:
        await callback.message.answer("В этом маршруте нет точек.")
        return
    
    # Настройки пагинации
    points_per_page = 10
    total_pages = (len(route_points) + points_per_page - 1) // points_per_page
    
    if page < 1 or page > total_pages:
        page = 1
    
    # Вычисляем индексы для текущей страницы
    start_idx = (page - 1) * points_per_page
    end_idx = start_idx + points_per_page
    current_points = route_points[start_idx:end_idx]
    
    # Формируем текст с точками маршрута
    text = f"🗺 Маршрут: {route.name}\n"
    text += f"📝 {route.description}\n"
    text += f"🔢 Количество точек: {len(route_points)}\n"
    text += f"📄 Страница {page} из {total_pages}\n\n"
    text += "📍 Точки маршрута:\n\n"
    
    for i, route_point in enumerate(current_points, start_idx + 1):
        point = route_point.point
        text += f"{i}. {point.name}\n"
        text += f"   📍 {point.description[:60]}{'...' if len(point.description) > 60 else ''}\n"
        
        # Проверяем наличие медиа-файлов
        media_info = []
        if point.photo:
            media_info.append("📸")
        if point.audio_file:
            media_info.append("🎵")
        if point.video_file:
            media_info.append("🎥")
        
        if media_info:
            text += f"   {' '.join(media_info)}\n"
        
        text += "\n"
    
    # Создаем клавиатуру для действий с точками
    keyboard = []
    
    # Кнопки для каждой точки на текущей странице
    for i, route_point in enumerate(current_points, start_idx + 1):
        point = route_point.point
        keyboard.append([
            InlineKeyboardButton(
                text=f"👁️ {i}. {point.name}",
                callback_data=f"view_pt:{str(point.id)}"
            )
        ])
    
    # Пагинация
    pagination_row = []
    
    if page > 1:
        pagination_row.append(
            InlineKeyboardButton(text="◀️", callback_data=f"route_points_page:{str(route.id)}:{page - 1}")
        )
    
    pagination_row.append(
        InlineKeyboardButton(text=str(page), callback_data="current_page")
    )
    
    if page < total_pages:
        pagination_row.append(
            InlineKeyboardButton(text="▶️", callback_data=f"route_points_page:{str(route.id)}:{page + 1}")
        )
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Дополнительные действия
    keyboard.append([
        InlineKeyboardButton(text="➕ Добавить точку", callback_data=f"add_pt:{str(route.id)}"),
        InlineKeyboardButton(text="✏️ Редактировать маршрут", callback_data=f"edit_rt:{str(route.id)}")
    ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 К маршрутам", callback_data="group_points_by_routes")])
    
    # Обновляем сообщение вместо отправки нового
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception as e:
        # Если не удалось отредактировать, отправляем новое сообщение
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("repeat_search:"))
async def handle_repeat_search(callback: CallbackQuery, state: FSMContext):
    """Повторный поиск с тем же запросом"""
    if not await check_admin(callback.from_user.id):
        return
    
    search_query = callback.data.split(":", 1)[1]
    
    # Получаем результаты поиска
    page_obj, total_pages = await get_filtered_points("search", search_query, page=1)
    
    if not page_obj:
        # Даже при неудачном поиске даем возможность продолжить
        keyboard = [
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_points")],
            [InlineKeyboardButton(text="🔙 К фильтрам", callback_data="list_points")]
        ]
        
        await callback.message.answer(
            f"🔍 По запросу '{search_query}' ничего не найдено.\n\nПопробуйте другой запрос или вернитесь к фильтрам.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        # Сохраняем неудачный запрос для истории
        await state.update_data(last_search_query=search_query)
        return
    
    # Формируем текст результатов
    text = f"🔍 Результаты поиска по '{search_query}'\n"
    text += f"📋 Найдено: {len(page_obj)} из {total_pages} результатов\n\n"
    
    for point in page_obj:
        # Проверяем использование в маршрутах
        route_info = await sync_to_async(lambda: list(RoutePoint.objects.filter(point=point).select_related('route')))()
        
        if route_info:
            routes_text = ", ".join([f"'{rp.route.name}'" for rp in route_info])
            text += f"📍 {point.name}\n"
            text += f"   🗺 В маршрутах: {routes_text}\n"
        else:
            text += f"📍 {point.name} 🆕\n"
            text += f"   🆕 Не используется\n"
        
        text += f"   📝 {point.description[:60]}{'...' if len(point.description) > 60 else ''}\n\n"
    
    # Создаем клавиатуру
    keyboard = []
    for point in page_obj:
        short_point_id = str(point.id)[:8]
        keyboard.append([
            InlineKeyboardButton(
                text=f"👁️ {point.name}",
                callback_data=f"view_pt:{short_point_id}"
            )
        ])
    
    # Пагинация для результатов поиска
    if total_pages > 1:
        keyboard.append([
            InlineKeyboardButton(text="◀️", callback_data="current_page"),
            InlineKeyboardButton(text="1", callback_data="current_page"),
            InlineKeyboardButton(text="▶️", callback_data=f"page_points:search:2:{search_query}")
        ])
    
    # Кнопки для продолжения поиска
    keyboard.append([
        InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_points"),
        InlineKeyboardButton(text="🔙 К фильтрам", callback_data="list_points")
    ])
    
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.update_data(last_search_query=search_query)

@router.callback_query(F.data == "new_search")
async def handle_new_search(callback: CallbackQuery, state: FSMContext):
    """Начало нового поиска"""
    if not await check_admin(callback.from_user.id):
        return
    
    await state.set_state(RouteStates.waiting_for_point_search)
    await callback.message.answer("🔍 Введите название точки для поиска:")
