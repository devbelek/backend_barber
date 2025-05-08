from rest_framework import serializers
from .models import Booking
from services.serializers import ServiceSerializer


class BookingSerializer(serializers.ModelSerializer):
    service_details = ServiceSerializer(source='service', read_only=True)
    client_name = serializers.CharField(write_only=True, required=False)
    client_phone = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Booking
        fields = ['id', 'client', 'service', 'service_details', 'date', 'time', 'status', 'notes', 'created_at',
                  'client_name', 'client_phone']
        extra_kwargs = {
            'client': {'read_only': True},
            'service': {'write_only': True}
        }

    def create(self, validated_data):
        request = self.context.get('request')

        # Извлекаем client_name и client_phone, если они предоставлены
        client_name = validated_data.pop('client_name', None)
        client_phone = validated_data.pop('client_phone', None)

        # Если пользователь авторизован, используем его аккаунт
        if request and request.user.is_authenticated:
            validated_data['client'] = request.user
            return super().create(validated_data)

        # Если не авторизован, но предоставлены client_name и client_phone
        elif client_name and client_phone:
            # Создаем или получаем анонимного пользователя
            from django.contrib.auth.models import User
            from django.db.utils import IntegrityError

            try:
                # Пытаемся создать уникальное имя пользователя на основе телефона
                username = f"anonymous_{client_phone.replace(' ', '').replace('+', '')}"
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': client_name,
                        'email': f"{username}@anonymous.com"
                    }
                )
                # Устанавливаем клиента
                validated_data['client'] = user
                return super().create(validated_data)
            except IntegrityError:
                # Если имя пользователя уже существует, добавляем случайный суффикс
                import random
                username = f"anonymous_{client_phone.replace(' ', '').replace('+', '')}_{random.randint(1000, 9999)}"
                user = User.objects.create(
                    username=username,
                    first_name=client_name,
                    email=f"{username}@anonymous.com"
                )
                validated_data['client'] = user
                return super().create(validated_data)
        else:
            raise serializers.ValidationError("Требуются учетные данные аутентификации или информация о клиенте")