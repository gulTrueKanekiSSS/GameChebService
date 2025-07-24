import uuid
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
        short_point_id = str(point.id)[:8]
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
        short_point_id = str(point.id)[:8]
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
        route = await Route.objects.aget(id__startswith=short_route_id)
        point = await Point.objects.aget(id__startswith=short_point_id)
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
                InlineKeyboardButton(text="📸 Фото", callback_data="edit_route_photo")
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
