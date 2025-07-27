import uuid
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.input_file import URLInputFile
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from core.models import User, Route, RoutePoint, Point
from django.core.files.base import ContentFile
import logging

from bot.base_handlers import BaseHandler
from bot.states import RouteStates

class RouteHandler(BaseHandler):
    """Обработчик для работы с маршрутами"""
    
    def __init__(self):
        super().__init__()
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрация всех обработчиков маршрутов"""
        
        # Основные обработчики меню
        self.router.message.register(self.handle_routes_menu, F.text == "🗺 Маршруты")
        self.router.callback_query.register(self.handle_list_routes_callback, F.data == "list_routes")
        self.router.callback_query.register(self.handle_back_to_routes_menu, F.data == "back_to_routes_menu")
        
        # Создание маршрутов
        self.router.callback_query.register(self.handle_create_route, F.data == "create_route")
        self.router.message.register(self.handle_route_name, RouteStates.waiting_for_route_name)
        self.router.message.register(self.handle_route_description, RouteStates.waiting_for_route_description)
        
        # Просмотр и редактирование маршрутов
        self.router.callback_query.register(self.handle_view_route, F.data.startswith("view_route:"))
        self.router.callback_query.register(self.handle_edit_route, F.data.startswith("edit_rt:"))
        self.router.callback_query.register(self.handle_delete_route, F.data.startswith("del_rt:"))
        
        # Редактирование полей маршрута
        self.router.callback_query.register(self.handle_edit_route_name, F.data == "edit_route_name")
        self.router.callback_query.register(self.handle_edit_route_description, F.data == "edit_route_description")
        self.router.callback_query.register(self.handle_edit_route_photo, F.data == "edit_route_photo")
        
        # Работа с точками в маршруте
        self.router.callback_query.register(self.handle_add_point_to_route, F.data.startswith("add_pt:"))
        self.router.callback_query.register(self.handle_select_point_for_route, F.data.startswith("sel_pt:"))
        self.router.callback_query.register(self.handle_remove_point_from_route, F.data.startswith("remove_point_from_route:"))
        self.router.callback_query.register(self.handle_remove_point_from_route_confirm, F.data.startswith("rm_pt:"))
        
        # Фото маршрута
        self.router.callback_query.register(self.handle_add_route_photo, F.data.startswith("add_route_photo:"))
        self.router.callback_query.register(self.handle_replace_route_photo, F.data == "replace_route_photo")
        self.router.callback_query.register(self.handle_delete_route_photo, F.data == "delete_route_photo")
        self.router.message.register(self.handle_route_photo_save, RouteStates.editing_route_photo, F.photo)
    
    async def handle_routes_menu(self, message: Message):
        """Обработка нажатия на кнопку 'Маршруты'"""
        if not await self.check_admin(message.from_user.id):
            return

        await message.answer(
            "Управление маршрутами:",
            reply_markup=self.get_routes_management_keyboard()
        )
    
    async def handle_list_routes_callback(self, callback: CallbackQuery):
        """Показать список маршрутов"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_back_to_routes_menu(self, callback: CallbackQuery):
        """Возврат в меню маршрутов"""
        await callback.message.answer(
            "Управление маршрутами:",
            reply_markup=self.get_routes_management_keyboard()
        )
    
    async def handle_create_route(self, callback: CallbackQuery, state: FSMContext):
        """Начало создания нового маршрута"""
        if not await self.check_admin(callback.from_user.id):
            return

        await state.set_state(RouteStates.waiting_for_route_name)
        await callback.message.answer("Введите название маршрута:")
    
    async def handle_route_name(self, message: Message, state: FSMContext):
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
                await self.handle_view_route(callback)
            except Route.DoesNotExist:
                await message.answer("Маршрут не найден.")
                await state.clear()
        else:
            await state.update_data(route_name=message.text)
            await state.set_state(RouteStates.waiting_for_route_description)
            await message.answer("Введите описание маршрута:")
    
    async def handle_route_description(self, message: Message, state: FSMContext):
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
                await self.handle_view_route(callback)
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
    
    async def handle_view_route(self, callback: CallbackQuery):
        """Просмотр конкретного маршрута"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_edit_route(self, callback: CallbackQuery, state: FSMContext):
        """Начало редактирования маршрута"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_edit_route_name(self, callback: CallbackQuery, state: FSMContext):
        """Редактирование названия маршрута"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_edit_route_description(self, callback: CallbackQuery, state: FSMContext):
        """Редактирование описания маршрута"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_edit_route_photo(self, callback: CallbackQuery, state: FSMContext):
        """Редактирование фото маршрута"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_delete_route(self, callback: CallbackQuery):
        """Удаление маршрута"""
        if not await self.check_admin(callback.from_user.id):
            return

        short_route_id = callback.data.split(":")[1]
        try:
            route = await Route.objects.aget(id=uuid.UUID(short_route_id))
        except Route.DoesNotExist:
            await callback.message.answer("Маршрут не найден.")
            return

        await route.adelete()
        await callback.message.answer("Маршрут успешно удален.")
        await self.handle_list_routes_callback(callback)
    
    # Работа с точками в маршруте
    async def handle_add_point_to_route(self, callback: CallbackQuery, state: FSMContext):
        """Добавление точки в маршрут"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_select_point_for_route(self, callback: CallbackQuery):
        """Обработка выбора точки для добавления в маршрут"""
        if not await self.check_admin(callback.from_user.id):
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
        await self.handle_view_route(callback)
    
    async def handle_remove_point_from_route(self, callback: CallbackQuery):
        """Удаление точки из маршрута"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_remove_point_from_route_confirm(self, callback: CallbackQuery):
        """Подтверждение удаления точки из маршрута"""
        if not await self.check_admin(callback.from_user.id):
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
    
    # Фото маршрута
    async def handle_add_route_photo(self, callback: CallbackQuery, state: FSMContext):
        """Добавление фото к новому маршруту"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_replace_route_photo(self, callback: CallbackQuery, state: FSMContext):
        """Замена фото маршрута"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_delete_route_photo(self, callback: CallbackQuery, state: FSMContext):
        """Удаление фото маршрута"""
        if not await self.check_admin(callback.from_user.id):
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
            await self.handle_view_route(new_callback)
            
        except Route.DoesNotExist:
            await callback.message.answer("Маршрут не найден.")
            await state.clear()
    
    async def handle_route_photo_save(self, message: Message, state: FSMContext, bot):
        """Сохранение фото маршрута"""
        if not await self.check_admin(message.from_user.id):
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
        await self.handle_view_route(new_callback) 