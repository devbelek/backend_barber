from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Booking
from .serializers import BookingSerializer
from .permissions import IsClientOrBarberOwner


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