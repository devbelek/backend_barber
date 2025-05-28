import logging
import os
from django.core.management.base import BaseCommand
from notifications.bot import get_bot_info, TOKEN, send_message_sync
from notifications.models import TelegramUser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Управление Telegram ботом'

    def add_arguments(self, parser):
        parser.add_argument(
            '--info',
            action='store_true',
            help='Показать информацию о боте',
        )
        parser.add_argument(
            '--test-chat',
            type=str,
            help='Тест отправки сообщения в указанный чат (chat_id или @username)',
        )
        parser.add_argument(
            '--test-barbers',
            action='store_true',
            help='Тест отправки сообщений всем зарегистрированным барберам',
        )
        parser.add_argument(
            '--list-barbers',
            action='store_true',
            help='Показать всех зарегистрированных барберов',
        )

    def handle(self, *args, **options):
        if not TOKEN:
            self.stdout.write(
                self.style.ERROR('TELEGRAM_BOT_TOKEN не установлен!')
            )
            return

        if options['info']:
            info = get_bot_info()
            if info:
                self.stdout.write(
                    self.style.SUCCESS(f"Бот активен: @{info['result']['username']}")
                )
                self.stdout.write(f"Имя: {info['result']['first_name']}")
                self.stdout.write(f"ID: {info['result']['id']}")
            else:
                self.stdout.write(
                    self.style.ERROR('Не удалось получить информацию о боте')
                )

        if options['test_chat']:
            chat = options['test_chat']
            self.stdout.write(f"Отправляю тестовое сообщение в {chat}...")

            success = send_message_sync(
                chat,
                "🤖 Тестовое сообщение от TARAK бота!\n\nЕсли вы видите это сообщение, значит бот работает корректно."
            )

            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'Тестовое сообщение отправлено в {chat}!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Не удалось отправить сообщение в {chat}')
                )
                self.stdout.write(
                    self.style.WARNING('Убедитесь что:\n'
                                       '1. Пользователь начал диалог с ботом (/start)\n'
                                       '2. Username указан правильно (с @)\n'
                                       '3. Или используйте числовой chat_id')
                )

        if options['list_barbers']:
            barbers = TelegramUser.objects.all()
            if barbers:
                self.stdout.write(
                    self.style.SUCCESS(f"Зарегистрированные барберы ({barbers.count()}):")
                )
                for barber in barbers:
                    status = "✅ Активен" if barber.is_active else "❌ Неактивен"
                    self.stdout.write(
                        f"  @{barber.username} - {barber.barber.get_full_name()} ({status})"
                    )
            else:
                self.stdout.write(
                    self.style.WARNING('Нет зарегистрированных барберов')
                )

        if options['test_barbers']:
            barbers = TelegramUser.objects.filter(is_active=True)
            if not barbers:
                self.stdout.write(
                    self.style.WARNING('Нет активных барберов для тестирования')
                )
                return

            self.stdout.write(f"Отправляю тестовые сообщения {barbers.count()} барберам...")

            success_count = 0
            for barber in barbers:
                success = send_message_sync(
                    f"@{barber.username}",
                    f"🔔 Тест уведомлений TARAK\n\n"
                    f"Привет, {barber.barber.get_full_name()}!\n"
                    f"Это тестовое уведомление для проверки работы бота.\n\n"
                    f"Если вы получили это сообщение - все работает отлично! ✅"
                )

                if success:
                    success_count += 1
                    self.stdout.write(f"  ✅ @{barber.username}")
                else:
                    self.stdout.write(f"  ❌ @{barber.username}")

            self.stdout.write(
                self.style.SUCCESS(f"Успешно отправлено: {success_count}/{barbers.count()}")
            )