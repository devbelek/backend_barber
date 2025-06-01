#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BarberHub Telegram Bot
Обработка команд /start, /help, /status для барберов
"""

import os
import sys
import django
import requests
import time
import json
from datetime import datetime

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barberhub.settings')
django.setup()

from notifications.models import TelegramUser

# Получаем токен
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    try:
        from django.conf import settings

        TOKEN = settings.TELEGRAM_BOT_TOKEN
    except:
        print("❌ TELEGRAM_BOT_TOKEN не найден!")
        sys.exit(1)


def send_message(chat_id, text, parse_mode='Markdown'):
    """Отправка сообщения"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        response = requests.post(url, data=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения: {e}")
        return {'ok': False, 'description': str(e)}


def get_updates(offset=None, timeout=10):
    """Получение обновлений"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        params = {'timeout': timeout}
        if offset:
            params['offset'] = offset

        response = requests.get(url, params=params, timeout=timeout + 5)
        return response.json()
    except Exception as e:
        print(f"❌ Ошибка получения обновлений: {e}")
        return {'ok': False, 'result': []}


def handle_start(message):
    """Обработка команды /start"""
    chat_id = message['chat']['id']
    user = message.get('from', {})
    username = user.get('username', '').lower()
    first_name = user.get('first_name', '')

    print(f"📥 /start от @{username} (ID: {chat_id}, Имя: {first_name})")

    if not username:
        no_username_msg = (
            "⚠️ *Нет username в Telegram*\n\n"
            "Для работы с BarberHub Bot нужен username.\n\n"
            "📱 *Как установить username:*\n"
            "1. Откройте Настройки Telegram\n"
            "2. Найдите поле 'Имя пользователя'\n"
            "3. Установите уникальное имя\n"
            "4. Отправьте /start снова"
        )
        send_message(chat_id, no_username_msg)
        return

    # Приветственное сообщение
    welcome_msg = (
        f"🤖 *BarberHub Bot*\n\n"
        f"Привет, {first_name}! 👋\n\n"
        f"🆔 Chat ID: `{chat_id}`\n"
        f"👤 Username: @{username}\n\n"
        f"⚡ Подключаю уведомления..."
    )
    send_message(chat_id, welcome_msg)

    # Ищем барбера в базе
    try:
        tg_user = TelegramUser.objects.get(username__iexact=username)

        # Обновляем данные
        old_chat_id = tg_user.chat_id
        tg_user.chat_id = str(chat_id)
        tg_user.is_active = True
        tg_user.save()

        print(f"✅ Обновлен @{username}: chat_id {old_chat_id} -> {chat_id}")

        # Сообщение об успехе
        success_msg = (
            f"🎉 *Уведомления подключены!*\n\n"
            f"👨‍💼 Барбер: {tg_user.barber.get_full_name()}\n"
            f"📱 Username: @{username}\n"
            f"🆔 Chat ID: `{chat_id}`\n\n"
            f"📬 *Теперь вы будете получать:*\n"
            f"• 🔔 Новые бронирования\n"
            f"• ✅ Подтверждения оплаты\n"
            f"• ❌ Отмены записей\n"
            f"• 📊 Важные уведомления\n\n"
            f"🚀 *Система готова к работе!*\n\n"
            f"💡 Используйте /help для справки"
        )
        send_message(chat_id, success_msg)

    except TelegramUser.DoesNotExist:
        print(f"❌ @{username} не найден в базе барберов")

        not_found_msg = (
            f"❌ *Барбер не найден*\n\n"
            f"@{username}, вы не зарегистрированы как барбер в BarberHub.\n\n"
            f"📝 *Для подключения уведомлений:*\n\n"
            f"1️⃣ Зайдите на сайт BarberHub\n"
            f"2️⃣ Зарегистрируйтесь как барбер\n"
            f"3️⃣ В профиле укажите Telegram: `{username}`\n"
            f"4️⃣ Отправьте /start этому боту\n\n"
            f"🆘 *Нужна помощь?*\n"
            f"Обратитесь к администратору сайта."
        )
        send_message(chat_id, not_found_msg)

    except Exception as e:
        print(f"❌ Ошибка обработки @{username}: {e}")
        send_message(chat_id, "❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору.")


def handle_help(message):
    """Обработка команды /help"""
    chat_id = message['chat']['id']

    help_msg = (
        "🤖 *BarberHub Bot - Справка*\n\n"
        "📋 *Доступные команды:*\n"
        "/start - Подключить уведомления\n"
        "/help - Показать эту справку\n"
        "/status - Проверить статус подключения\n\n"
        "💡 *Как подключиться:*\n"
        "1. Зарегистрируйтесь на сайте как барбер\n"
        "2. В профиле укажите ваш Telegram username\n"
        "3. Отправьте /start этому боту\n\n"
        "🔔 *Что вы получите:*\n"
        "• Мгновенные уведомления о новых записях\n"
        "• Информацию об отменах и изменениях\n"
        "• Напоминания о предстоящих сеансах\n\n"
        "🌐 *Сайт:* your-barberhub-site.com\n"
        "🆘 *Поддержка:* @admin_username"
    )
    send_message(chat_id, help_msg)


def handle_status(message):
    """Обработка команды /status"""
    chat_id = message['chat']['id']
    user = message.get('from', {})
    username = user.get('username', '').lower()

    if not username:
        send_message(chat_id, "❌ Нет username в Telegram")
        return

    try:
        tg_user = TelegramUser.objects.get(username__iexact=username)

        # Форматируем даты
        connected_date = tg_user.connected_at.strftime('%d.%m.%Y %H:%M') if tg_user.connected_at else 'Неизвестно'
        last_notif = tg_user.last_notification.strftime('%d.%m.%Y %H:%M') if tg_user.last_notification else 'Не было'

        status_msg = (
            f"📊 *Статус подключения*\n\n"
            f"👨‍💼 *Барбер:* {tg_user.barber.get_full_name()}\n"
            f"📧 *Email:* {tg_user.barber.email}\n"
            f"📱 *Username:* @{tg_user.username}\n"
            f"🆔 *Chat ID:* `{tg_user.chat_id}`\n"
            f"🟢 *Статус:* {'🟢 Активен' if tg_user.is_active else '🔴 Неактивен'}\n"
            f"📅 *Подключен:* {connected_date}\n"
            f"🔔 *Последнее уведомление:* {last_notif}\n\n"
            f"✅ *Все работает корректно!*\n\n"
            f"💡 Используйте /help для справки"
        )
        send_message(chat_id, status_msg)

    except TelegramUser.DoesNotExist:
        error_msg = (
            f"❌ *Не подключен*\n\n"
            f"@{username} не найден в базе барберов.\n\n"
            f"📝 Отправьте /start для инструкций по подключению."
        )
        send_message(chat_id, error_msg)


def handle_message(message):
    """Обработка обычных сообщений"""
    chat_id = message['chat']['id']
    text = message.get('text', '').strip().lower()

    if text.startswith('/'):
        # Неизвестная команда
        unknown_msg = (
            "❓ *Неизвестная команда*\n\n"
            "Используйте /help для просмотра доступных команд."
        )
        send_message(chat_id, unknown_msg)
    else:
        # Обычное сообщение
        info_msg = (
            "🤖 *BarberHub Bot*\n\n"
            "Я бот для уведомлений барберов.\n\n"
            "📋 Доступные команды:\n"
            "/start - Подключить уведомления\n"
            "/help - Справка\n"
            "/status - Статус подключения"
        )
        send_message(chat_id, info_msg)


def main():
    """Основной цикл бота"""
    print("🤖 Запуск BarberHub Telegram Bot")
    print(f"🔗 Ссылка: https://t.me/barber_tarak_bot")
    print(f"⏰ Время запуска: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 50)
    print("📝 Логи:")

    # Проверяем подключение к API
    try:
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=10)
        if response.status_code == 200:
            bot_info = response.json()['result']
            print(f"✅ Бот подключен: @{bot_info['username']} ({bot_info['first_name']})")
        else:
            print(f"❌ Ошибка подключения к Telegram API: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Не удалось подключиться к Telegram API: {e}")
        return

    print("⏹️ Остановка: Ctrl+C")
    print("-" * 50)

    offset = None
    error_count = 0
    max_errors = 10

    try:
        while True:
            try:
                updates = get_updates(offset, timeout=10)

                if not updates.get('ok'):
                    print(f"⚠️ Ошибка API: {updates.get('description', 'Неизвестная ошибка')}")
                    error_count += 1
                    if error_count >= max_errors:
                        print(f"❌ Слишком много ошибок ({max_errors}), остановка...")
                        break
                    time.sleep(5)
                    continue

                # Сбрасываем счетчик ошибок при успешном запросе
                error_count = 0

                for update in updates.get('result', []):
                    try:
                        offset = update['update_id'] + 1

                        if 'message' not in update:
                            continue

                        message = update['message']
                        text = message.get('text', '').strip()

                        if text == '/start':
                            handle_start(message)
                        elif text == '/help':
                            handle_help(message)
                        elif text == '/status':
                            handle_status(message)
                        else:
                            handle_message(message)

                    except Exception as e:
                        print(f"❌ Ошибка обработки сообщения: {e}")
                        continue

                time.sleep(1)

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"❌ Ошибка в основном цикле: {e}")
                error_count += 1
                if error_count >= max_errors:
                    break
                time.sleep(5)
                continue

    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        print(f"⏰ Время остановки: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print("📊 Сессия завершена")


if __name__ == '__main__':
    main()