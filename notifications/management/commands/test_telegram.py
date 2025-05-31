# notifications/management/commands/test_telegram.py
from django.core.management.base import BaseCommand
from notifications.bot import test_bot_connection, send_test_message, send_booking_notification
from notifications.models import TelegramUser
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Тестирование Telegram бота'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Тестировать подключение к боту',
        )
        parser.add_argument(
            '--test-user',
            type=str,
            help='Отправить тестовое сообщение пользователю (username)',
        )
        parser.add_argument(
            '--test-booking',
            type=int,
            help='Тестировать уведомление о бронировании (barber_id)',
        )
        parser.add_argument(
            '--list-users',
            action='store_true',
            help='Показать всех зарегистрированных пользователей',
        )

    def handle(self, *args, **options):
        if options['test_connection']:
            self.stdout.write("Тестируем подключение к боту...")
            if test_bot_connection():
                self.stdout.write(
                    self.style.SUCCESS('✅ Бот подключен успешно!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Ошибка подключения к боту')
                )

        if options['list_users']:
            self.stdout.write("Зарегистрированные пользователи:")
            users = TelegramUser.objects.all()
            if users:
                for user in users:
                    self.stdout.write(
                        f"  - {user.barber.username} (@{user.username}) - "
                        f"chat_id: {user.chat_id or 'не установлен'}"
                    )
            else:
                self.stdout.write("  Нет зарегистрированных пользователей")

        if options['test_user']:
            username = options['test_user']
            self.stdout.write(f"Отправляем тестовое сообщение пользователю @{username}...")

            success = send_test_message(
                username,
                "Тест подключения",
                "Это тестовое сообщение от BarberHub бота! Если вы видите это сообщение, значит все работает корректно."
            )

            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Сообщение отправлено пользователю @{username}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Ошибка отправки сообщения пользователю @{username}')
                )

        if options['test_booking']:
            barber_id = options['test_booking']
            self.stdout.write(f"Тестируем уведомление о бронировании для барбера {barber_id}...")

            # Тестовые данные бронирования
            booking_data = {
                'client_name': 'Тестовый Клиент',
                'client_phone': '+996555123456',
                'service_title': 'Тестовая стрижка',
                'date': '01.12.2024',
                'time': '14:30',
                'notes': 'Это тестовое бронирование для проверки уведомлений'
            }

            success = send_booking_notification(barber_id, booking_data)

            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Уведомление отправлено барберу {barber_id}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Ошибка отправки уведомления барберу {barber_id}')
                )

        if not any([options['test_connection'], options['test_user'],
                    options['test_booking'], options['list_users']]):
            self.stdout.write("Используйте --help для просмотра доступных опций")