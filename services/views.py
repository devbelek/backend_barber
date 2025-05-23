from rest_framework import viewsets, permissions, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.db.models import Q

from .models import Service, ServiceImage
from .serializers import ServiceSerializer
from .permissions import IsBarberOrReadOnly


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'length', 'style', 'location', 'barber']
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at', 'views']

    def get_queryset(self):
        queryset = Service.objects.all()

        # Фильтр по типу
        types = self.request.query_params.getlist('types[]')
        if types:
            queryset = queryset.filter(type__in=types)

        # Фильтр по локации
        locations = self.request.query_params.getlist('locations[]')
        if locations:
            queryset = queryset.filter(location__in=locations)

        # Поиск
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        # Сортировка
        ordering = self.request.query_params.get('ordering', '-views')
        if ordering in ['price', '-price', 'created_at', '-created_at', 'views', '-views']:
            queryset = queryset.order_by(ordering)

        return queryset

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsBarberOrReadOnly]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Возвращает рекомендации услуг на основе местоположения пользователя."""
        try:
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')

            if not latitude or not longitude:
                # Если координаты не указаны, возвращаем популярные услуги
                services = Service.objects.all().order_by('-views')[:10]
            else:
                # Фильтруем по городу
                services = Service.objects.filter(location__icontains='Бишкек')[:10]

            serializer = self.get_serializer(services, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {"error": f"Ошибка при получении рекомендаций: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        """Увеличивает счетчик просмотров для услуги"""
        try:
            service = self.get_object()

            # Увеличиваем счетчик без проверки IP для упрощения
            service.views += 1
            service.save()

            return Response({'views': service.views})
        except Service.DoesNotExist:
            return Response(
                {'error': 'Услуга не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )

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