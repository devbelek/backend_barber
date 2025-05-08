from django.urls import path
from .views import (
    TelegramRegistrationView,
    TelegramStatusView,
    list_notifications,
    mark_as_read,
    mark_all_as_read
)

urlpatterns = [
    path('register-telegram/', TelegramRegistrationView.as_view(), name='register-telegram'),
    path('telegram-status/', TelegramStatusView.as_view(), name='telegram-status'),
    path('list/', list_notifications, name='list-notifications'),
    path('mark-read/<int:notification_id>/', mark_as_read, name='mark-notification-read'),
    path('mark-all-read/', mark_all_as_read, name='mark-all-notifications-read'),
]