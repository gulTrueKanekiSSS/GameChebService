import logger
from aiogram.types.input_file import URLInputFile
import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Video, URLInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from core.models import User, Route, RoutePoint, Point
from django.conf import settings
from django.core.paginator import Paginator
import logging

from bot.states import RouteStates

router = Router()


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
    """Показать список точек"""
    # if not await check_admin(callback.from_user.id):
    #     return
    #
    # points = await sync_to_async(list)(Point.objects.all().order_by('-created_at'))
    # if not points:
    #     await callback.message.answer("Список точек пуст.")
    #     return
    #
    # text = "📋 Список точек:\n\n"
    # for point in points:
    #     text += f"• {point.name}\n"
    #     text += f"  ID: {point.id}\n"
    #     text += f"  Описание: {point.description}\n"
    #     text += f"  Создана: {point.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    #
    # keyboard = []
    # for point in points:
    #     short_point_id = str(point.id)
    #     keyboard.append([
    #         InlineKeyboardButton(
    #             text=f"✏️ {point.name}",
    #             callback_data=f"view_pt:{short_point_id}"
    #         )
    #     ])
    # keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_points_menu")])
    #
    # await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    if not await check_admin(callback.from_user.id):
        return

    points = await sync_to_async(list)(Point.objects.all().order_by('-created_at'))
    if not points:
        await callback.message.answer("Список точек пуст.")
        return

    # Отдельно отправить клавиатуру
    keyboard = []
    for point in points:
        short_point_id = str(point.id)
        keyboard.append([
            InlineKeyboardButton(
                text=f"✏️ {point.name}",
                callback_data=f"view_pt:{short_point_id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_points_menu")])

    await callback.message.answer("Выберите точку:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


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
                    InlineKeyboardButton(text="📸 Добавить фото", callback_data=f"edit_pt_photo:{str(point.id)}")
                ],
                [
                    InlineKeyboardButton(text="🎵 Добавить аудио", callback_data=f"edit_pt_audio:{str(point.id)}"),
                    InlineKeyboardButton(text="🎥 Добавить видео", callback_data=f"edit_pt_video:{str(point.id)}")
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
                        InlineKeyboardButton(text="➕ Добавить точку", callback_data=f"add_pt:{str(route.id)[:8]}"),
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

    short_route_id = callback.data.split(":")[1]

    try:
        route = await Route.objects.aget(id__startswith=short_route_id)
    except Route.DoesNotExist:
        await callback.message.answer("Маршрут не найден.")
        return

    existing_points = await sync_to_async(list)(
        RoutePoint.objects.filter(route=route).values_list('point_id', flat=True))
    available_points = await sync_to_async(list)(Point.objects.exclude(id__in=existing_points))

    if not available_points:
        await callback.message.answer("Нет доступных точек для добавления в маршрут.")
        return

    keyboard = []
    for point in available_points:
        short_point_id = str(point.id)
        keyboard.append([
            InlineKeyboardButton(
                text=point.name,
                callback_data=f"sel_pt:{short_route_id}:{short_point_id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Отмена", callback_data=f"view_route:{route.id}")])

    await callback.message.answer(
        "Выберите точку для добавления в маршрут:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("sel_pt:"))
async def handle_select_point_for_route(callback: CallbackQuery):
    """Обработка выбора точки для добавления в маршрут"""
    if not await check_admin(callback.from_user.id):
        return

    _, short_route_id, short_point_id = callback.data.split(":")

    try:
        route = await Route.objects.aget(id=uuid.UUID(short_route_id))
        point = await Point.objects.aget(id=uuid.UUID(short_point_id))
    except (Route.DoesNotExist, Point.DoesNotExist):
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

    short_route_id = callback.data.split(":")[1]
    try:
        route = await Route.objects.aget(id=uuid.UUID(short_route_id))
    except Route.DoesNotExist:
        await callback.message.answer("Маршрут не найден.")
        return

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
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_rt:{short_route_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_rt:{short_route_id}")
            ],
            [
                InlineKeyboardButton(text="➕ Добавить точку", callback_data=f"add_pt:{short_route_id}"),
                InlineKeyboardButton(text="➖ Удалить точку", callback_data=f"remove_point_from_route:{short_route_id}")
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

    short_route_id = callback.data.split(":")[1]
    try:
        route = await Route.objects.aget(id=uuid.UUID(short_route_id))
    except Route.DoesNotExist:
        await callback.message.answer("Маршрут не найден.")
        return

    route_points = await sync_to_async(list)(
        RoutePoint.objects.filter(route=route).select_related('point').order_by('order'))
    if not route_points:
        await callback.message.answer("В маршруте нет точек.")
        return

    keyboard = []
    for route_point in route_points:
        short_point_id = str(route_point.point.id)[:8]
        keyboard.append([
            InlineKeyboardButton(
                text=route_point.point.name,
                callback_data=f"rm_pt:{short_route_id}:{short_point_id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Отмена", callback_data=f"view_route:{short_route_id}")])

    await callback.message.answer(
        "Выберите точку для удаления из маршрута:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("rm_pt:"))
async def handle_remove_point_from_route_confirm(callback: CallbackQuery):
    """Подтверждение удаления точки из маршрута"""
    if not await check_admin(callback.from_user.id):
        return

    _, short_route_id, short_point_id = callback.data.split(":")
    try:
        route = await Route.objects.aget(id=uuid.UUID(short_route_id))
        point = await Point.objects.aget(id=uuid.UUID(short_point_id))
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
                        callback_data=f"view_route:{short_route_id}"
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

    short_route_id = callback.data.split(":")[1]
    try:
        route = await Route.objects.aget(id=uuid.UUID(short_route_id))
    except Route.DoesNotExist:
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
                InlineKeyboardButton(text="🔙 Отмена", callback_data=f"view_route:{short_route_id}")
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


# @router.callback_query(F.data.startswith("edit_pt:"))
# async def handle_edit_point(callback: CallbackQuery, state: FSMContext):
#     """Начало редактирования точки"""
#     if not await check_admin(callback.from_user.id):
#         return
#
#     short_point_id = callback.data.split(":")[1]
#     try:
#         point = await Point.objects.aget(id=uuid.UUID(short_point_id))
#     except Point.DoesNotExist:
#         await callback.message.answer("Точка не найдена.")
#         return
#
#     await state.set_state(RouteStates.editing_point)
#     await state.update_data(point_id=str(point.id))
#
#     keyboard = InlineKeyboardMarkup(
#         inline_keyboard=[
#             [
#                 InlineKeyboardButton(text="📝 Название", callback_data="edit_point_name"),
#                 InlineKeyboardButton(text="📄 Описание", callback_data="edit_point_description")
#             ],
#             [
#                 InlineKeyboardButton(text="📍 Локация", callback_data="edit_point_location"),
#                 InlineKeyboardButton(text="📝 Текст", callback_data=f"edit_pt_text:{short_point_id}")
#             ],
#             [
#                 InlineKeyboardButton(text="📸 Фото", callback_data=f"edit_pt_photo:{short_point_id}"),
#                 InlineKeyboardButton(text="🎵 Аудио", callback_data=f"edit_pt_audio:{short_point_id}")
#             ],
#             [
#                 InlineKeyboardButton(text="🎥 Видео", callback_data=f"edit_pt_video:{short_point_id}")
#             ],
#             [
#                 InlineKeyboardButton(text="🔙 Отмена", callback_data=f"view_pt:{short_point_id}")
#             ]
#         ]
#     )
#
#     await callback.message.answer(
#         "Выберите, что хотите отредактировать:",
#         reply_markup=keyboard
#     )

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
                InlineKeyboardButton(text="📸 Фото", callback_data=f"edit_pt_photo:{short_id}"),
                InlineKeyboardButton(text="🎵 Аудио", callback_data=f"edit_pt_audio:{short_id}")
            ],
            [
                InlineKeyboardButton(text="🎥 Видео", callback_data=f"edit_pt_video:{short_id}")
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
        point = await Point.objects.aget(id=uuid.UUID(short_point_id))
    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    await state.set_state(RouteStates.waiting_for_point_photo)
    await state.update_data(point_id=str(point.id))
    await callback.message.answer(
        "Отправьте новое фото для точки.\n"
        "Нажмите на кнопку 📎 и выберите 'Фото'"
    )


@router.message(RouteStates.waiting_for_point_photo, F.photo)
async def handle_point_photo_edit(message: Message, state: FSMContext, bot):
    """Сохранение нового фото точки"""
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

    photo = message.photo[-1]
    photo_file = await bot.get_file(photo.file_id)
    photo_bytes_io = await bot.download_file(photo_file.file_path)
    photo_bytes = photo_bytes_io.getvalue()

    from django.core.files.base import ContentFile
    point.photo.save(f"{point.name}.jpg", ContentFile(photo_bytes), save=False)
    await point.asave()

    await message.answer("Фото точки успешно обновлено.")
    await state.clear()

    new_callback = CallbackQuery(
        id=str(message.message_id),
        from_user=message.from_user,
        chat_instance=str(message.chat.id),
        message=message,
        data=f"view_pt:{str(point.id)}"
    )
    await handle_view_point(new_callback)


@router.message(RouteStates.waiting_for_point_audio, F.audio)
async def handle_point_audio_edit(message: Message, state: FSMContext, bot):
    """Сохранение нового аудио точки"""
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

    audio = message.audio
    audio_file = await bot.get_file(audio.file_id)
    audio_bytes_io = await bot.download_file(audio_file.file_path)
    audio_bytes = audio_bytes_io.getvalue()

    from django.core.files.base import ContentFile
    point.audio_file.save(f"{point.name}.mp3", ContentFile(audio_bytes), save=False)
    await point.asave()

    await message.answer("Аудио точки успешно обновлено.")
    await state.clear()

    new_callback = CallbackQuery(
        id=str(message.message_id),
        from_user=message.from_user,
        chat_instance=str(message.chat.id),
        message=message,
        data=f"view_pt:{str(point.id)}"
    )
    await handle_view_point(new_callback)


@router.message(RouteStates.waiting_for_point_text)
async def handle_point_text_edit(message: Message, state: FSMContext):
    """Сохранение нового текста точки"""
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

    point.text_content = message.text
    await point.asave()

    await message.answer("Текст точки успешно обновлен.")
    await state.clear()

    new_callback = CallbackQuery(
        id=str(message.message_id),
        from_user=message.from_user,
        chat_instance=str(message.chat.id),
        message=message,
        data=f"view_pt:{str(point.id)}"
    )
    await handle_view_point(new_callback)


@router.message(RouteStates.waiting_for_point_video, F.video)
async def handle_point_video_edit(message: Message, state: FSMContext):
    """Сохранение нового видео точки"""
    if not await check_admin(message.from_user.id):
        return

    data = await state.get_data()
    point_id = data.get('point_id')

    try:
        point = await Point.objects.aget(id=point_id)
    except Point.DoesNotExist:
        await message.answer("Точка не найдена.")
        await state.clear()
        return

    video = message.video
    file = await message.bot.get_file(video.file_id)
    file_path = file.file_path

    video_bytes = await message.bot.download_file(file_path)

    from django.core.files.base import ContentFile
    point.video_file.save(f"{point.name}.mp4", ContentFile(video_bytes.read()), save=False)
    await point.asave()

    await message.answer("Видео успешно обновлено!")
    await state.clear()

    short_point_id = str(point.id)
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
        data=f"view_pt:{str(point.id)}"
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
        data=f"view_pt:{str(point.id)}"
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
        data=f"view_pt:{str(point.id)}"
    )
    await handle_view_point(new_callback)


@router.callback_query(F.data.startswith("view_pt:"))
async def handle_view_point(callback: CallbackQuery):
    """Просмотр конкретной точки"""
    if not await check_admin(callback.from_user.id):
        return

    short_point_id = callback.data.split(":")[1]
    try:
        point = await Point.objects.aget(id=uuid.UUID(short_point_id))
    except Point.DoesNotExist:
        await callback.message.answer("Точка не найдена.")
        return

    if point.photo:
        logger.logger.info(point.photo.url)

        await callback.message.answer_photo(
            photo=URLInputFile(point.photo.url),
            caption=f"📍 {point.name}"
        )
    else:
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

    if point.audio_file:
        await callback.message.answer_audio(
            audio=URLInputFile(point.audio_file.url),
            caption=f"🎵 {point.name}"
        )

    if point.video_file and point.video_file.name:
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
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_pt:{short_point_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_pt:{short_point_id}")
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

    short_route_id = callback.data.split(":")[1]
    try:
        route = await Route.objects.aget(id=uuid.UUID(short_route_id))
    except Route.DoesNotExist:
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
            short_point_id = str(point_id)[:8]
            await handle_view_point(CallbackQuery(message=callback.message, data=f"view_pt:{short_point_id}"))
        elif route_id:
            short_route_id = str(route_id)[:8]
            await handle_view_route(CallbackQuery(message=callback.message, data=f"view_route:{short_route_id}"))
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
    await state.update_data(point_id=str(point.id))
    await callback.message.answer(
        "Отправьте новое аудио для точки.\nНажмите на скрепку и выберите 'Аудио'."
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
    await state.update_data(point_id=str(point.id))
    await callback.message.answer(
        "Отправьте новое видео для точки (или отправьте /cancel для отмены)."
    )
