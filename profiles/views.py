from rest_framework import viewsets, generics, permissions, status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from .models import Favorite, Review
from .serializers import FavoriteSerializer, ReviewSerializer
from users.serializers import UserSerializer
from services.models import Service
from django.db.models import Avg, Count


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
            return Response({'status': 'Услуга добавлена в избранное'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'Услуга уже в избранном'}, status=status.HTTP_200_OK)

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