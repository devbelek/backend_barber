from rest_framework import serializers
from .models import Service
from users.serializers import UserSerializer
from django.contrib.auth.models import User


class BarberMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class ServiceSerializer(serializers.ModelSerializer):
    barber_details = BarberMiniSerializer(source='barber', read_only=True)
    is_favorite = serializers.SerializerMethodField()
    image = serializers.ImageField(required=False)

    class Meta:
        model = Service
        fields = ['id', 'title', 'image', 'price', 'duration', 'type', 'length', 'style',
                  'location', 'description', 'created_at', 'barber', 'barber_details', 'is_favorite']
        extra_kwargs = {
            'barber': {'write_only': True}
        }

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(user=request.user).exists()
        return False

    def create(self, validated_data):
        # Устанавливаем текущего пользователя как барбера
        validated_data['barber'] = self.context['request'].user
        return super().create(validated_data)