from rest_framework import serializers
from .models import Booking
from services.serializers import ServiceSerializer


class BookingSerializer(serializers.ModelSerializer):
    service_details = ServiceSerializer(source='service', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'client', 'service', 'service_details', 'date', 'time', 'status', 'notes', 'created_at']
        extra_kwargs = {
            'client': {'read_only': True},
            'service': {'write_only': True}
        }

    def create(self, validated_data):
        # Устанавливаем текущего пользователя как клиента
        validated_data['client'] = self.context['request'].user
        return super().create(validated_data)