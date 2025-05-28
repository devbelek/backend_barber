import logging
import requests
import os
from django.conf import settings
from typing import Dict, Optional

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    try:
        TOKEN = settings.TELEGRAM_BOT_TOKEN
    except AttributeError:
        logger.error("TELEGRAM_BOT_TOKEN не найден!")
        TOKEN = None


def send_telegram_message(chat_id: str, message: str) -> bool:
    """
    Отправка сообщения через Telegram Bot API (синхронно)
    """
    if not TOKEN:
        logger.error("Telegram bot токен не настроен")
        return False

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }

        response = requests.post(url, data=data, timeout=10)

        if response.status_code == 200:
            logger.info(f"Сообщение успешно отправлено в чат {chat_id}")
            return True
        else:
            logger.error(f"Ошибка отправки сообщения: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Исключение при отправке сообщения: {str(e)}")
        return False


def send_booking_notification(barber_id: int, booking_data: dict) -> bool:
    """
    Отправка уведомления о бронировании (синхронно)
    """
    try:
        from notifications.models import TelegramUser

        # Находим Telegram пользователя
        telegram_user = TelegramUser.objects.get(barber_id=barber_id)

        # Формируем сообщение
        client_name = booking_data.get('client_name', 'Клиент')
        client_phone = booking_data.get('client_phone', '')
        service_title = booking_data.get('service_title', 'Услуга')
        date = booking_data.get('date', 'Дата не указана')
        time = booking_data.get('time', 'Время не указано')
        notes = booking_data.get('notes', '')

        message = (
            f"🔔 *Новое бронирование!*\n\n"
            f"👤 Клиент: {client_name}\n"
        )

        if client_phone:
            message += f"📱 Телефон: {client_phone}\n"

        message += (
            f"✂️ Услуга: {service_title}\n"
            f"📅 Дата: {date}\n"
            f"🕒 Время: {time}\n"
        )

        if notes:
            message += f"\n📝 Примечания: {notes}\n"

        message += f"\n✅ Для управления бронированиями перейдите в личный кабинет."

        # Определяем chat_id
        chat_id = telegram_user.chat_id or f"@{telegram_user.username}"

        # Отправляем сообщение
        success = send_telegram_message(chat_id, message)

        if success:
            # Обновляем время последнего уведомления
            from django.utils import timezone
            telegram_user.last_notification = timezone.now()
            telegram_user.save()

        return success

    except TelegramUser.DoesNotExist:
        logger.warning(f"Telegram username не найден для барбера ID {barber_id}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления барберу {barber_id}: {str(e)}")
        return False


def send_test_message(username: str, title: str, message: str) -> bool:
    """
    Отправка тестового сообщения
    """
    try:
        from notifications.models import TelegramUser

        telegram_user = TelegramUser.objects.get(username=username)
        formatted_message = f"*{title}*\n\n{message}"
        chat_id = telegram_user.chat_id or f"@{username}"

        success = send_telegram_message(chat_id, formatted_message)

        if success:
            from django.utils import timezone
            telegram_user.last_notification = timezone.now()
            telegram_user.save()

        return success

    except TelegramUser.DoesNotExist:
        logger.error(f"TelegramUser с username {username} не найден")
        return False
    except Exception as e:
        logger.error(f"Ошибка отправки тестового сообщения: {str(e)}")
        return False