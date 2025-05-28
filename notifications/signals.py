from django.db.models.signals import post_save
from django.dispatch import receiver
from bookings.models import Booking
import logging
import threading

logger = logging.getLogger(__name__)


def send_notification_background(barber_id, booking_data):
    """
    Фоновая отправка уведомления (в отдельном потоке)
    """
    try:
        from notifications.bot import send_booking_notification
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

            # Отправляем уведомление в фоновом потоке (чтобы не блокировать основной поток)
            thread = threading.Thread(
                target=send_notification_background,
                args=(barber_id, booking_data)
            )
            thread.daemon = True
            thread.start()

            logger.info(f"Задача уведомления для бронирования {instance.id} запущена")

        except Exception as e:
            logger.error(f"Ошибка при создании уведомления для бронирования {instance.id}: {str(e)}")


# 3. ОБНОВИТЬ notifications/views.py (метод _send_test_notification):

def _send_test_notification(self, user, username):
    """Отправляет тестовое уведомление для проверки подключения."""
    try:
        from notifications.models import Notification
        from notifications.bot import send_test_message

        # Создаем системное уведомление
        notification = Notification.objects.create(
            recipient=user,
            type='system',
            title='Подключение уведомлений',
            content=f'Вы успешно подключили уведомления через Telegram! Теперь вы будете получать информацию о новых бронированиях.',
            status='pending'
        )

        # Отправляем уведомление через Telegram (синхронно)
        success = send_test_message(
            username=username,
            title='Подключение успешно!',
            message='Вы успешно подключили уведомления BarberHub! Теперь вы будете получать уведомления о новых бронированиях ваших услуг.'
        )

        # Обновляем статус уведомления
        if success:
            notification.status = 'sent'
            from django.utils import timezone
            notification.sent_at = timezone.now()
        else:
            notification.status = 'failed'

        notification.save()

    except Exception as e:
        logger.error(f"Error sending test notification to {username}: {str(e)}")
