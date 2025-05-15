
import requests
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
import jwt

import json

from .serializers import UserSerializer, UserProfileSerializer
from .models import UserProfile


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_user_type(request):
    """Изменение типа пользователя с клиента на барбера"""
    new_type = request.data.get('user_type')

    if new_type not in ['client', 'barber']:
        return Response({"error": "Неверный тип пользователя"}, status=400)

    try:
        profile = request.user.profile
        old_type = profile.user_type

        # Если переключаемся на барбера, проверяем наличие Telegram
        if new_type == 'barber' and old_type == 'client':
            telegram = request.data.get('telegram')
            if not telegram:
                return Response({"error": "Для барбера необходим Telegram"}, status=400)
            profile.telegram = telegram

        profile.user_type = new_type
        profile.save()

        return Response({
            "message": f"Тип пользователя изменен на {new_type}",
            "user": UserSerializer(request.user).data
        })
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_client(request):
    """Регистрация обычного клиента"""
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    phone = request.data.get('phone', '')

    if not email or not password:
        return Response({"error": "Email и пароль обязательны"}, status=400)

    # Проверяем, существует ли пользователь
    if User.objects.filter(email=email).exists():
        return Response({"error": "Пользователь с таким email уже существует"}, status=400)

    # Создаем пользователя
    username = email.split('@')[0]
    if User.objects.filter(username=username).exists():
        username = f"{username}_{User.objects.count()}"

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name
    )

    # Создаем профиль клиента
    profile = UserProfile.objects.create(
        user=user,
        user_type='client',
        phone=phone
    )

    # Создаем токены
    refresh = RefreshToken.for_user(user)

    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data
    }, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_client(request):
    """Авторизация клиента"""
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({"error": "Email и пароль обязательны"}, status=400)

    try:
        user = User.objects.get(email=email)
        if not user.check_password(password):
            return Response({"error": "Неверный пароль"}, status=400)

        # Создаем токены
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })
    except User.DoesNotExist:
        return Response({"error": "Пользователь не найден"}, status=400)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """Удаление аккаунта пользователя"""
    try:
        user = request.user
        user.delete()
        return Response({"message": "Аккаунт успешно удален"}, status=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """Аутентификация пользователя через Google"""
    token = request.data.get('token')
    user_type = request.data.get('user_type', 'client')  # По умолчанию создаем клиента

    if not token:
        return Response({"error": "Token is required"}, status=400)

    try:
        # Проверка токена через Google API
        response = requests.get(f'https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={token}')
        if not response.ok:
            return Response({"error": "Invalid token"}, status=400)

        token_info = response.json()
        email = token_info.get('email')

        if not email:
            return Response({"error": "Email not found in token"}, status=400)

        # Находим или создаем пользователя
        try:
            user = User.objects.get(email=email)
            # Обновляем данные, если они изменились
            if 'given_name' in token_info and user.first_name != token_info['given_name']:
                user.first_name = token_info['given_name']
            if 'family_name' in token_info and user.last_name != token_info['family_name']:
                user.last_name = token_info['family_name']
            user.save()
        except User.DoesNotExist:
            # Создаем нового пользователя
            username = email.split('@')[0]
            # Проверка уникальности username
            if User.objects.filter(username=username).exists():
                username = f"{username}_{User.objects.count()}"

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=token_info.get('given_name', ''),
                last_name=token_info.get('family_name', ''),
                password=None
            )

            # Создаем профиль с указанным типом
            UserProfile.objects.create(
                user=user,
                user_type=user_type
            )

        # Создаем JWT токены
        refresh = RefreshToken.for_user(user)

        # Формируем ответ с данными пользователя
        user_data = UserSerializer(user).data

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_data
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": f"Authentication failed: {str(e)}"}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_google_user(request):
    """
    Регистрация пользователя через Google
    """
    email = request.data.get('email')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    picture = request.data.get('picture', '')

    if not email:
        return Response({"error": "Email is required"}, status=400)

    # Проверяем, существует ли пользователь с таким email
    try:
        user = User.objects.get(email=email)
        # Обновляем имя и фамилию, если они изменились
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if last_name and user.last_name != last_name:
            user.last_name = last_name
        user.save()
    except User.DoesNotExist:
        # Создаем нового пользователя
        username = email.split('@')[0]
        # Проверка уникальности username
        if User.objects.filter(username=username).exists():
            username = f"{username}_{User.objects.count()}"

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=None  # Пароль не нужен для Google-авторизации
        )

    # Проверяем, есть ли у пользователя профиль
    try:
        profile = user.profile
    except:
        # Создаем профиль, если его нет
        profile = UserProfile.objects.create(user=user)

    # Устанавливаем тип пользователя как барбер
    profile.user_type = 'barber'
    if picture:
        # Обработка URL картинки, если нужно сохранить изображение
        # Этот код может потребовать библиотеки для загрузки изображений
        # profile.photo = handle_profile_picture(picture)
        pass
    profile.save()

    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "profile": {
            "user_type": profile.user_type,
            "photo": profile.photo.url if profile.photo else None
        }
    })


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)  # Делаем PATCH по умолчанию
        instance = self.get_object()

        # Логирование входящих данных
        print(f"Content-Type: {request.content_type}")
        print(f"Request data: {request.data}")

        data = {}

        # Обрабатываем FormData
        if hasattr(request.data, 'getlist'):  # Проверяем, что это QueryDict (FormData)
            for key in request.data:
                value = request.data.get(key)

                # Специальная обработка для JSON полей
                if key == 'working_days' and value:
                    try:
                        data[key] = json.loads(value)
                    except json.JSONDecodeError:
                        data[key] = value
                elif key == 'offers_home_service':
                    data[key] = value in ['true', 'True', True]
                elif key == 'latitude' or key == 'longitude':
                    try:
                        data[key] = float(value) if value else None
                    except (ValueError, TypeError):
                        data[key] = None
                else:
                    data[key] = value
        else:
            data = request.data

        print(f"Processed data: {data}")

        serializer = self.get_serializer(instance, data=data, partial=partial)

        if not serializer.is_valid():
            print(f"Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_update(serializer)

        return Response(serializer.data)