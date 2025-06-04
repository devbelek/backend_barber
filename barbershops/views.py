from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg
from django.contrib.auth.models import User
from .models import Barbershop, BarbershopPhoto, BarbershopStaff, BarbershopApplication, BarbershopReview
from .serializers import (
    BarbershopSerializer,
    BarbershopCreateSerializer,
    BarbershopPhotoSerializer,
    BarbershopStaffSerializer,
    BarbershopApplicationSerializer,
    BarbershopReviewSerializer,
    AvailableBarberSerializer
)
from .permissions import IsBarbershopOwnerOrReadOnly
from services.models import Service
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


# ViewSet для заявок на регистрацию барбершопов
@extend_schema_view(
    list=extend_schema(
        summary="Получить список заявок",
        description="Возвращает список заявок на регистрацию барбершопов. Доступно только администраторам.",
        tags=['barbershop-applications']
    ),
    create=extend_schema(
        summary="Подать заявку на регистрацию барбершопа",
        description="Создает новую заявку на регистрацию барбершопа. Доступно всем.",
        tags=['barbershop-applications']
    ),
    retrieve=extend_schema(
        summary="Получить детали заявки",
        description="Возвращает детали конкретной заявки. Доступно только администраторам.",
        tags=['barbershop-applications']
    )
)
class BarbershopApplicationViewSet(viewsets.ModelViewSet):
    queryset = BarbershopApplication.objects.all()
    serializer_class = BarbershopApplicationSerializer

    def get_permissions(self):
        if self.action == 'create':
            # Создавать заявки могут все
            permission_classes = [permissions.AllowAny]
        else:
            # Просматривать и управлять заявками могут только админы
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

    @extend_schema(
        summary="Одобрить заявку",
        description="Одобряет заявку и создает барбершоп. Доступно только администраторам.",
        request={
            'type': 'object',
            'properties': {
                'notes': {
                    'type': 'string',
                    'description': 'Примечания администратора',
                    'example': 'Все документы в порядке'
                }
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Заявка одобрена'},
                    'barbershop_id': {'type': 'integer', 'example': 1}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Заявка уже рассмотрена'}
                }
            }
        },
        tags=['barbershop-applications']
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """Одобрить заявку"""
        application = self.get_object()

        try:
            barbershop = application.approve(request.user)

            # Обновляем примечания, если есть
            notes = request.data.get('notes')
            if notes:
                application.admin_notes = notes
                application.save()

            return Response({
                'message': 'Заявка одобрена',
                'barbershop_id': barbershop.id
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Отклонить заявку",
        description="Отклоняет заявку. Доступно только администраторам.",
        request={
            'type': 'object',
            'properties': {
                'reason': {
                    'type': 'string',
                    'description': 'Причина отклонения',
                    'example': 'Недостаточно информации о барбершопе'
                }
            },
            'required': ['reason']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Заявка отклонена'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Заявка уже рассмотрена'}
                }
            }
        },
        tags=['barbershop-applications']
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """Отклонить заявку"""
        application = self.get_object()
        reason = request.data.get('reason', '')

        try:
            application.reject(request.user, reason)
            return Response({'message': 'Заявка отклонена'})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Основной ViewSet для барбершопов
