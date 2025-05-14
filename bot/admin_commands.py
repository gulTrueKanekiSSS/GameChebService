from aiogram import types, Router, F
from aiogram.filters import Command, CommandObject
from asgiref.sync import sync_to_async
from core.models import UserQuestProgress, PromoCode, User
from django.conf import settings

router = Router()

async def check_admin_group(message: types.Message) -> bool:
    """Проверяет, что сообщение пришло из группы администраторов"""
    if not message.chat.id == int(settings.ADMIN_GROUP_ID):
        await message.reply("Эта команда доступна только в группе администраторов")
        return False
    return True

async def handle_approve(message: types.Message, command: CommandObject):
    # Проверяем, что команда пришла из группы администраторов
    if not await check_admin_group(message):
        return

    if not command.args:
        await message.reply("Ошибка: укажите ID прогресса\nПример: /approve 12345")
        return

    progress_id = command.args

    # Получаем прогресс
    get_progress = sync_to_async(lambda: UserQuestProgress.objects.select_related('user', 'quest').filter(id=progress_id).first())
    progress = await get_progress()

    if not progress:
        await message.reply(f"Ошибка: прогресс с ID {progress_id} не найден")
        return

    if progress.status != UserQuestProgress.Status.PENDING:
        await message.reply("Этот квест уже проверен")
        return

    # Находим свободный промокод
    get_promo = sync_to_async(lambda: PromoCode.objects.filter(
        quest=progress.quest,
        is_used=False
    ).first())
    promo_code = await get_promo()

    if not promo_code:
        await message.reply("Ошибка: нет доступных промокодов для этого квеста")
        return

    # Обновляем статус и привязываем промокод
    @sync_to_async
    def update_progress():
        progress.status = UserQuestProgress.Status.APPROVED
        progress.promo_code = promo_code
        progress.save()
        promo_code.is_used = True
        promo_code.save()

    await update_progress()

    # Отправляем уведомление пользователю
    await message.bot.send_message(
        progress.user.telegram_id,
        f"🎉 Поздравляем! Ваше выполнение квеста \"{progress.quest.name}\" подтверждено!\n\n"
        f"Ваш промокод: {promo_code.code}"
    )

    await message.reply("✅ Квест подтвержден, промокод отправлен пользователю")

async def handle_reject(message: types.Message, command: CommandObject):
    # Проверяем, что команда пришла из группы администраторов
    if not await check_admin_group(message):
        return

    if not command.args:
        await message.reply("Ошибка: укажите ID прогресса и причину\nПример: /reject 12345 фото не соответствует заданию")
        return

    args = command.args.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Ошибка: укажите причину отклонения")
        return

    progress_id, reason = args

    # Получаем прогресс
    get_progress = sync_to_async(lambda: UserQuestProgress.objects.select_related('user', 'quest').filter(id=progress_id).first())
    progress = await get_progress()

    if not progress:
        await message.reply(f"Ошибка: прогресс с ID {progress_id} не найден")
        return

    if progress.status != UserQuestProgress.Status.PENDING:
        await message.reply("Этот квест уже проверен")
        return

    # Обновляем статус и добавляем комментарий
    @sync_to_async
    def update_progress():
        progress.status = UserQuestProgress.Status.REJECTED
        progress.admin_comment = reason
        progress.save()

    await update_progress()

    # Отправляем уведомление пользователю
    await message.bot.send_message(
        progress.user.telegram_id,
        f"❌ К сожалению, ваше выполнение квеста \"{progress.quest.name}\" отклонено.\n\n"
        f"Причина: {reason}\n\n"
        "Вы можете попробовать выполнить квест ещё раз."
    )

    await message.reply("❌ Квест отклонен, уведомление отправлено пользователю")

@router.message(Command("make_admin"))
async def cmd_make_admin(message: types.Message):
    """Назначение пользователя администратором"""
    # Проверяем, является ли отправитель уже администратором
    sender = await User.objects.aget(telegram_id=message.from_user.id)
    if not sender.is_admin:
        await message.answer("У вас нет прав для назначения администраторов.")
        return

    # Проверяем, есть ли ID пользователя в сообщении
    try:
        user_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer(
            "Использование: /make_admin <ID пользователя>\n"
            "ID пользователя можно получить, переслав его сообщение боту @getidsbot"
        )
        return

    # Находим пользователя и делаем его администратором
    try:
        user = await User.objects.aget(telegram_id=user_id)
        user.is_admin = True
        await user.asave()
        await message.answer(f"✅ Пользователь {user.name} теперь администратор!")
    except User.DoesNotExist:
        await message.answer("❌ Пользователь не найден.")

@router.message(Command("remove_admin"))
async def cmd_remove_admin(message: types.Message):
    """Снятие прав администратора"""
    # Проверяем, является ли отправитель администратором
    sender = await User.objects.aget(telegram_id=message.from_user.id)
    if not sender.is_admin:
        await message.answer("У вас нет прав для снятия прав администратора.")
        return

    # Проверяем, есть ли ID пользователя в сообщении
    try:
        user_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer(
            "Использование: /remove_admin <ID пользователя>\n"
            "ID пользователя можно получить, переслав его сообщение боту @getidsbot"
        )
        return

    # Находим пользователя и снимаем права администратора
    try:
        user = await User.objects.aget(telegram_id=user_id)
        user.is_admin = False
        await user.asave()
        await message.answer(f"✅ Пользователь {user.name} больше не администратор.")
    except User.DoesNotExist:
        await message.answer("❌ Пользователь не найден.")

@router.message(Command("list_admins"))
async def cmd_list_admins(message: types.Message):
    """Показать список всех администраторов"""
    # Проверяем, является ли отправитель администратором
    sender = await User.objects.aget(telegram_id=message.from_user.id)
    if not sender.is_admin:
        await message.answer("У вас нет прав для просмотра списка администраторов.")
        return

    # Получаем список всех администраторов
    admins = await User.objects.filter(is_admin=True).all()
    if not admins:
        await message.answer("Список администраторов пуст.")
        return

    text = "👥 Список администраторов:\n\n"
    for admin in admins:
        text += f"• {admin.name} (ID: {admin.telegram_id})\n"
        text += f"  Телефон: {admin.phone_number or 'Не указан'}\n"
        text += f"  Создан: {admin.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    await message.answer(text) 