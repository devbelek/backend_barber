import logging
from typing import Dict, Optional
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
import os
from django.conf import settings
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ИСПРАВЛЕНО: Используем токен только из переменных окружения
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    logger.warning("TELEGRAM_BOT_TOKEN не найден в переменных окружения. Используем токен по умолчанию.")
    # В продакшн-системе здесь должна быть ошибка вместо использования дефолтного токена
    TOKEN = "7993091176:AAFcjI0NrUl-Sdz_XLAxbVjHzfzdhVAhdOw"

# Инициализация бота
bot = Bot(token=TOKEN)


def start(update: Update, context: CallbackContext) -> None:
    """Отправляет приветственное сообщение при команде /start."""
    user = update.effective_user
    if not user:
        return

    update.message.reply_text(
        f"👋 Привет, {user.first_name}! Я бот для уведомлений о бронированиях в BarberHub.\n\n"
        f"Ваш username в Telegram: @{user.username}\n\n"
        f"Укажите этот username в настройках вашего профиля барбера, чтобы получать уведомления о новых бронированиях."
    )


def help_command(update: Update, context: CallbackContext) -> None:
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
    update.message.reply_text(help_text, parse_mode='Markdown')


def status_command(update: Update, context: CallbackContext) -> None:
    """Проверяет статус подключения пользователя."""
    user = update.effective_user
    if not user or not user.username:
        update.message.reply_text(
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

        update.message.reply_text(
            f"✅ Вы успешно подключены к системе уведомлений!\n\n"
            f"Ваш профиль: {barber_name}\n"
            f"Вы будете получать уведомления о новых бронированиях на ваши услуги."
        )
    except TelegramUser.DoesNotExist:
        update.message.reply_text(
            f"⚠️ Ваш Telegram аккаунт (@{username}) не связан с аккаунтом барбера в системе.\n\n"
            f"Пожалуйста, добавьте свой username в настройках профиля на сайте или в приложении."
        )


def handle_message(update: Update, context: CallbackContext) -> None:
    """Обрабатывает все сообщения, которые не являются командами."""
    update.message.reply_text(
        "Я бот для уведомлений и не могу отвечать на сообщения. "
        "Используйте /help для получения списка доступных команд."
    )


def setup_bot():
    """Настраивает и возвращает updater бота."""
    updater = Updater(token=TOKEN)
    dispatcher = updater.dispatcher

    # Добавляем обработчики команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("status", status_command))

    # Обрабатываем сообщения, которые не являются командами
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    return updater


def run_bot():
    """Запускает бота."""
    updater = setup_bot()
    updater.start_polling()
    updater.idle()


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
                bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            else:
                # Иначе отправляем через username
                bot.send_message(chat_id=f"@{username}", text=message, parse_mode='Markdown')

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