import os
from rest_framework import serializers
from django.db import models
from .models import Service, ServiceImage
from users.serializers import UserSerializer
from django.contrib.auth.models import User


class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = ['id', 'image', 'is_primary', 'order']


class BarberDetailsSerializer(serializers.ModelSerializer):
    """Сериализатор с дополнительной информацией о барбере"""
    full_name = serializers.SerializerMethodField()
    whatsapp = serializers.CharField(source='profile.whatsapp', read_only=True)
    telegram = serializers.CharField(source='profile.telegram', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'whatsapp', 'telegram']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class ServiceSerializer(serializers.ModelSerializer):
    barber_details = BarberDetailsSerializer(source='barber', read_only=True)
    is_favorite = serializers.SerializerMethodField()
    images = ServiceImageSerializer(many=True, read_only=True)
    primary_image = serializers.SerializerMethodField()
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Service
        fields = [
            'id', 'title', 'price', 'duration', 'type', 'length',
            'style', 'location', 'description', 'views', 'created_at',
            'barber', 'barber_details', 'is_favorite', 'images',
            'primary_image', 'uploaded_images'
        ]
        extra_kwargs = {
            'barber': {'write_only': True},
            'views': {'read_only': True}
        }

    def get_primary_image(self, obj):
        request = self.context.get('request')

        # Ищем основное изображение
        primary = obj.images.filter(is_primary=True).first()
        if primary and primary.image:
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url

        # Если нет основного, берем первое
        first_image = obj.images.first()
        if first_image and first_image.image:
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url

        return None

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(user=request.user).exists()
        return False

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        validated_data['barber'] = self.context['request'].user
        service = super().create(validated_data)

        # Создаем записи для изображений
        for index, image in enumerate(uploaded_images):
            ServiceImage.objects.create(
                service=service,
                image=image,
                is_primary=(index == 0),  # Первое изображение - основное
                order=index
            )

        return service

    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])

        # Обновляем основные поля
        instance = super().update(instance, validated_data)

        # Добавляем новые изображения
        if uploaded_images:
            # Определяем порядок для новых изображений
            last_order = instance.images.aggregate(
                max_order=models.Max('order')
            )['max_order'] or -1

            for index, image in enumerate(uploaded_images):
                ServiceImage.objects.create(
                    service=instance,
                    image=image,
                    is_primary=False,  # Новые изображения не основные
                    order=last_order + index + 1
                )

        return instance