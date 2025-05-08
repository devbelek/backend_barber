from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.conf import settings
from bookings.models import Booking
import asyncio
import logging
from notifications.bot import send_booking_notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Booking)
def send_booking_notification_signal(sender, instance, created, **kwargs):
    """
    Обрабатывает сигнал сохранения бронирования и отправляет уведомление барберу.
    """
    if created:  # Только для новых бронирований
        try:
            # Подготавливаем данные для уведомления
            booking_data = {
                'client_name': f"{instance.client.first_name} {instance.client.last_name}".strip() or instance.client.username,
                'service_title': instance.service.title,
                'date': instance.date.strftime('%d.%m.%Y'),
                'time': instance.time.strftime('%H:%M'),
                'notes': instance.notes or ''
            }

            # Получаем ID барбера
            barber_id = instance.service.barber.id

            # Отправляем уведомление асинхронно
            transaction.on_commit(lambda: _send_notification_async(barber_id, booking_data))

            # Создаем запись об уведомлении
            from notifications.models import Notification
            Notification.objects.create(
                recipient=instance.service.barber,
                type='booking_new',
                title='Новое бронирование',
                content=f"Новое бронирование на услугу '{instance.service.title}' от клиента {booking_data['client_name']}",
                related_object_id=instance.id,
                related_object_type='booking',
                status='pending'
            )

            logger.info(f"Notification for booking {instance.id} created successfully")

        except Exception as e:
            logger.error(f"Error creating notification for booking {instance.id}: {str(e)}")


def _send_notification_async(barber_id, booking_data):
    """
    Вспомогательная функция для асинхронной отправки уведомления.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        coroutine = send_booking_notification(barber_id, booking_data)
        loop.run_until_complete(coroutine)
        loop.close()
    except Exception as e:
        logger.error(f"Error sending async notification: {str(e)}")