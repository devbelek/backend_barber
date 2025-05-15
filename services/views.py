from rest_framework import viewsets, permissions, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import Service
from .serializers import ServiceSerializer
from .permissions import IsBarberOrReadOnly


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'length', 'style', 'location', 'barber']
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsBarberOrReadOnly]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """
        Возвращает рекомендации услуг на основе местоположения пользователя.
        """
        try:
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')

            if not latitude or not longitude:
                return Response(
                    {"error": "Необходимо указать параметры 'latitude' и 'longitude'"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Получаем все услуги с ограничением по городу Бишкек
            services = Service.objects.filter(location__icontains='Бишкек')[:10]

            # Сериализуем данные
            serializer = self.get_serializer(services, many=True)

            return Response(serializer.data)

        except Exception as e:
            return Response(
                {"error": f"Ошибка при получении рекомендаций: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        # Для отладки в консоли сервера
        print("Received data:", request.data)
        print("Received files:", request.FILES)

        # Проверяем, что есть файл изображения
        if 'image' not in request.FILES:
            return Response({"image": "Изображение обязательно для загрузки"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Проверяем тип файла
        image_file = request.FILES['image']
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']

        # Извлекаем расширение из имени файла
        file_name = image_file.name
        extension = '.' + file_name.split('.')[-1].lower() if '.' in file_name else ''

        if extension not in valid_extensions:
            return Response(
                {"image": f"Поддерживаются только форматы: {', '.join(valid_extensions)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем размер файла (не более 5MB)
        if image_file.size > 5 * 1024 * 1024:
            return Response(
                {"image": "Размер файла не должен превышать 5MB"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем наличие поля barber
        # if 'barber' not in request.data:
        #     return Response(
        #         {"barber": "Это поле обязательно"},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        # Продолжаем стандартное создание
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)