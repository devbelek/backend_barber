#!/usr/bin/env python
"""
Скрипт для проверки работы Telegram уведомлений
Запускать из корневой директории проекта: python test_telegram_notifications.py
"""

import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barberhub.settings')
django.setup()

from django.contrib.auth.models import User
from notifications.models import TelegramUser, Notification
from notifications.bot import send_telegram_message, send_test_message, send_booking_notification
from bookings.models import Booking
from services.models import Service
import datetime
from django.utils import timezone


def test_telegram_connection():
    """Проверка подключения к Telegram Bot API"""
    print("=" * 50)
    print("1. ПРОВЕРКА ПОДКЛЮЧЕНИЯ К TELEGRAM BOT API")
    print("=" * 50)

    from django.conf import settings
    token = settings.TELEGRAM_BOT_TOKEN

    if not token:
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не настроен в settings.py")
        return False

    print(f"✅ Токен найден: {token[:10]}...{token[-10:]}")

    # Проверяем информацию о боте
    import requests
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        if response.status_code == 200:
            bot_info = response.json()['result']
            print(f"✅ Бот активен: @{bot_info['username']} ({bot_info['first_name']})")
            return True
        else:
            print(f"❌ Ошибка подключения к боту: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def check_telegram_users():
    """Проверка зарегистрированных Telegram пользователей"""
    print("\n" + "=" * 50)
    print("2. ПРОВЕРКА ЗАРЕГИСТРИРОВАННЫХ TELEGRAM ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 50)

    telegram_users = TelegramUser.objects.all()

    if not telegram_users.exists():
        print("⚠️  Нет зарегистрированных Telegram пользователей")
        return []

    print(f"✅ Найдено {telegram_users.count()} пользователей:")
    for tg_user in telegram_users:
        print(f"   - Барбер: {tg_user.barber.get_full_name()} | Telegram: @{tg_user.username}")
        if tg_user.chat_id:
            print(f"     Chat ID: {tg_user.chat_id}")
        else:
            print(f"     ⚠️  Chat ID не установлен")

    return list(telegram_users)


def test_send_message(telegram_users):
    """Тест отправки сообщений"""
    print("\n" + "=" * 50)
    print("3. ТЕСТ ОТПРАВКИ СООБЩЕНИЙ")
    print("=" * 50)

    if not telegram_users:
        print("⚠️  Нет пользователей для теста")
        return

    # Выбираем первого пользователя для теста
    tg_user = telegram_users[0]
    print(f"Отправка тестового сообщения для @{tg_user.username}...")

    success = send_test_message(
        username=tg_user.username,
        title="Тест системы уведомлений",
        message="Это тестовое сообщение. Если вы его видите - система уведомлений работает! 🎉"
    )

    if success:
        print("✅ Сообщение успешно отправлено!")
    else:
        print("❌ Ошибка отправки сообщения")

        # Пробуем отправить напрямую по chat_id
        if tg_user.chat_id:
            print(f"Пробуем отправить по chat_id: {tg_user.chat_id}")
            success = send_telegram_message(
                tg_user.chat_id,
                "*Тест по Chat ID*\n\nЭто сообщение отправлено напрямую по chat_id"
            )
            if success:
                print("✅ Отправка по chat_id успешна!")
            else:
                print("❌ Отправка по chat_id не удалась")


def test_booking_notification():
    """Тест уведомления о бронировании"""
    print("\n" + "=" * 50)
    print("4. ТЕСТ УВЕДОМЛЕНИЯ О БРОНИРОВАНИИ")
    print("=" * 50)

    # Находим барбера с Telegram
    barber = User.objects.filter(
        profile__user_type='barber',
        telegram_account__isnull=False
    ).first()

    if not barber:
        print("⚠️  Нет барберов с подключенным Telegram")
        return

    print(f"✅ Найден барбер: {barber.get_full_name()} (@{barber.telegram_account.username})")

    # Находим услугу этого барбера
    service = Service.objects.filter(barber=barber).first()
    if not service:
        print("⚠️  У барбера нет услуг")
        return

    print(f"✅ Найдена услуга: {service.title}")

    # Создаем тестовое бронирование
    tomorrow = timezone.now().date() + datetime.timedelta(days=1)

    booking_data = {
        'client_name': 'Тестовый Клиент',
        'client_phone': '+996 555 123456',
        'service_title': service.title,
        'date': tomorrow.strftime('%d.%m.%Y'),
        'time': '14:00',
        'notes': 'Это тестовое бронирование для проверки уведомлений'
    }

    print("\nОтправка тестового уведомления о бронировании...")
    success = send_booking_notification(barber.id, booking_data)

    if success:
        print("✅ Уведомление о бронировании отправлено!")
    else:
        print("❌ Ошибка отправки уведомления о бронировании")


def check_notifications_status():
    """Проверка статуса уведомлений в БД"""
    print("\n" + "=" * 50)
    print("5. СТАТУС УВЕДОМЛЕНИЙ В БАЗЕ ДАННЫХ")
    print("=" * 50)

    total = Notification.objects.count()
    pending = Notification.objects.filter(status='pending').count()
    sent = Notification.objects.filter(status='sent').count()
    failed = Notification.objects.filter(status='failed').count()

    print(f"Всего уведомлений: {total}")
    print(f"  - Ожидают отправки: {pending}")
    print(f"  - Отправлено: {sent}")
    print(f"  - Ошибка отправки: {failed}")

    # Показываем последние 5 уведомлений
    recent = Notification.objects.order_by('-created_at')[:5]
    if recent:
        print("\nПоследние уведомления:")
        for notif in recent:
            print(
                f"  - {notif.created_at.strftime('%d.%m %H:%M')} | {notif.recipient.username} | {notif.type} | {notif.status}")


def check_signal_registration():
    """Проверка регистрации сигналов"""
    print("\n" + "=" * 50)
    print("6. ПРОВЕРКА РЕГИСТРАЦИИ СИГНАЛОВ")
    print("=" * 50)

    from django.db.models import signals
    from bookings.models import Booking

    # Проверяем, есть ли обработчики для post_save сигнала Booking
    handlers = signals.post_save._live_receivers(sender=Booking)

    if handlers:
        print(f"✅ Найдено {len(handlers)} обработчиков для Booking.post_save")
        for handler in handlers:
            print(f"   - {handler}")
    else:
        print("❌ Обработчики сигналов не зарегистрированы!")


def main():
    """Главная функция"""
    print("\n" + "🔍 ДИАГНОСТИКА СИСТЕМЫ TELEGRAM УВЕДОМЛЕНИЙ" + "\n")

    # 1. Проверка подключения
    if not test_telegram_connection():
        print("\n❌ Критическая ошибка: не удается подключиться к Telegram Bot API")
        return

    # 2. Проверка пользователей
    telegram_users = check_telegram_users()

    # 3. Тест отправки сообщений
    if telegram_users:
        test_send_message(telegram_users)

    # 4. Тест уведомления о бронировании
    test_booking_notification()

    # 5. Статус уведомлений
    check_notifications_status()

    # 6. Проверка сигналов
    check_signal_registration()

    print("\n" + "=" * 50)
    print("✅ ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("=" * 50)

    print("\nРЕКОМЕНДАЦИИ:")
    print("1. Убедитесь, что бот @barber_tarak_bot активен")
    print("2. Барберы должны написать /start боту перед регистрацией")
    print("3. Проверьте, что TELEGRAM_BOT_TOKEN правильный в .env файле")
    print("4. Убедитесь, что сигналы импортируются в apps.py")


if __name__ == "__main__":
    main()