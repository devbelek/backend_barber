import json


from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile
from rest_framework import serializers
from .models import UserProfile
import json


class UserProfileSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    working_days = serializers.JSONField(required=False)

    class Meta:
        model = UserProfile
        fields = [
            'user_type', 'phone', 'photo', 'whatsapp', 'telegram',
            'address', 'offers_home_service', 'bio', 'working_hours_from',
            'working_hours_to', 'working_days', 'latitude', 'longitude'
        ]
        extra_kwargs = {
            'latitude': {'required': False, 'allow_null': True},
            'longitude': {'required': False, 'allow_null': True},
            'working_hours_from': {'required': False},
            'working_hours_to': {'required': False},
        }


class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        fields = ['id', 'email', 'username', 'password', 'first_name', 'last_name']


class UserSerializer(BaseUserSerializer):
    profile = UserProfileSerializer()

    class Meta(BaseUserSerializer.Meta):
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'profile']