@extend_schema_view(
    list=extend_schema(
        summary="Получить список барбершопов",
        description="Возвращает список всех проверенных барбершопов",
        parameters=[
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Поиск по названию, адресу или описанию'
            ),
            OpenApiParameter(
                name='has_barber',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Фильтр по наличию конкретного барбера (ID)'
            ),
        ],
        tags=['barbershops']
    ),
    create=extend_schema(
        summary="Создать новый барбершоп",
        description="Создает новый барбершоп. Доступно только авторизованным пользователям. Барбершоп будет неверифицирован.",
        tags=['barbershops']
    ),
    retrieve=extend_schema(
        summary="Получить детали барбершопа",
        description="Возвращает подробную информацию о барбершопе",
        tags=['barbershops']
    ),
    update=extend_schema(
        summary="Обновить барбершоп",
        description="Обновляет информацию о барбершопе. Доступно только владельцу.",
        tags=['barbershops']
    ),
    partial_update=extend_schema(
        summary="Частично обновить барбершоп",
        description="Частично обновляет информацию о барбершопе. Доступно только владельцу.",
        tags=['barbershops']
    ),
    destroy=extend_schema(
        summary="Удалить барбершоп",
        description="Удаляет барбершоп. Доступно только владельцу.",
        tags=['barbershops']
    )
)
class BarbershopViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Barbershop.objects.filter(is_verified=True)

        # Поиск
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search) |
                Q(description__icontains=search)
            )

        # Фильтр по барберу
        has_barber = self.request.query_params.get('has_barber')
        if has_barber:
            queryset = queryset.filter(staff__user_id=has_barber, staff__role='barber')

        return queryset.distinct()

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

    @extend_schema(
        summary="Получить доступных барберов",
        description="Возвращает список барберов, которых можно добавить в барбершоп",
        responses={
            200: {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'username': {'type': 'string'},
                        'full_name': {'type': 'string'},
                        'specialization': {'type': 'string'},
                        'rating': {'type': 'number'},
                        'photo': {'type': 'string', 'format': 'uri', 'nullable': True},
                        'current_barbershops': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'integer'},
                                    'name': {'type': 'string'},
                                    'role': {'type': 'string'}
                                }
                            }
                        }
                    }
                }
            }
        },
        tags=['barbershops']
    )
    @action(detail=True, methods=['get'])
    def available_barbers(self, request, pk=None):
        """Получить список барберов, доступных для добавления"""
        barbershop = self.get_object()

        # Проверка прав (только владелец или менеджер)
        if not (barbershop.owner == request.user or
                barbershop.staff.filter(user=request.user, role__in=['owner', 'manager']).exists()):
            return Response(
                {"error": "У вас нет прав для просмотра списка барберов"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Получаем всех барберов
        barbers = User.objects.filter(
            profile__user_type='barber'
        ).exclude(
            # Исключаем тех, кто уже в этом барбершопе
            barbershop_staff__barbershop=barbershop
        ).select_related('profile').prefetch_related('barbershop_staff__barbershop')

        serializer = AvailableBarberSerializer(barbers, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Получить барберов барбершопа",
        description="Возвращает список всех барберов, работающих в данном барбершопе",
        tags=['barbershops']
    )
    @action(detail=True, methods=['get'])
    def barbers(self, request, pk=None):
        """Получить всех барберов барбершопа"""
        barbershop = self.get_object()
        barbers = barbershop.staff.filter(role='barber').select_related('user')
        serializer = BarbershopStaffSerializer(barbers, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Получить услуги барбершопа",
        description="Возвращает все услуги, предоставляемые барберами данного барбершопа",
        tags=['barbershops']
    )
    @action(detail=True, methods=['get'])
    def services(self, request, pk=None):
        """Получить все услуги барбершопа"""
        barbershop = self.get_object()
        barber_ids = barbershop.staff.filter(
            role='barber'
        ).values_list('user_id', flat=True)

        services = Service.objects.filter(barber_id__in=barber_ids)

        from services.serializers import ServiceSerializer
        serializer = ServiceSerializer(services, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Добавить барбера в барбершоп",
        description="Добавляет барбера в команду барбершопа. Доступно только владельцу или менеджеру.",
        request={
            'type': 'object',
            'properties': {
                'user_id': {
                    'type': 'integer',
                    'description': 'ID пользователя-барбера для добавления',
                    'example': 5
                }
            },
            'required': ['user_id']
        },
        tags=['barbershops']
    )
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

    @extend_schema(
        summary="Удалить барбера из барбершопа",
        description="Удаляет барбера из команды барбершопа. Доступно только владельцу или менеджеру.",
        tags=['barbershops']
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

    @extend_schema(
        summary="Загрузить фотографии барбершопа",
        description="Загружает фотографии барбершопа. Доступно только владельцу.",
        tags=['barbershops']
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

    @extend_schema(
        summary="Получить отзывы о барбершопе",
        description="Возвращает список отзывов о барбершопе",
        parameters=[
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Количество отзывов',
                default=10
            ),
            OpenApiParameter(
                name='offset',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Смещение',
                default=0
            ),
        ],
        tags=['barbershops']
    )
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Получить отзывы о барбершопе"""
        barbershop = self.get_object()

        limit = int(request.query_params.get('limit', 10))
        offset = int(request.query_params.get('offset', 0))

        reviews = barbershop.barbershop_reviews.all()[offset:offset + limit]
        serializer = BarbershopReviewSerializer(reviews, many=True)

        return Response({
            'count': barbershop.barbershop_reviews.count(),
            'results': serializer.data,
            'rating': barbershop.rating,
            'rating_distribution': self._get_rating_distribution(barbershop)
        })

    def _get_rating_distribution(self, barbershop):
        """Получить распределение оценок"""
        distribution = {}
        for i in range(1, 6):
            distribution[str(i)] = barbershop.barbershop_reviews.filter(rating=i).count()
        return distribution


# ViewSet для отзывов о барбершопах
@extend_schema_view(
    list=extend_schema(
        summary="Получить список отзывов о барбершопах",
        description="Возвращает отзывы текущего пользователя или отзывы о конкретном барбершопе",
        parameters=[
            OpenApiParameter(
                name='barbershop',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID барбершопа для фильтрации отзывов'
            )
        ],
        tags=['barbershop-reviews']
    ),
    create=extend_schema(
        summary="Создать отзыв о барбершопе",
        description="Создает новый отзыв о барбершопе. Один пользователь может оставить только один отзыв одному барбершопу.",
        tags=['barbershop-reviews']
    ),
    update=extend_schema(
        summary="Обновить отзыв",
        description="Обновляет отзыв. Доступно только автору отзыва.",
        tags=['barbershop-reviews']
    ),
    destroy=extend_schema(
        summary="Удалить отзыв",
        description="Удаляет отзыв. Доступно только автору отзыва.",
        tags=['barbershop-reviews']
    )
)
class BarbershopReviewViewSet(viewsets.ModelViewSet):
    serializer_class = BarbershopReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        barbershop_id = self.request.query_params.get('barbershop')
        if barbershop_id:
            return BarbershopReview.objects.filter(barbershop_id=barbershop_id)
        return BarbershopReview.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)