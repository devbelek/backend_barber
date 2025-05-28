from rest_framework import serializers
from .models import Barbershop, BarbershopPhoto, BarbershopStaff
from users.serializers import UserSerializer


class BarbershopPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BarbershopPhoto
        fields = ['id', 'photo', 'order']


class BarbershopStaffSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = BarbershopStaff
        fields = ['id', 'user', 'user_details', 'role', 'joined_at']


class BarbershopSerializer(serializers.ModelSerializer):
    photos = BarbershopPhotoSerializer(many=True, read_only=True)
    staff = BarbershopStaffSerializer(many=True, read_only=True)
    barbers = serializers.SerializerMethodField()
    rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()
    working_hours = serializers.SerializerMethodField()
    # Исправленное поле
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = Barbershop
        fields = [
            'id', 'name', 'logo', 'description', 'address',
            'latitude', 'longitude', 'phone', 'whatsapp',
            'telegram', 'instagram', 'working_hours_from',
            'working_hours_to', 'working_days', 'is_verified',
            'created_at', 'updated_at', 'photos', 'staff',
            'barbers', 'rating', 'review_count', 'working_hours'
        ]

    def get_barbers(self, obj):
        """Получить только барберов (не менеджеров и владельцев)"""
        barber_staff = obj.staff.filter(role='barber')
        return BarbershopStaffSerializer(barber_staff, many=True).data

    def get_working_hours(self, obj):
        """Форматировать рабочие часы для фронтенда - всегда возвращаем объект"""
        return {
            'from': obj.working_hours_from.strftime('%H:%M') if obj.working_hours_from else '09:00',
            'to': obj.working_hours_to.strftime('%H:%M') if obj.working_hours_to else '21:00',
            'days': obj.working_days if obj.working_days else ['Пн', 'Вт', 'Ср', 'Чт', 'Пт']
        }


class BarbershopCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barbershop
        fields = [
            'name', 'logo', 'description', 'address',
            'latitude', 'longitude', 'phone', 'whatsapp',
            'telegram', 'instagram', 'working_hours_from',
            'working_hours_to', 'working_days'
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        barbershop = Barbershop.objects.create(
            owner=user,
            **validated_data
        )
        # Автоматически добавляем владельца как staff
        BarbershopStaff.objects.create(
            barbershop=barbershop,
            user=user,
            role='owner'
        )
        return barbershop