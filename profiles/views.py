from rest_framework import viewsets, generics, permissions, status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Favorite, Review
from .serializers import FavoriteSerializer, ReviewSerializer
from users.serializers import UserSerializer
from services.models import Service
from django.db.models import Avg, Count
from rest_framework import generics, permissions
from django.contrib.auth.models import User
from users.serializers import UserProfileSerializer
from users.models import UserProfile
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


@extend_schema_view(
    list=extend_schema(
        summary="Получить избранные услуги",
        description="Возвращает список избранных услуг текущего пользователя",
        tags=['profiles']
    ),
    create=extend_schema(
        summary="Добавить услугу в избранное",
        description="Добавляет услугу в избранное текущего пользователя",
        tags=['profiles']
    ),
    retrieve=extend_schema(
        summary="Получить детали избранной услуги",
        description="Возвращает детали конкретной избранной услуги",
        tags=['profiles']
    ),
    destroy=extend_schema(
        summary="Удалить услугу из избранного",
        description="Удаляет услугу из избранного по ID услуги",
        tags=['profiles']
    )
)
class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        service_id = request.data.get('service')

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return Response({'error': 'Услуга не найдена'}, status=status.HTTP_404_NOT_FOUND)

        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            service=service
        )

        if created:
            serializer = self.get_serializer(favorite)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response({'status': 'Услуга уже в избранном'}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Переключить избранное для услуги",
        description="Добавляет услугу в избранное если её там нет, или удаляет если есть",
        request={
            'type': 'object',
            'properties': {
                'service': {
                    'type': 'integer',
                    'description': 'ID услуги для переключения',
                    'example': 1
                }
            },
            'required': ['service']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'string',
                        'enum': ['added', 'removed'],
                        'description': 'Статус операции'
                    }
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Не указан ID услуги'}
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Услуга не найдена'}
                }
            }
        },
        tags=['profiles']
    )
    @action(detail=False, methods=['post'], url_path='toggle')
    def toggle(self, request):
        """Переключение избранного для сервиса"""
        service_id = request.data.get('service')

        if not service_id:
            return Response({'error': 'Не указан ID услуги'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = Service.objects.get(id=service_id)

            # Проверяем, существует ли уже запись избранного
            favorite_exists = Favorite.objects.filter(
                user=request.user,
                service=service
            ).exists()

            if favorite_exists:
                # Если уже есть в избранном - удаляем
                Favorite.objects.filter(
                    user=request.user,
                    service=service
                ).delete()
                return Response({'status': 'removed'}, status=status.HTTP_200_OK)
            else:
                # Если нет в избранном - добавляем
                Favorite.objects.create(
                    user=request.user,
                    service=service
                )
                return Response({'status': 'added'}, status=status.HTTP_201_CREATED)

        except Service.DoesNotExist:
            return Response({'error': 'Услуга не найдена'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error in toggle: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Переопределяем destroy для удаления по service_id
    def destroy(self, request, *args, **kwargs):
        service_id = kwargs.get('pk')
        try:
            favorite = Favorite.objects.get(user=request.user, service_id=service_id)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Favorite.DoesNotExist:
            return Response({'error': 'Не найдено в избранном'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        summary="Удалить услугу из избранного",
        description="Удаляет конкретную услугу из избранного по ID услуги",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'Услуга удалена из избранного'}
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Услуга не найдена в избранном'}
                }
            }
        },
        tags=['profiles']
    )
    @action(detail=True, methods=['delete'], url_path='remove')
    def remove(self, request, pk=None):
        try:
            favorite = Favorite.objects.get(user=request.user, service_id=pk)
            favorite.delete()
            return Response({'status': 'Услуга удалена из избранного'}, status=status.HTTP_200_OK)
        except Favorite.DoesNotExist:
            return Response({'error': 'Услуга не найдена в избранном'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema_view(
    list=extend_schema(
        summary="Получить список отзывов",
        description="Возвращает отзывы текущего пользователя или отзывы о конкретном барбере",
        parameters=[
            OpenApiParameter(
                name='barber',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID барбера для фильтрации отзывов'
            )
        ],
        tags=['profiles']
    ),
    create=extend_schema(
        summary="Создать отзыв",
        description="Создает новый отзыв о барбере. Один пользователь может оставить только один отзыв одному барберу.",
        tags=['profiles']
    ),
    retrieve=extend_schema(
        summary="Получить детали отзыва",
        tags=['profiles']
    ),
    update=extend_schema(
        summary="Обновить отзыв",
        description="Обновляет отзыв. Доступно только автору отзыва.",
        tags=['profiles']
    ),
    destroy=extend_schema(
        summary="Удалить отзыв",
        description="Удаляет отзыв. Доступно только автору отзыва.",
        tags=['profiles']
    )
)
class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        barber_id = self.request.query_params.get('barber')
        if barber_id:
            return Review.objects.filter(barber_id=barber_id)
        return Review.objects.filter(author=self.request.user)


@extend_schema(
    summary="Получить список барберов",
    description="Возвращает список всех зарегистрированных барберов в системе",
    responses={
        200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'description': 'Данные барбера (см. схему User)'
            }
        }
    },
    tags=['profiles']
)
class BarberListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Изменено с AllowAny
    queryset = User.objects.filter(profile__user_type='barber')

    def get_queryset(self):
        return User.objects.filter(profile__user_type='barber')


@extend_schema(
    summary="Получить детали барбера",
    description="Возвращает подробную информацию о барбере включая рейтинг, количество отзывов и портфолио",
    responses={
        200: {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'username': {'type': 'string'},
                'first_name': {'type': 'string'},
                'last_name': {'type': 'string'},
                'email': {'type': 'string'},
                'profile': {
                    'type': 'object',
                    'description': 'Данные профиля барбера'
                },
                'avg_rating': {
                    'type': 'number',
                    'format': 'float',
                    'description': 'Средний рейтинг барбера'
                },
                'review_count': {
                    'type': 'integer',
                    'description': 'Количество отзывов о барбере'
                },
                'portfolio': {
                    'type': 'array',
                    'items': {'type': 'string', 'format': 'uri'},
                    'description': 'Изображения из портфолио барбера'
                }
            }
        },
        404: {
            'type': 'object',
            'properties': {
                'detail': {'type': 'string', 'example': 'Не найдено.'}
            }
        }
    },
    tags=['profiles']
)
class BarberDetailView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = User.objects.filter(profile__user_type='barber')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        # Дополняем информацию рейтингом и количеством отзывов
        reviews = Review.objects.filter(barber=instance)
        avg_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
        review_count = reviews.count()

        data['avg_rating'] = round(avg_rating, 1)
        data['review_count'] = review_count

        # Добавляем портфолио (основные изображения услуг)
        portfolio = []
        services = Service.objects.filter(barber=instance)
        for service in services:
            # Пытаемся получить основное изображение
            primary_image = service.images.filter(is_primary=True).first()
            if primary_image:
                portfolio.append(request.build_absolute_uri(primary_image.image.url))
            else:
                # Если основного нет, берём первое изображение
                first_image = service.images.first()
                if first_image:
                    portfolio.append(request.build_absolute_uri(first_image.image.url))

        data['portfolio'] = portfolio

        return Response(data)


@extend_schema(
    summary="Обновить профиль пользователя",
    description="Обновляет профиль текущего пользователя",
    request={
        'type': 'object',
        'description': 'Данные для обновления профиля (см. схему UserProfile)'
    },
    responses={
        200: {
            'type': 'object',
            'description': 'Обновленные данные профиля'
        },
        400: {
            'type': 'object',
            'properties': {
                'field_name': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'example': ['Это поле обязательно.']
                }
            }
        }
    },
    tags=['profiles']
)
class UserProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile