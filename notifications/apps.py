from django.apps import AppConfig

class NotificationsConfig(AppConfig):  # Изменено с BookingsConfig
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'  # Изменено с 'bookings'

    def ready(self):
        import notifications.signals  # Изменено