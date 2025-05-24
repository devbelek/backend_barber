from rest_framework import viewsets, permissions, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from .models import Booking
from .serializers import BookingSerializer
from .permissions import IsClientOrBarberOwner
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime, timedelta
import pytz
from django.db.models import Count, Q
from django.utils import timezone


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'date']
    ordering_fields = ['date', 'time', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.user_type == 'barber':
            # Барбер видит бронирования на свои услуги
            return Booking.objects.filter(service__barber=user)
        else:
            # Клиент видит свои бронирования
            return Booking.objects.filter(client=user)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsClientOrBarberOwner]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def available_slots(self, request):
        """
        Возвращает доступные временные слоты для указанного барбера и даты.
        """
        barber_id = request.query_params.get('barber')
        date_str = request.query_params.get('date')

        if not barber_id or not date_str:
            return Response(
                {"error": "Необходимо указать параметры 'barber' и 'date'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Преобразуем строку даты в объект date
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # Получаем временную зону из настроек Django
            timezone = pytz.timezone(settings.TIME_ZONE)

            # Создаем начало и конец рабочего дня
            start_time = timezone.localize(datetime.combine(selected_date, datetime.min.time()))
            start_time = start_time.replace(hour=9, minute=0, second=0)  # 9:00
            end_time = timezone.localize(datetime.combine(selected_date, datetime.min.time()))
            end_time = end_time.replace(hour=21, minute=0, second=0)  # 21:00

            # Интервал между слотами (в минутах)
            interval = 30

            # Генерируем все возможные слоты
            all_slots = []
            current_time = start_time
            while current_time < end_time:
                all_slots.append({
                    'time': current_time.strftime('%H:%M'),
                    'available': True
                })
                current_time += timedelta(minutes=interval)

            # Получаем все бронирования на этот день для данного барбера
            existing_bookings = Booking.objects.filter(
                service__barber_id=barber_id,
                date=selected_date,
                status__in=['pending', 'confirmed']
            )

            # Помечаем занятые слоты
            for booking in existing_bookings:
                booking_time = booking.time.strftime('%H:%M')
                for slot in all_slots:
                    if slot['time'] == booking_time:
                        slot['available'] = False
                        break

            return Response(all_slots)

        except Exception as e:
            return Response(
                {"error": f"Ошибка при получении доступных слотов: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Получить статистику бронирований для барбера"""
        if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'barber':
            return Response(
                {"error": "Доступно только для барберов"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Статистика за последние 30 дней
        last_month = timezone.now() - timedelta(days=30)

        bookings = Booking.objects.filter(
            service__barber=request.user,
            created_at__gte=last_month
        )

        stats = {
            'total': bookings.count(),
            'pending': bookings.filter(status='pending').count(),
            'confirmed': bookings.filter(status='confirmed').count(),
            'completed': bookings.filter(status='completed').count(),
            'cancelled': bookings.filter(status='cancelled').count(),
            'by_service': bookings.values('service__title').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
        }

        return Response(stats)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Подтвердить бронирование (только для барбера)"""
        booking = self.get_object()

        if booking.service.barber != request.user:
            return Response(
                {"error": "Вы не можете подтвердить это бронирование"},
                status=status.HTTP_403_FORBIDDEN
            )

        if booking.status != 'pending':
            return Response(
                {"error": "Можно подтвердить только ожидающие бронирования"},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = 'confirmed'
        booking.save()

        return Response({"status": "Бронирование подтверждено"})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Отметить бронирование как выполненное (только для барбера)"""
        booking = self.get_object()

        if booking.service.barber != request.user:
            return Response(
                {"error": "Вы не можете завершить это бронирование"},
                status=status.HTTP_403_FORBIDDEN
            )

        if booking.status != 'confirmed':
            return Response(
                {"error": "Можно завершить только подтвержденные бронирования"},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = 'completed'
        booking.save()

        return Response({"status": "Бронирование завершено"})