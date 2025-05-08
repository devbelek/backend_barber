from rest_framework import generics, permissions
from rest_framework.response import Response
from django.contrib.auth.models import User
from .serializers import UserSerializer, UserProfileSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .models import UserProfile


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