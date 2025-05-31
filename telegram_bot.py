import os, sys, django, requests, time, json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barberhub.settings')
django.setup()

from notifications.models import TelegramUser

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') or __import__('django.conf',
                                                           fromlist=['settings']).settings.TELEGRAM_BOT_TOKEN


def send_message(chat_id, text):
    return requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                         data={'chat_id': chat_id, 'text': text}).json()


def get_updates(offset=None):
    params = {'timeout': 10}
    if offset: params['offset'] = offset
    try:
        return requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params=params, timeout=15).json()
    except:
        return {'ok': False, 'result': []}


def handle_start(message):
    chat_id, user = message['chat']['id'], message.get('from', {})
    username = user.get('username')
    print(f"START от @{username} chat_id: {chat_id}")

    send_message(chat_id, f"✅ BarberHub бот!\nВаш chat_id: {chat_id}\nUsername: @{username}")

    if username:
        try:
            tg_user = TelegramUser.objects.get(username=username.lower())
            tg_user.chat_id = str(chat_id)
            tg_user.save()
            print(f"✅ chat_id сохранен для @{username}")
            send_message(chat_id, f"🎉 @{username} подключен к уведомлениям!")
        except TelegramUser.DoesNotExist:
            print(f"❌ @{username} не найден в базе")
            send_message(chat_id, f"❌ @{username} не найден в BarberHub.\nЗарегистрируйтесь как барбер на сайте.")


print("🚀 Запуск бота @barber_tarak_bot")
print("🔗 https://t.me/barber_tarak_bot")
offset = None
try:
    while True:
        for update in get_updates(offset).get('result', []):
            offset = update['update_id'] + 1
            if 'message' in update and update['message'].get('text') == '/start':
                handle_start(update['message'])
        time.sleep(1)
except KeyboardInterrupt:
    print("👋 Остановлен")