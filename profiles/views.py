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

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Favorite
from .serializers import FavoriteSerializer
from services.models import Service


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

    @action(detail=True, methods=['delete'], url_path='remove')
    def remove(self, request, pk=None):
        try:
            favorite = Favorite.objects.get(user=request.user, service_id=pk)
            favorite.delete()
            return Response({'status': 'Услуга удалена из избранного'}, status=status.HTTP_200_OK)
        except Favorite.DoesNotExist:
            return Response({'error': 'Услуга не найдена в избранном'}, status=status.HTTP_404_NOT_FOUND)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        barber_id = self.request.query_params.get('barber')
        if barber_id:
            return Review.objects.filter(barber_id=barber_id)
        return Review.objects.filter(author=self.request.user)


class BarberListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Изменено с AllowAny
    queryset = User.objects.filter(profile__user_type='barber')

    def get_queryset(self):
        return User.objects.filter(profile__user_type='barber')


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

        # Добавляем портфолио (услуги с фото)
        portfolio = []
        services = Service.objects.filter(barber=instance)
        for service in services:
            if service.image:
                portfolio.append(service.image.url)

        data['portfolio'] = portfolio

        return Response(data)


class UserProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile
