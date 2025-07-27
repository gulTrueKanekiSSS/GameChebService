import uuid
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.input_file import URLInputFile
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from core.models import User, Point, PointPhoto, PointAudio, PointVideo
from django.core.files.base import ContentFile
import logging

from bot.base_handlers import BaseHandler
from bot.states import RouteStates

class PointHandler(BaseHandler):
    """Обработчик для работы с точками"""
    
    def __init__(self):
        super().__init__()
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрация всех обработчиков точек"""
        
        # Основные обработчики меню
        self.router.message.register(self.handle_points_menu, F.text == "📍 Точки")
        self.router.callback_query.register(self.handle_list_points_callback, F.data == "list_points")
        self.router.callback_query.register(self.handle_back_to_points_menu, F.data == "back_to_points_menu")
        self.router.callback_query.register(self.handle_back_to_main, F.data == "back_to_main")
        
        # Создание точек
        self.router.callback_query.register(self.handle_create_point, F.data == "create_point")
        self.router.message.register(self.handle_point_name, RouteStates.waiting_for_point_name)
        self.router.message.register(self.handle_point_description, RouteStates.waiting_for_point_description)
        self.router.message.register(self.handle_point_location, RouteStates.waiting_for_point_location, F.location)
        
        # Просмотр и редактирование точек
        self.router.callback_query.register(self.handle_view_point, F.data.startswith("view_pt:"))
        self.router.callback_query.register(self.handle_edit_point, F.data.startswith("edit_pt:"))
        self.router.callback_query.register(self.handle_delete_point, F.data.startswith("del_pt:"))
        
        # Редактирование полей точки
        self.router.callback_query.register(self.handle_edit_point_name, F.data == "edit_point_name")
        self.router.callback_query.register(self.handle_edit_point_description, F.data == "edit_point_description")
        self.router.callback_query.register(self.handle_edit_point_location, F.data == "edit_point_location")
        self.router.callback_query.register(self.handle_edit_point_text, F.data.startswith("edit_pt_text:"))
        
        # Обработка редактирования полей
        self.router.message.register(self.handle_point_name_edit, RouteStates.editing_point_name)
        self.router.message.register(self.handle_point_description_edit, RouteStates.editing_point_description)
        self.router.message.register(self.handle_point_location_edit, RouteStates.editing_point_location, F.location)
        self.router.message.register(self.handle_point_text_edit, RouteStates.waiting_for_point_text)
        
        # Медиа файлы
        self.router.callback_query.register(self.handle_edit_point_photo, F.data.startswith("edit_pt_photo:"))
        self.router.callback_query.register(self.handle_edit_point_audio, F.data.startswith("edit_pt_audio:"))
        self.router.callback_query.register(self.handle_edit_point_video, F.data.startswith("edit_pt_video:"))
        self.router.callback_query.register(self.handle_add_point_photo, F.data.startswith("add_pt_photo:"))
        self.router.callback_query.register(self.handle_add_point_audio, F.data.startswith("add_pt_audio:"))
        self.router.callback_query.register(self.handle_add_point_video, F.data.startswith("add_pt_video:"))
        
        # Обработка медиа файлов
        self.router.message.register(self.handle_point_photo_edit, RouteStates.waiting_for_point_photo, F.photo)
        self.router.message.register(self.handle_point_audio_edit, RouteStates.waiting_for_point_audio, F.audio)
        self.router.message.register(self.handle_point_video_edit, RouteStates.waiting_for_point_video, F.video)
        
        # Специальные обработчики фото
        self.router.callback_query.register(self.handle_edit_old_photo, F.data.startswith("edit_photo_old:"))
        self.router.callback_query.register(self.handle_edit_new_photo, F.data.startswith("edit_photo_new:"))
        
        # Отмена редактирования
        self.router.callback_query.register(self.handle_cancel_edit, F.data == "cancel_edit")
    
    async def handle_points_menu(self, message: Message):
        """Обработка нажатия на кнопку 'Точки'"""
        if not await self.check_admin(message.from_user.id):
            return

        await message.answer(
            "Управление точками:",
            reply_markup=self.get_points_management_keyboard()
        )
    
    async def handle_list_points_callback(self, callback: CallbackQuery):
        """Показать список точек"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_back_to_points_menu(self, callback: CallbackQuery):
        """Возврат в меню точек"""
        await callback.message.answer(
            "Управление точками:",
            reply_markup=self.get_points_management_keyboard()
        )
    
    async def handle_back_to_main(self, callback: CallbackQuery):
        """Возврат в главное меню"""
        await callback.message.answer(
            "Главное меню:",
            reply_markup=self.get_admin_keyboard()
        )
    
    async def handle_create_point(self, callback: CallbackQuery, state: FSMContext):
        """Начало создания новой точки"""
        if not await self.check_admin(callback.from_user.id):
            return

        await state.set_state(RouteStates.waiting_for_point_name)
        await callback.message.answer("Введите название точки:")
    
    async def handle_point_name(self, message: Message, state: FSMContext):
        """Обработка названия точки"""
        await state.update_data(name=message.text)
        await state.set_state(RouteStates.waiting_for_point_description)
        await message.answer("Введите описание точки:")
    
    async def handle_point_description(self, message: Message, state: FSMContext):
        """Обработка описания точки"""
        await state.update_data(description=message.text)
        await state.set_state(RouteStates.waiting_for_point_location)
        await message.answer(
            "Отправьте локацию точки.\n"
            "Нажмите на кнопку 📎 и выберите 'Локация'"
        )
    
    async def handle_point_location(self, message: Message, state: FSMContext):
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
    
    async def handle_view_point(self, callback: CallbackQuery):
        """Просмотр конкретной точки (теперь все медиа)"""
        if not await self.check_admin(callback.from_user.id):
            return

        short_point_id = callback.data.split(":")[1]
        point, error = await self.find_point_by_short_id(short_point_id)
        
        if error:
            await callback.message.answer(error)
            return

        photos = await sync_to_async(list)(point.photos.all())
        self.logger.info(f"DEBUG: Point {point.name} has {len(photos)} photos in PointPhoto table")
        if point.photo:
            self.logger.info(f"DEBUG: Point {point.name} also has old photo field: {point.photo.url}")
        
        if photos:
            from aiogram.types import InputMediaPhoto
            media_group = []
            for i, photo in enumerate(photos):
                self.logger.info(f"DEBUG: Adding photo {i+1}: {photo.image.url}")
                media_group.append(InputMediaPhoto(
                    media=URLInputFile(photo.image.url),
                    caption=f"📍 {point.name}" if i == 0 else None
                ))
            self.logger.info(f"DEBUG: Sending media group with {len(media_group)} photos")
            try:
                await callback.message.answer_media_group(media_group)
                self.logger.info(f"DEBUG: Media group sent successfully")
            except Exception as e:
                self.logger.info(f"DEBUG: Error sending media group: {e}")
                for i, photo in enumerate(photos):
                    try:
                        await callback.message.answer_photo(
                            photo=URLInputFile(photo.image.url),
                            caption=f"📍 {point.name} (фото {i+1}/{len(photos)})"
                        )
                    except Exception as photo_error:
                        self.logger.info(f"DEBUG: Error sending individual photo {i+1}: {photo_error}")
        elif point.photo:
            self.logger.info(f"DEBUG: Sending old photo field")
            await callback.message.answer_photo(
                photo=URLInputFile(point.photo.url),
                caption=f"📍 {point.name}"
            )
        else:
            self.logger.info(f"DEBUG: No photos found, sending text message")
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
                self.logger.error(f"Ошибка при отправке видео: {e}")
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
                self.logger.error(f"Ошибка при отправке видео: {e}")
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
    
    async def handle_edit_point(self, callback: CallbackQuery, state: FSMContext):
        """Начало редактирования точки"""
        if not await self.check_admin(callback.from_user.id):
            return

        short_point_id = callback.data.split(":")[1]
        point, error = await self.find_point_by_short_id(short_point_id)
        
        if error:
            await callback.message.answer(error)
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
    
    async def handle_delete_point(self, callback: CallbackQuery):
        """Удаление точки"""
        if not await self.check_admin(callback.from_user.id):
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
        await self.handle_list_points_callback(callback)
    
    # Остальные методы для редактирования точек...
    async def handle_edit_point_name(self, callback: CallbackQuery, state: FSMContext):
        """Редактирование названия точки"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_edit_point_description(self, callback: CallbackQuery, state: FSMContext):
        """Редактирование описания точки"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_edit_point_location(self, callback: CallbackQuery, state: FSMContext):
        """Редактирование локации точки"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_edit_point_text(self, callback: CallbackQuery, state: FSMContext):
        """Редактирование текста точки"""
        if not await self.check_admin(callback.from_user.id):
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
    
    # Обработчики сохранения изменений
    async def handle_point_name_edit(self, message: Message, state: FSMContext):
        """Сохранение нового названия точки"""
        if not await self.check_admin(message.from_user.id):
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
        await self.handle_view_point(new_callback)
    
    async def handle_point_description_edit(self, message: Message, state: FSMContext):
        """Сохранение нового описания точки"""
        if not await self.check_admin(message.from_user.id):
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
        await self.handle_view_point(new_callback)
    
    async def handle_point_location_edit(self, message: Message, state: FSMContext):
        """Сохранение новой локации точки"""
        if not await self.check_admin(message.from_user.id):
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
        await self.handle_view_point(new_callback)
    
    async def handle_point_text_edit(self, message: Message, state: FSMContext):
        """Сохранение нового текста точки"""
        if not await self.check_admin(message.from_user.id):
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
            data=f"view_pt:{str(point.id)[:8]}"
        )
        await self.handle_view_point(new_callback)
    
    # Медиа обработчики
    async def handle_edit_point_photo(self, callback: CallbackQuery, state: FSMContext):
        """Начало редактирования фото точки"""
        if not await self.check_admin(callback.from_user.id):
            return

        short_point_id = callback.data.split(":")[1]
        point, error = await self.find_point_by_short_id(short_point_id)
        
        if error:
            await callback.message.answer(error)
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
    
    async def handle_point_photo_edit(self, message: Message, state: FSMContext, bot):
        """Сохранение/добавление фото точки"""
        if not await self.check_admin(message.from_user.id):
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
                point, error = await self.find_point_by_short_id(point_id)
                if error:
                    await message.answer(error)
                    await state.clear()
                    return
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
        await self.handle_view_point(new_callback)
    
    async def handle_point_audio_edit(self, message: Message, state: FSMContext, bot):
        """Сохранение нового аудио точки (теперь можно несколько)"""
        if not await self.check_admin(message.from_user.id):
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
        await self.handle_view_point(new_callback)
    
    async def handle_point_video_edit(self, message: Message, state: FSMContext):
        """Сохранение нового видео точки (теперь можно несколько)"""
        if not await self.check_admin(message.from_user.id):
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
        await self.handle_view_point(CallbackQuery(
            id=str(message.message_id),
            from_user=message.from_user,
            chat_instance=str(message.chat.id),
            message=message,
            data=f"view_pt:{short_point_id}"
        ))
    
    # Дополнительные обработчики медиа
    async def handle_edit_point_audio(self, callback: CallbackQuery, state: FSMContext):
        """Начало редактирования аудио точки"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_edit_point_video(self, callback: CallbackQuery, state: FSMContext):
        """Начало редактирования видео точки"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_add_point_photo(self, callback: CallbackQuery, state: FSMContext):
        """Добавление нового фото к точке"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_add_point_audio(self, callback: CallbackQuery, state: FSMContext):
        """Добавление нового аудио к точке"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_add_point_video(self, callback: CallbackQuery, state: FSMContext):
        """Добавление нового видео к точке"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_edit_old_photo(self, callback: CallbackQuery, state: FSMContext):
        """Редактирование старого фото точки"""
        if not await self.check_admin(callback.from_user.id):
            return

        short_point_id = callback.data.split(":")[1]
        await state.set_state(RouteStates.waiting_for_point_photo)
        await state.update_data(point_id=short_point_id, mode="edit", photo_type="old")
        await callback.message.answer(
            "Отправьте новое фото для замены основного фото.\n"
            "Нажмите на кнопку 📎 и выберите 'Фото'"
        )
    
    async def handle_edit_new_photo(self, callback: CallbackQuery, state: FSMContext):
        """Редактирование нового фото точки"""
        if not await self.check_admin(callback.from_user.id):
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
    
    async def handle_cancel_edit(self, callback: CallbackQuery, state: FSMContext):
        """Отмена редактирования"""
        if not await self.check_admin(callback.from_user.id):
            return

        try:
            data = await state.get_data()
            point_id = data.get('point_id')
            route_id = data.get('route_id')

            await state.clear()

            if point_id:
                short_point_id = str(point_id)[:8]
                await self.handle_view_point(CallbackQuery(
                    id=callback.id,
                    from_user=callback.from_user,
                    chat_instance=callback.chat_instance,
                    message=callback.message,
                    data=f"view_pt:{short_point_id}"
                ))
            elif route_id:
                short_route_id = str(route_id)[:8]
                # Здесь нужно будет добавить обработчик для маршрутов
                await callback.message.answer("Возврат к маршруту...")
        except Exception as e:
            await callback.message.answer("Произошла ошибка при отмене редактирования.")
            await state.clear() 