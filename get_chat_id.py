import requests
import os
import django
from django.conf import settings

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barberhub.settings')
django.setup()

TOKEN = settings.TELEGRAM_BOT_TOKEN


def get_chat_updates():
    """Получает последние сообщения для определения chat_id"""
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()

            print("🤖 Последние сообщения боту:")
            print("=" * 50)

            updates = data.get('result', [])
            if not updates:
                print("Нет сообщений. Отправьте любое сообщение боту @barber_tarak_bot")
                return

            for update in updates:
                if 'message' in update:
                    msg = update['message']
                    chat = msg['chat']
                    user = msg.get('from', {})

                    print(f"📱 Chat ID: {chat['id']}")
                    print(f"👤 Пользователь: {user.get('first_name', '')} {user.get('last_name', '')}")
                    print(f"🏷️ Username: @{user.get('username', 'не указан')}")
                    print(f"💬 Сообщение: {msg.get('text', 'медиа')}")
                    print(f"🕐 Время: {msg.get('date', '')}")
                    print("-" * 30)

            # Сохраняем последний chat_id для тестов
            if updates:
                last_chat_id = updates[-1]['message']['chat']['id']
                with open('last_chat_id.txt', 'w') as f:
                    f.write(str(last_chat_id))
                print(f"✅ Последний chat_id сохранен: {last_chat_id}")

        else:
            print(f"❌ Ошибка получения обновлений: {response.status_code}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")


def test_send_message():
    """Тестирует отправку сообщения на последний chat_id"""
    try:
        with open('last_chat_id.txt', 'r') as f:
            chat_id = f.read().strip()

        print(f"📤 Отправляю тестовое сообщение в chat_id: {chat_id}")

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': '🎉 Отлично! Бот TARAK работает!\n\nТеперь вы можете:\n• Зарегистрироваться как барбер\n• Получать уведомления о бронированиях\n• Управлять своими услугами',
            'parse_mode': 'Markdown'
        }

        response = requests.post(url, json=data, timeout=10)

        if response.status_code == 200:
            print("✅ Тестовое сообщение отправлено успешно!")
        else:
            print(f"❌ Ошибка отправки: {response.status_code} - {response.text}")

    except FileNotFoundError:
        print("❌ Файл last_chat_id.txt не найден. Сначала выполните get_updates()")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    print("🚀 Получение обновлений от Telegram бота...")
    get_chat_updates()

    print("\n" + "=" * 50)

    # Спрашиваем, отправить ли тестовое сообщение
    choice = input("Отправить тестовое сообщение? (y/n): ").lower()
    if choice == 'y':
        test_send_message()