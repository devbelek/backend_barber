import asyncio
import logging
from datetime import datetime
from django.utils import timezone
from celery import shared_task
from .models import Notification, TelegramUser
from .bot import bot

logger = logging.getLogger(__name__)


@shared_task
def send_telegram_notification(username, title, message, notification_id=None):
    """
    Отправляет уведомление через Telegram.

    Args:
        username (str): Имя пользователя Telegram
        title (str): Заголовок уведомления
        message (str): Текст сообщения
        notification_id (int, optional): ID уведомления в базе данных
    """
    try:
        # Форматируем сообщение для Telegram
        formatted_message = f"*{title}*\n\n{message}"

        # Выполняем асинхронную отправку сообщения
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(
            bot.send_message(
                chat_id=f"@{username}",
                text=formatted_message,
                parse_mode='Markdown'
            )
        )

        # Обновляем статус уведомления в базе данных, если указан ID
        if notification_id:
            notification = Notification.objects.get(id=notification_id)
            notification.status = 'sent'
            notification.sent_at = timezone.now()
            notification.save()

            # Также обновляем дату последнего уведомления для пользователя Telegram
            telegram_user = TelegramUser.objects.get(username=username)
            telegram_user.last_notification = timezone.now()
            telegram_user.save()

        logger.info(f"Telegram notification successfully sent to @{username}")
        return True

    except Exception as e:
        logger.error(f"Error sending Telegram notification to @{username}: {str(e)}")

        # Обновляем статус уведомления в базе данных, если указан ID
        if notification_id:
            try:
                notification = Notification.objects.get(id=notification_id)
                notification.status = 'failed'
                notification.save()
            except Exception as db_error:
                logger.error(f"Error updating notification status: {str(db_error)}")

        return False


@shared_task
def process_pending_notifications():
    """
    Находит и отправляет все ожидающие отправки уведомления.
    """
    pending_notifications = Notification.objects.filter(status='pending')

    for notification in pending_notifications:
        try:
            # Проверяем, есть ли у получателя зарегистрированный Telegram
            if hasattr(notification.recipient,
                       'telegram_account') and notification.recipient.telegram_account.is_active:
                telegram_user = notification.recipient.telegram_account

                # Отправляем уведомление
                send_telegram_notification.delay(
                    username=telegram_user.username,
                    title=notification.title,
                    message=notification.content,
                    notification_id=notification.id
                )
            else:
                # Если Telegram не подключен, просто помечаем как отправленное
                # (в реальном приложении можно отправить по другим каналам)
                notification.status = 'sent'
                notification.sent_at = timezone.now()
                notification.save()

        except Exception as e:
            logger.error(f"Error processing notification {notification.id}: {str(e)}")


@shared_task
def send_booking_reminders():
    """
    Отправляет напоминания о предстоящих бронированиях.
    """
    from bookings.models import Booking
    from datetime import date, timedelta

    # Находим бронирования на завтра
    tomorrow = date.today() + timedelta(days=1)
    bookings = Booking.objects.filter(date=tomorrow, status='confirmed')

    for booking in bookings:
        try:
            # Отправляем напоминание клиенту
            if hasattr(booking.client, 'telegram_account') and booking.client.telegram_account.is_active:
                # Создаем уведомление
                notification = Notification.objects.create(
                    recipient=booking.client,
                    type='booking_reminder',
                    title=f"Напоминание о бронировании",
                    content=f"Напоминаем, что завтра ({tomorrow.strftime('%d.%m.%Y')}) в {booking.time.strftime('%H:%M')} "
                            f"у вас запланирована услуга \"{booking.service.title}\".",
                    related_object_id=booking.id,
                    related_object_type='booking',
                    status='pending'
                )

                # Отправляем через Telegram
                send_telegram_notification.delay(
                    username=booking.client.telegram_account.username,
                    title="Напоминание о записи",
                    message=f"Завтра ({tomorrow.strftime('%d.%m.%Y')}) в {booking.time.strftime('%H:%M')} "
                            f"у вас запланирована услуга \"{booking.service.title}\".",
                    notification_id=notification.id
                )

            # Отправляем напоминание барберу
            if hasattr(booking.service.barber,
                       'telegram_account') and booking.service.barber.telegram_account.is_active:
                # Создаем уведомление
                notification = Notification.objects.create(
                    recipient=booking.service.barber,
                    type='booking_reminder',
                    title=f"Напоминание о бронировании",
                    content=f"Напоминаем, что завтра ({tomorrow.strftime('%d.%m.%Y')}) в {booking.time.strftime('%H:%M')} "
                            f"у вас запланирована услуга \"{booking.service.title}\" для клиента {booking.client.get_full_name() or booking.client.username}.",
                    related_object_id=booking.id,
                    related_object_type='booking',
                    status='pending'
                )

                # Отправляем через Telegram
                send_telegram_notification.delay(
                    username=booking.service.barber.telegram_account.username,
                    title="Напоминание о клиенте",
                    message=f"Завтра ({tomorrow.strftime('%d.%m.%Y')}) в {booking.time.strftime('%H:%M')} "
                            f"у вас запланирована услуга \"{booking.service.title}\" для клиента {booking.client.get_full_name() or booking.client.username}.",
                    notification_id=notification.id
                )

        except Exception as e:
            logger.error(f"Error sending reminder for booking {booking.id}: {str(e)}")