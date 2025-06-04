from rest_framework import serializers
from .models import Barbershop, BarbershopPhoto, BarbershopStaff, BarbershopApplication, BarbershopReview
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


class BarbershopReviewSerializer(serializers.ModelSerializer):
    author_details = UserSerializer(source='author', read_only=True)

    class Meta:
        model = BarbershopReview
        fields = ['id', 'barbershop', 'rating', 'comment', 'created_at', 'author', 'author_details']
        extra_kwargs = {
            'author': {'read_only': True}
        }

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class BarbershopSerializer(serializers.ModelSerializer):
    photos = BarbershopPhotoSerializer(many=True, read_only=True)
    staff = BarbershopStaffSerializer(many=True, read_only=True)
    barbers = serializers.SerializerMethodField()
    rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()
    barbers_rating = serializers.ReadOnlyField()
    working_hours = serializers.SerializerMethodField()
    is_verified = serializers.BooleanField(read_only=True)
    owner_details = UserSerializer(source='owner', read_only=True)
    latest_reviews = serializers.SerializerMethodField()

    class Meta:
        model = Barbershop
        fields = [
            'id', 'name', 'logo', 'description', 'address',
            'latitude', 'longitude', 'phone', 'whatsapp',
            'telegram', 'instagram', 'working_hours_from',
            'working_hours_to', 'working_days', 'is_verified',
            'created_at', 'updated_at', 'photos', 'staff',
            'barbers', 'rating', 'review_count', 'barbers_rating',
            'working_hours', 'owner', 'owner_details', 'latest_reviews'
        ]

    def get_barbers(self, obj):
        """Получить только барберов (не менеджеров и владельцев)"""
        barber_staff = obj.staff.filter(role='barber')
        return BarbershopStaffSerializer(barber_staff, many=True).data

    def get_working_hours(self, obj):
        """Форматировать рабочие часы для фронтенда"""
        return {
            'from': obj.working_hours_from.strftime('%H:%M') if obj.working_hours_from else '09:00',
            'to': obj.working_hours_to.strftime('%H:%M') if obj.working_hours_to else '21:00',
            'days': obj.working_days if obj.working_days else ['Пн', 'Вт', 'Ср', 'Чт', 'Пт']
        }

    def get_latest_reviews(self, obj):
        """Получить последние 3 отзыва о барбершопе"""
        reviews = obj.barbershop_reviews.all()[:3]
        return BarbershopReviewSerializer(reviews, many=True).data


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


class BarbershopApplicationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = BarbershopApplication
        fields = [
            'id', 'applicant_name', 'applicant_email', 'applicant_phone',
            'barbershop_name', 'barbershop_address', 'barbershop_description',
            'barbershop_phone', 'barbershop_whatsapp', 'barbershop_instagram',
            'barbers_count', 'working_experience', 'additional_info',
            'status', 'status_display', 'created_at', 'reviewed_at',
            'admin_notes'
        ]
        read_only_fields = ['status', 'created_at', 'reviewed_at', 'admin_notes']

    def validate_applicant_email(self, value):
        # Проверяем, что email не используется существующим пользователем
        from django.contrib.auth.models import User
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже зарегистрирован. Войдите в систему для создания барбершопа."
            )
        return value

    def validate_barbershop_name(self, value):
        # Проверяем уникальность названия барбершопа
        if Barbershop.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                "Барбершоп с таким названием уже существует."
            )
        return value


class AvailableBarberSerializer(serializers.ModelSerializer):
    """Сериализатор для списка доступных барберов"""
    full_name = serializers.SerializerMethodField()
    specialization = serializers.CharField(source='profile.specialization', read_only=True)
    rating = serializers.SerializerMethodField()
    photo = serializers.ImageField(source='profile.photo', read_only=True)
    current_barbershops = serializers.SerializerMethodField()

    class Meta:
        model = UserSerializer.Meta.model
        fields = ['id', 'username', 'full_name', 'specialization', 'rating', 'photo', 'current_barbershops']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_rating(self, obj):
        from profiles.models import Review
        from django.db.models import Avg
        avg = obj.received_reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0

    def get_current_barbershops(self, obj):
        # Показываем, в каких барбершопах уже работает барбер
        staffs = obj.barbershop_staff.select_related('barbershop')
        return [
            {
                'id': staff.barbershop.id,
                'name': staff.barbershop.name,
                'role': staff.get_role_display()
            }
            for staff in staffs
        ]