import asyncio
import logging
from typing import Dict, Optional
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import os
from django.conf import settings
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Используем токен из переменных окружения или константы
TOKEN = "7993091176:AAFcjI0NrUl-Sdz_XLAxbVjHzfzdhVAhdOw"

# Инициализация бота
bot = Bot(token=TOKEN)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при команде /start."""
    user = update.effective_user
    if not user:
        return

    await update.message.reply_text(
        f"👋 Привет, {user.first_name}! Я бот для уведомлений о бронированиях в BarberHub.\n\n"
        f"Ваш username в Telegram: @{user.username}\n\n"
        f"Укажите этот username в настройках вашего профиля барбера, чтобы получать уведомления о новых бронированиях."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет сообщение с помощью при команде /help."""
    help_text = (
        "🤖 *Бот для уведомлений BarberHub*\n\n"
        "Я отправляю уведомления о новых бронированиях на ваши услуги.\n\n"
        "*Доступные команды:*\n"
        "/start - Показать приветственное сообщение\n"
        "/help - Показать эту справку\n"
        "/status - Проверить статус подключения\n\n"
        "Если у вас возникли проблемы, обратитесь в поддержку через приложение."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверяет статус подключения пользователя."""
    user = update.effective_user
    if not user or not user.username:
        await update.message.reply_text(
            "⚠️ У вас не установлен username в Telegram. Пожалуйста, установите его в настройках Telegram.")
        return

    username = user.username.lower()

    # Проверяем в базе данных
    from notifications.models import TelegramUser
    try:
        telegram_user = TelegramUser.objects.get(username=username)
        barber_name = f"{telegram_user.barber.first_name} {telegram_user.barber.last_name}"

        # Обновляем chat_id, если он отсутствует
        if not telegram_user.chat_id:
            telegram_user.chat_id = update.effective_chat.id
            telegram_user.save()

        await update.message.reply_text(
            f"✅ Вы успешно подключены к системе уведомлений!\n\n"
            f"Ваш профиль: {barber_name}\n"
            f"Вы будете получать уведомления о новых бронированиях на ваши услуги."
        )
    except TelegramUser.DoesNotExist:
        await update.message.reply_text(
            f"⚠️ Ваш Telegram аккаунт (@{username}) не связан с аккаунтом барбера в системе.\n\n"
            f"Пожалуйста, добавьте свой username в настройках профиля на сайте или в приложении."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает все сообщения, которые не являются командами."""
    await update.message.reply_text(
        "Я бот для уведомлений и не могу отвечать на сообщения. "
        "Используйте /help для получения списка доступных команд."
    )


def setup_application():
    """Настраивает и возвращает приложение бота."""
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))

    # Обрабатываем сообщения, которые не являются командами
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return application


async def run_bot():
    """Запускает бота."""
    application = setup_application()
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # Ожидаем бесконечно, чтобы бот не завершился
    await asyncio.Event().wait()


async def send_booking_notification(barber_id: int, booking_data: dict) -> bool:
    """
    Отправляет уведомление о новом бронировании барберу.

    Args:
        barber_id (int): ID барбера в системе
        booking_data (dict): Данные о бронировании

    Returns:
        bool: True если уведомление успешно отправлено, иначе False
    """
    try:
        # Получаем username из базы данных
        from notifications.models import TelegramUser
        try:
            telegram_user = TelegramUser.objects.get(barber_id=barber_id)
            username = telegram_user.username
            chat_id = telegram_user.chat_id

            # Формируем сообщение
            client_name = booking_data.get('client_name', 'Клиент')
            service_title = booking_data.get('service_title', 'Услуга')
            date = booking_data.get('date', 'Дата не указана')
            time = booking_data.get('time', 'Время не указано')
            notes = booking_data.get('notes', '')

            message = (
                f"🔔 *Новое бронирование!*\n\n"
                f"👤 Клиент: {client_name}\n"
                f"✂️ Услуга: {service_title}\n"
                f"📅 Дата: {date}\n"
                f"🕒 Время: {time}\n"
            )

            if notes:
                message += f"\n📝 Примечания: {notes}\n"

            message += f"\nДля управления бронированиями перейдите в личный кабинет на сайте или в приложении."

            # Отправляем сообщение
            if chat_id:
                # Если есть chat_id, отправляем напрямую в чат
                await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            else:
                # Иначе отправляем через username
                await bot.send_message(chat_id=f"@{username}", text=message, parse_mode='Markdown')

            # Обновляем последнее уведомление
            telegram_user.last_notification = datetime.now()
            telegram_user.save()

            return True

        except TelegramUser.DoesNotExist:
            logger.warning(f"Telegram username not found for barber ID {barber_id}")
            return False

        except Exception as e:
            logger.error(f"Error sending notification to barber {barber_id}: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"Error in send_booking_notification: {str(e)}")
        return False


def run_telegram_bot():
    """Запускает бота в отдельном потоке."""
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.error(f"Error running telegram bot: {str(e)}")