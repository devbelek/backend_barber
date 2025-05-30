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
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


@extend_schema_view(
    list=extend_schema(
        summary="Получить список бронирований",
        description="Возвращает бронирования текущего пользователя. Барберы видят бронирования на свои услуги, клиенты - свои бронирования.",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Фильтр по статусу бронирования',
                enum=['pending', 'confirmed', 'completed', 'cancelled']
            ),
            OpenApiParameter(
                name='date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Фильтр по дате бронирования (YYYY-MM-DD)'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Сортировка результатов',
                enum=['date', '-date', 'time', '-time', 'created_at', '-created_at']
            ),
        ],
        tags=['bookings']
    ),
    create=extend_schema(
        summary="Создать новое бронирование",
        description="Создает новое бронирование. Можно бронировать как авторизованным пользователям, так и анонимно с указанием контактных данных.",
        tags=['bookings']
    ),
    retrieve=extend_schema(
        summary="Получить детали бронирования",
        description="Возвращает подробную информацию о бронировании",
        tags=['bookings']
    ),
    update=extend_schema(
        summary="Обновить бронирование",
        description="Обновляет бронирование. Доступно клиенту-владельцу или барберу услуги",
        tags=['bookings']
    ),
    partial_update=extend_schema(
        summary="Частично обновить бронирование",
        description="Частично обновляет бронирование. Доступно клиенту-владельцу или барберу услуги",
        tags=['bookings']
    ),
    destroy=extend_schema(
        summary="Отменить бронирование",
        description="Отменяет бронирование. Доступно клиенту-владельцу или барберу услуги",
        tags=['bookings']
    )
)
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

    @extend_schema(
        summary="Получить доступные временные слоты",
        description="Возвращает доступные временные слоты для бронирования у конкретного барбера на указанную дату",
        parameters=[
            OpenApiParameter(
                name='barber',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True,
                description='ID барбера'
            ),
            OpenApiParameter(
                name='date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=True,
                description='Дата в формате YYYY-MM-DD'
            ),
        ],
        responses={
            200: {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'time': {'type': 'string', 'example': '10:00', 'description': 'Время слота в формате HH:MM'},
                        'available': {'type': 'boolean', 'description': 'Доступен ли слот для бронирования'}
                    }
                },
                'example': [
                    {'time': '09:00', 'available': True},
                    {'time': '09:30', 'available': True},
                    {'time': '10:00', 'available': False},
                    {'time': '10:30', 'available': True}
                ]
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': "Необходимо указать параметры 'barber' и 'date'"}
                }
            }
        },
        tags=['bookings']
    )
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

    @extend_schema(
        summary="Получить статистику бронирований",
        description="Возвращает статистику бронирований для барбера за последние 30 дней. Доступно только барберам.",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'total': {'type': 'integer', 'description': 'Общее количество бронирований'},
                    'pending': {'type': 'integer', 'description': 'Ожидающие подтверждения'},
                    'confirmed': {'type': 'integer', 'description': 'Подтвержденные'},
                    'completed': {'type': 'integer', 'description': 'Завершенные'},
                    'cancelled': {'type': 'integer', 'description': 'Отмененные'},
                    'totalRevenue': {'type': 'number', 'description': 'Общий доход от завершенных бронирований'},
                    'avgRating': {'type': 'number', 'description': 'Средний рейтинг барбера'},
                    'by_service': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'service__title': {'type': 'string'},
                                'count': {'type': 'integer'}
                            }
                        },
                        'description': 'Топ 5 услуг по количеству бронирований'
                    }
                }
            },
            403: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Доступно только для барберов'}
                }
            }
        },
        tags=['bookings']
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

        # Считаем общий доход
        total_revenue = bookings.filter(status='completed').aggregate(
            total=Sum('service__price')
        )['total'] or 0

        # Средний рейтинг барбера
        from profiles.models import Review
        avg_rating = Review.objects.filter(barber=request.user).aggregate(
            avg=Avg('rating')
        )['avg'] or 0

        stats = {
            'total': bookings.count(),
            'pending': bookings.filter(status='pending').count(),
            'confirmed': bookings.filter(status='confirmed').count(),
            'completed': bookings.filter(status='completed').count(),
            'cancelled': bookings.filter(status='cancelled').count(),
            'totalRevenue': float(total_revenue),
            'avgRating': round(avg_rating, 1),
            'by_service': bookings.values('service__title').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
        }

        return Response(stats)

    @extend_schema(
        summary="Подтвердить бронирование",
        description="Подтверждает бронирование. Доступно только барберу услуги.",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'Бронирование подтверждено'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Можно подтвердить только ожидающие бронирования'}
                }
            },
            403: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Вы не можете подтвердить это бронирование'}
                }
            }
        },
        tags=['bookings']
    )
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

    @extend_schema(
        summary="Завершить бронирование",
        description="Отмечает бронирование как выполненное. Доступно только барберу услуги.",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'Бронирование завершено'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Можно завершить только подтвержденные бронирования'}
                }
            },
            403: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Вы не можете завершить это бронирование'}
                }
            }
        },
        tags=['bookings']
    )
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