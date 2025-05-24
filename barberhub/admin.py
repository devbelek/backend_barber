def dashboard_callback(request, context):
    """
    Callback для отображения статистики на главной странице админки
    """
    from services.models import Service
    from bookings.models import Booking
    from users.models import UserProfile
    from django.contrib.auth.models import User
    from django.utils import timezone
    from datetime import timedelta

    # Статистика за последние 30 дней
    last_month = timezone.now() - timedelta(days=30)

    context.update({
        "total_users": User.objects.count(),
        "total_barbers": UserProfile.objects.filter(user_type='barber').count(),
        "total_clients": UserProfile.objects.filter(user_type='client').count(),
        "total_services": Service.objects.count(),
        "total_bookings": Booking.objects.count(),
        "recent_bookings": Booking.objects.filter(created_at__gte=last_month).count(),
        "pending_bookings": Booking.objects.filter(status='pending').count(),
    })

    return context


def badge_callback(request):
    """
    Callback для отображения бейджа с количеством ожидающих бронирований
    """
    from bookings.models import Booking

    count = Booking.objects.filter(status='pending').count()
    return count if count > 0 else None