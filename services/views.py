import os
from rest_framework import viewsets, permissions, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.db.models import Q, Avg, Count
from rest_framework.views import APIView

from .models import Service, ServiceImage, Banner
from .serializers import ServiceSerializer, BannerSerializer
from .permissions import IsBarberOrReadOnly


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

        # Фильтр по барберу
        barber = self.request.query_params.get('barber')
        if barber:
            queryset = queryset.filter(barber_id=barber)

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


class ActiveBannerAPIView(APIView):
    def get(self, request):
        banners = Banner.objects.filter(is_active=True)
        serializer = BannerSerializer(banners, many=True, context={"request": request})
        return Response(serializer.data)
