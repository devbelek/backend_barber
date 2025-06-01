import os
from rest_framework import viewsets, permissions, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.db.models import Q, Avg, Count
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Service, ServiceImage, Banner
from .serializers import ServiceSerializer, BannerSerializer
from .permissions import IsBarberOrReadOnly


@extend_schema_view(
    list=extend_schema(
        summary="Получить список услуг",
        description="Возвращает список всех услуг с возможностью фильтрации по типу, длине волос, стилю и локации",
        parameters=[
            OpenApiParameter(
                name='types[]',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Фильтр по типам стрижки (можно передать несколько)',
                enum=['classic', 'fade', 'undercut', 'crop', 'pompadour', 'textured'],
                many=True
            ),
            OpenApiParameter(
                name='lengths[]',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Фильтр по длине волос (можно передать несколько)',
                enum=['short', 'medium', 'long'],
                many=True
            ),
            OpenApiParameter(
                name='styles[]',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Фильтр по стилю (можно передать несколько)',
                enum=['business', 'casual', 'trendy', 'vintage', 'modern'],
                many=True
            ),
            OpenApiParameter(
                name='locations[]',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Фильтр по локации (можно передать несколько)',
                many=True
            ),
            OpenApiParameter(
                name='barber',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID барбера для фильтрации услуг'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Поиск по названию, описанию, имени барбера или локации'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Сортировка результатов',
                enum=['price', '-price', 'created_at', '-created_at', 'views', '-views']
            ),
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Количество результатов на странице'
            ),
            OpenApiParameter(
                name='offset',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Смещение для пагинации'
            ),
        ],
        tags=['services']
    ),
    create=extend_schema(
        summary="Создать новую услугу",
        description="Создает новую услугу. Доступно только барберам. Обязательно загрузить хотя бы одно изображение.",
        tags=['services']
    ),
    retrieve=extend_schema(
        summary="Получить детали услуги",
        description="Возвращает подробную информацию об услуге включая изображения и данные барбера",
        tags=['services']
    ),
    update=extend_schema(
        summary="Обновить услугу",
        description="Обновляет услугу. Доступно только владельцу услуги.",
        tags=['services']
    ),
    partial_update=extend_schema(
        summary="Частично обновить услугу",
        description="Частично обновляет услугу. Доступно только владельцу услуги.",
        tags=['services']
    ),
    destroy=extend_schema(
        summary="Удалить услугу",
        description="Удаляет услугу. Доступно только владельцу услуги.",
        tags=['services']
    )
)
class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'barber__first_name', 'barber__last_name']
    ordering_fields = ['price', 'created_at', 'views']
    lookup_field = 'pk'
    lookup_value_regex = '[0-9]+'

    def get_queryset(self):
        queryset = Service.objects.all()

        # Фильтр по типам (массив)
        types = self.request.query_params.getlist('types[]')
        if not types:  # Если не передан как массив, пробуем получить как строку
            types_str = self.request.query_params.get('types')
            if types_str:
                types = types_str.split(',')

        if types:
            # Преобразуем значения фронтенда в значения бэкенда
            type_mapping = {
                'Классическая': 'classic',
                'Фейд': 'fade',
                'Андеркат': 'undercut',
                'Кроп': 'crop',
                'Помпадур': 'pompadour',
                'Текстурная': 'textured'
            }
            backend_types = [type_mapping.get(t, t) for t in types]
            queryset = queryset.filter(type__in=backend_types)

        # Фильтр по длине волос (массив)
        lengths = self.request.query_params.getlist('lengths[]')
        if not lengths:
            lengths_str = self.request.query_params.get('lengths')
            if lengths_str:
                lengths = lengths_str.split(',')

        if lengths:
            length_mapping = {
                'Короткие': 'short',
                'Средние': 'medium',
                'Длинные': 'long'
            }
            backend_lengths = [length_mapping.get(l, l) for l in lengths]
            queryset = queryset.filter(length__in=backend_lengths)

        # Фильтр по стилям (массив)
        styles = self.request.query_params.getlist('styles[]')
        if not styles:
            styles_str = self.request.query_params.get('styles')
            if styles_str:
                styles = styles_str.split(',')

        if styles:
            style_mapping = {
                'Деловой': 'business',
                'Повседневный': 'casual',
                'Трендовый': 'trendy',
                'Винтажный': 'vintage',
                'Современный': 'modern'
            }
            backend_styles = [style_mapping.get(s, s) for s in styles]
            queryset = queryset.filter(style__in=backend_styles)

        # Фильтр по локации
        locations = self.request.query_params.getlist('locations[]')
        if locations:
            location_query = Q()
            for location in locations:
                location_query |= Q(location__icontains=location)
            queryset = queryset.filter(location_query)

        # Фильтр по барберу - ИСПРАВЛЕННАЯ ВЕРСИЯ
        barber = self.request.query_params.get('barber')
        if barber:
            if barber == 'me' and self.request.user.is_authenticated:
                # Если передан 'me' и пользователь авторизован, фильтруем по текущему пользователю
                queryset = queryset.filter(barber=self.request.user)
            else:
                # Проверяем, что barber - это число
                try:
                    barber_id = int(barber)
                    queryset = queryset.filter(barber_id=barber_id)
                except (ValueError, TypeError):
                    # Если barber не число и не 'me', игнорируем фильтр
                    pass

        # Поиск
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(barber__first_name__icontains=search) |
                Q(barber__last_name__icontains=search) |
                Q(location__icontains=search)
            )

        # Сортировка
        ordering = self.request.query_params.get('ordering', '-views')
        valid_orderings = ['price', '-price', 'created_at', '-created_at', 'views', '-views']
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)

        return queryset

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsBarberOrReadOnly]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]

    @extend_schema(
        summary="Увеличить счетчик просмотров",
        description="Увеличивает счетчик просмотров для услуги на 1",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'views': {'type': 'integer', 'description': 'Новое количество просмотров'}
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Услуга не найдена'}
                }
            }
        },
        tags=['services']
    )
    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        """Увеличивает счетчик просмотров для услуги"""
        try:
            service = self.get_object()
            service.views += 1
            service.save()
            return Response({'views': service.views})
        except Service.DoesNotExist:
            return Response(
                {'error': 'Услуга не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        summary="Найти услуги поблизости",
        description="Возвращает услуги в указанном радиусе от заданных координат",
        parameters=[
            OpenApiParameter(
                name='latitude',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=True,
                description='Широта (-90 до 90)'
            ),
            OpenApiParameter(
                name='longitude',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=True,
                description='Долгота (-180 до 180)'
            ),
            OpenApiParameter(
                name='radius',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description='Радиус поиска в километрах (по умолчанию 5)',
                default=5
            ),
        ],
        responses={
            200: {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'title': {'type': 'string'},
                        'price': {'type': 'string'},
                        'distance': {'type': 'number', 'description': 'Расстояние в км'}
                    }
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        },
        tags=['services']
    )
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Получить услуги поблизости"""
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        radius = request.query_params.get('radius', 5)

        if not latitude or not longitude:
            return Response(
                {"error": "Требуются параметры latitude и longitude"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lat = float(latitude)
            lon = float(longitude)
            radius = float(radius)

            # Валидация координат
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return Response(
                    {"error": "Неверные координаты"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            services = Service.objects.filter(
                barber__profile__latitude__isnull=False,
                barber__profile__longitude__isnull=False
            ).select_related('barber__profile')

            nearby_services = []
            for service in services:
                barber_lat = service.barber.profile.latitude
                barber_lon = service.barber.profile.longitude

                distance = self._calculate_distance(lat, lon, barber_lat, barber_lon)

                if distance <= radius:
                    service_data = self.get_serializer(service).data
                    service_data['distance'] = round(distance, 1)
                    nearby_services.append(service_data)

            nearby_services.sort(key=lambda x: x['distance'])
            return Response(nearby_services)

        except ValueError:
            return Response(
                {"error": "Неверный формат координат"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Расчет расстояния между двумя точками в километрах"""
        from math import sin, cos, sqrt, atan2, radians

        R = 6371  # Радиус Земли в километрах

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def create(self, request, *args, **kwargs):
        """Создание новой услуги с изображениями"""
        # Проверяем наличие изображений
        if not request.FILES.getlist('uploaded_images'):
            return Response(
                {"uploaded_images": ["Необходимо загрузить хотя бы одно изображение"]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Валидация типов файлов
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif'}

        for image_file in request.FILES.getlist('uploaded_images'):
            file_ext = os.path.splitext(image_file.name)[1].lower()

            if file_ext not in valid_extensions:
                return Response(
                    {"uploaded_images": [f"Поддерживаются только форматы: {', '.join(valid_extensions)}"]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Проверка размера (5MB)
            if image_file.size > 5 * 1024 * 1024:
                return Response(
                    {"uploaded_images": ["Размер файла не должен превышать 5MB"]},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Обновление услуги с изображениями"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Обработка существующих изображений
        existing_images = request.data.getlist('existing_images', [])

        # Удаляем изображения, которые не в списке существующих
        if existing_images:
            instance.images.exclude(id__in=existing_images).delete()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)


@extend_schema(
    summary="Получить активные баннеры",
    description="Возвращает список всех активных баннеров для главной страницы",
    responses={
        200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'desktop_image': {'type': 'string', 'format': 'uri'},
                    'mobile_image': {'type': 'string', 'format': 'uri'}
                }
            }
        }
    },
    tags=['services']
)
class ActiveBannerAPIView(APIView):
    def get(self, request):
        banners = Banner.objects.filter(is_active=True)
        serializer = BannerSerializer(banners, many=True, context={"request": request})
        return Response(serializer.data)