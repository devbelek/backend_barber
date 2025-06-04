from django.contrib.auth.models import User
from barbershops.models import Barbershop, BarbershopApplication
from services.models import Service
from bookings.models import Booking
from profiles.models import Review
from django.utils import timezone
from datetime import timedelta


def dashboard_callback(request, context):
    """
    Callback для dashboard в админке Django Unfold
    """
    # Статистика за последние 30 дней
    last_30_days = timezone.now() - timedelta(days=30)

    # Основная статистика
    context.update({
        "stats": [
            {
                "label": "Пользователей",
                "value": User.objects.count(),
                "icon": "people",
                "color": "primary",
            },
            {
                "label": "Барбершопов",
                "value": Barbershop.objects.filter(is_verified=True).count(),
                "icon": "store",
                "color": "success",
            },
            {
                "label": "Услуг",
                "value": Service.objects.count(),
                "icon": "cut",
                "color": "info",
            },
            {
                "label": "Бронирований",
                "value": Booking.objects.count(),
                "icon": "calendar_today",
                "color": "warning",
            },
        ],
        "recent_stats": [
            {
                "label": "Новых пользователей (30 дней)",
                "value": User.objects.filter(date_joined__gte=last_30_days).count(),
                "trend": "up",
            },
            {
                "label": "Новых бронирований (30 дней)",
                "value": Booking.objects.filter(created_at__gte=last_30_days).count(),
                "trend": "up",
            },
            {
                "label": "Новых отзывов (30 дней)",
                "value": Review.objects.filter(created_at__gte=last_30_days).count(),
                "trend": "up",
            },
        ],
        "pending_applications": BarbershopApplication.objects.filter(status='pending').count(),
    })

    return context


def badge_callback(request):
    """
    Callback для badge в навигации
    """
    pending_count = BarbershopApplication.objects.filter(status='pending').count()
    return pending_count if pending_count > 0 else None