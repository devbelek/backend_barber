# notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from bookings.models import Booking
from notifications.models import Notification
from notifications.bot import send_booking_notification
import logging
import threading

logger = logging.getLogger(__name__)


def send_notification_background(barber_id, booking_data):
    """
    Фоновая отправка уведомления (в отдельном потоке)
    """
    try:
        logger.info(f"Начинаем отправку уведомления барберу {barber_id}")
        success = send_booking_notification(barber_id, booking_data)

        if success:
            logger.info(f"Уведомление успешно отправлено барберу {barber_id}")
        else:
            logger.error(f"Не удалось отправить уведомление барберу {barber_id}")

    except Exception as e:
        logger.error(f"Ошибка в фоновой отправке уведомления: {str(e)}")


@receiver(post_save, sender=Booking)
def send_booking_notification_signal(sender, instance, created, **kwargs):
    """
    Обрабатывает сигнал сохранения бронирования и отправляет уведомление барберу
    """
    logger.info(f"Сигнал получен: created={created}, booking_id={instance.id}")

    if created:  # Только для новых бронирований
        try:
            # Подготавливаем данные для уведомления
            client_name = instance.client_name_contact or (
                f"{instance.client.first_name} {instance.client.last_name}".strip()
                if instance.client.first_name else instance.client.username
            )

            booking_data = {
                'client_name': client_name,
                'client_phone': instance.client_phone_contact or (
                    instance.client.profile.phone if hasattr(instance.client, 'profile') else ''
                ),
                'service_title': instance.service.title,
                'date': instance.date.strftime('%d.%m.%Y'),
                'time': instance.time.strftime('%H:%M'),
                'notes': instance.notes or ''
            }

            # Получаем ID барбера
            barber_id = instance.service.barber.id

            logger.info(f"Подготовлены данные для уведомления: barber_id={barber_id}, data={booking_data}")

            # Создаем запись об уведомлении
            notification = Notification.objects.create(
                recipient=instance.service.barber,
                type='booking_new',
                title='Новое бронирование',
                content=f"Новое бронирование на услугу '{instance.service.title}' от клиента {booking_data['client_name']}",
                related_object_id=instance.id,
                related_object_type='booking',
                status='pending'
            )

            logger.info(f"Создано уведомление в БД: {notification.id}")

            # Отправляем уведомление в фоновом потоке
            thread = threading.Thread(
                target=send_notification_background,
                args=(barber_id, booking_data)
            )
            thread.daemon = True
            thread.start()

            logger.info(f"Задача уведомления для бронирования {instance.id} запущена")

        except Exception as e:
            logger.error(f"Ошибка при создании уведомления для бронирования {instance.id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())