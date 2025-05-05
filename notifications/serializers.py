from rest_framework import serializers
from .models import TelegramUser, Notification


class TelegramUserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели TelegramUser."""
    barber_name = serializers.SerializerMethodField()

    class Meta:
        model = TelegramUser
        fields = ['id', 'barber', 'barber_name', 'username', 'is_active', 'connected_at', 'last_notification']
        read_only_fields = ['barber', 'connected_at', 'last_notification']

    def get_barber_name(self, obj):
        return f"{obj.barber.first_name} {obj.barber.last_name}".strip() or obj.barber.username


class TelegramRegistrationSerializer(serializers.Serializer):
    """Сериализатор для регистрации Telegram аккаунта."""
    username = serializers.CharField(max_length=64)

    def validate_username(self, value):
        # Проверяем, что имя пользователя не содержит "@"
        if value.startswith('@'):
            raise serializers.ValidationError("Пожалуйста, введите имя пользователя без символа @")

        # Валидируем формат имени пользователя (только буквы, цифры и _)
        if not all(c.isalnum() or c == '_' for c in value):
            raise serializers.ValidationError(
                "Имя пользователя Telegram может содержать только буквы, цифры и символ подчеркивания"
            )

        return value.lower()


class NotificationSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Notification."""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'type', 'type_display', 'title', 'content',
            'related_object_id', 'related_object_type', 'status', 'status_display',
            'created_at', 'sent_at', 'read_at'
        ]
        read_only_fields = ['recipient', 'created_at', 'sent_at', 'read_at']