from rest_framework import serializers
from .models import Favorite, Review
from services.serializers import ServiceSerializer
from users.serializers import UserSerializer


class FavoriteSerializer(serializers.ModelSerializer):
    service_details = ServiceSerializer(source='service', read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'service', 'service_details', 'created_at']
        extra_kwargs = {
            'service': {'write_only': True}
        }


class ReviewSerializer(serializers.ModelSerializer):
    author_details = UserSerializer(source='author', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'barber', 'rating', 'comment', 'created_at', 'author', 'author_details']
        extra_kwargs = {
            'author': {'read_only': True}
        }

    def create(self, validated_data):
        # Устанавливаем текущего пользователя как автора отзыва
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)