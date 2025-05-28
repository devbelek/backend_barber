from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Barbershop, BarbershopPhoto, BarbershopStaff
from .serializers import (
    BarbershopSerializer,
    BarbershopCreateSerializer,
    BarbershopPhotoSerializer,
    BarbershopStaffSerializer
)
from .permissions import IsBarbershopOwnerOrReadOnly
from services.models import Service


class BarbershopViewSet(viewsets.ModelViewSet):
    queryset = Barbershop.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BarbershopCreateSerializer
        return BarbershopSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsBarbershopOwnerOrReadOnly]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['get'])
    def barbers(self, request, pk=None):
        """Получить всех барберов барбершопа"""
        barbershop = self.get_object()
        barbers = barbershop.staff.filter(role='barber').select_related('user')
        serializer = BarbershopStaffSerializer(barbers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def services(self, request, pk=None):
        """Получить все услуги барбершопа"""
        barbershop = self.get_object()
        # Получаем всех барберов барбершопа
        barber_ids = barbershop.staff.filter(
            role='barber'
        ).values_list('user_id', flat=True)

        # Получаем услуги этих барберов
        services = Service.objects.filter(barber_id__in=barber_ids)

        from services.serializers import ServiceSerializer
        serializer = ServiceSerializer(services, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_barber(self, request, pk=None):
        """Добавить барбера в барбершоп"""
        barbershop = self.get_object()

        # Проверка прав (только владелец или менеджер)
        if not (barbershop.owner == request.user or
                barbershop.staff.filter(user=request.user, role__in=['owner', 'manager']).exists()):
            return Response(
                {"error": "У вас нет прав для добавления барберов"},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {"error": "user_id обязателен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id, profile__user_type='barber')

            # Проверяем, не добавлен ли уже
            if barbershop.staff.filter(user=user).exists():
                return Response(
                    {"error": "Барбер уже добавлен в этот барбершоп"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            staff = BarbershopStaff.objects.create(
                barbershop=barbershop,
                user=user,
                role='barber'
            )

            serializer = BarbershopStaffSerializer(staff)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response(
                {"error": "Барбер не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['delete'])
    def remove_barber(self, request, pk=None):
        """Удалить барбера из барбершопа"""
        barbershop = self.get_object()

        # Проверка прав
        if not (barbershop.owner == request.user or
                barbershop.staff.filter(user=request.user, role__in=['owner', 'manager']).exists()):
            return Response(
                {"error": "У вас нет прав для удаления барберов"},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {"error": "user_id обязателен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            staff = barbershop.staff.get(user_id=user_id)

            # Нельзя удалить владельца
            if staff.role == 'owner':
                return Response(
                    {"error": "Нельзя удалить владельца барбершопа"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            staff.delete()
            return Response(
                {"message": "Барбер удален из барбершопа"},
                status=status.HTTP_204_NO_CONTENT
            )

        except BarbershopStaff.DoesNotExist:
            return Response(
                {"error": "Барбер не найден в этом барбершопе"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def upload_photos(self, request, pk=None):
        """Загрузить фотографии барбершопа"""
        barbershop = self.get_object()

        # Проверка прав
        if barbershop.owner != request.user:
            return Response(
                {"error": "Только владелец может загружать фотографии"},
                status=status.HTTP_403_FORBIDDEN
            )

        photos = request.FILES.getlist('photos')
        if not photos:
            return Response(
                {"error": "Фотографии не предоставлены"},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_photos = []
        for index, photo in enumerate(photos):
            barbershop_photo = BarbershopPhoto.objects.create(
                barbershop=barbershop,
                photo=photo,
                order=index
            )
            created_photos.append(barbershop_photo)

        serializer = BarbershopPhotoSerializer(created_photos, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)