import requests
import json
import logging
import base64
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserSerializer, UserProfileSerializer
from .models import UserProfile
from drf_spectacular.utils import extend_schema, OpenApiExample

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Изменить тип пользователя",
    description="Изменяет тип пользователя с клиента на барбера или наоборот. При смене на барбера требуется указать Telegram username.",
    request={
        'type': 'object',
        'properties': {
            'user_type': {
                'type': 'string',
                'enum': ['client', 'barber'],
                'description': 'Новый тип пользователя'
            },
            'telegram': {
                'type': 'string',
                'description': 'Telegram username (обязателен при смене на барбера)',
                'example': 'my_username'
            }
        },
        'required': ['user_type']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string', 'example': 'Тип пользователя изменен на barber'},
                'user': {'type': 'object', 'description': 'Обновленные данные пользователя'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string', 'example': 'Для барбера необходим Telegram'}
            }
        }
    },
    tags=['users']
)
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

        logger.info(f"User {request.user.id} changed type from {old_type} to {new_type}")

        return Response({
            "message": f"Тип пользователя изменен на {new_type}",
            "user": UserSerializer(request.user).data
        })
    except Exception as e:
        logger.error(f"Error changing user type for {request.user.id}: {str(e)}")
        return Response({"error": str(e)}, status=400)


@extend_schema(
    summary="Регистрация клиента",
    description="Регистрирует нового клиента с email и паролем",
    request={
        'type': 'object',
        'properties': {
            'email': {'type': 'string', 'format': 'email', 'example': 'client@example.com'},
            'password': {'type': 'string', 'minLength': 8, 'example': 'securepassword123'},
            'first_name': {'type': 'string', 'example': 'Иван'},
            'last_name': {'type': 'string', 'example': 'Иванов'},
            'phone': {'type': 'string', 'example': '+996700123456'}
        },
        'required': ['email', 'password']
    },
    responses={
        201: {
            'type': 'object',
            'properties': {
                'access': {'type': 'string', 'description': 'JWT Access Token'},
                'refresh': {'type': 'string', 'description': 'JWT Refresh Token'},
                'user': {'type': 'object', 'description': 'Данные созданного пользователя'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string', 'example': 'Пользователь с таким email уже существует'}
            }
        }
    },
    tags=['auth']
)
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

    try:
        # Создаем пользователя
        username = email.split('@')[0]
        counter = 1
        original_username = username
        while User.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Создаем профиль клиента
        UserProfile.objects.create(
            user=user,
            user_type='client',
            phone=phone
        )

        # Создаем токены
        refresh = RefreshToken.for_user(user)

        logger.info(f"New client registered: {email}")

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        }, status=201)

    except Exception as e:
        logger.error(f"Error registering client {email}: {str(e)}")
        return Response({"error": "Ошибка создания аккаунта"}, status=500)


@extend_schema(
    summary="Авторизация клиента",
    description="Авторизует клиента по email и паролю",
    request={
        'type': 'object',
        'properties': {
            'email': {'type': 'string', 'format': 'email', 'example': 'client@example.com'},
            'password': {'type': 'string', 'example': 'securepassword123'}
        },
        'required': ['email', 'password']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'access': {'type': 'string', 'description': 'JWT Access Token'},
                'refresh': {'type': 'string', 'description': 'JWT Refresh Token'},
                'user': {'type': 'object', 'description': 'Данные пользователя'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string', 'example': 'Неверный пароль'}
            }
        }
    },
    tags=['auth']
)
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
            logger.warning(f"Failed login attempt for {email}")
            return Response({"error": "Неверный пароль"}, status=400)

        # Создаем токены
        refresh = RefreshToken.for_user(user)

        logger.info(f"Successful login for {email}")

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })
    except User.DoesNotExist:
        logger.warning(f"Login attempt for non-existent user: {email}")
        return Response({"error": "Пользователь не найден"}, status=400)
    except Exception as e:
        logger.error(f"Login error for {email}: {str(e)}")
        return Response({"error": "Ошибка авторизации"}, status=500)


@extend_schema(
    summary="Удалить аккаунт",
    description="Полностью удаляет аккаунт текущего пользователя и все связанные данные",
    responses={
        204: {
            'description': 'Аккаунт успешно удален'
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'}
            }
        }
    },
    tags=['users']
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """Удаление аккаунта пользователя"""
    try:
        user = request.user
        user_email = user.email
        user.delete()

        logger.info(f"Account deleted for user: {user_email}")
        return Response({"message": "Аккаунт успешно удален"}, status=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error(f"Error deleting account for user {request.user.id}: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Авторизация через Google",
    description="Авторизует или регистрирует пользователя через Google OAuth. Поддерживает создание как клиентов, так и барберов. Включает fallback методы для регионов с ограниченным доступом к Google.",
    request={
        'type': 'object',
        'properties': {
            'token': {
                'type': 'string',
                'description': 'Google ID Token, полученный с фронтенда',
                'example': 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...'
            },
            'user_type': {
                'type': 'string',
                'enum': ['client', 'barber'],
                'default': 'client',
                'description': 'Тип пользователя для новых регистраций'
            }
        },
        'required': ['token']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'access': {'type': 'string', 'description': 'JWT Access Token'},
                'refresh': {'type': 'string', 'description': 'JWT Refresh Token'},
                'user': {'type': 'object', 'description': 'Данные пользователя'},
                'message': {'type': 'string', 'description': 'Сообщение о результате авторизации'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string', 'example': 'Invalid token'},
                'details': {'type': 'string', 'description': 'Детали ошибки'},
                'suggestion': {'type': 'string', 'description': 'Предложение по решению'}
            }
        },
        500: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string', 'example': 'Authentication failed'},
                'details': {'type': 'string', 'description': 'Детали ошибки'},
                'suggestion': {'type': 'string', 'description': 'Предложение по решению'}
            }
        }
    },
    tags=['auth']
)
@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """Аутентификация пользователя через Google с улучшенной обработкой ошибок"""
    token = request.data.get('token')
    user_type = request.data.get('user_type', 'client')

    if not token:
        return Response({"error": "Token is required"}, status=400)

    try:
        # Пробуем несколько способов верификации токена
        token_info = None

        # Способ 1: Прямая верификация через Google API
        try:
            response = requests.get(
                f'https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={token}',
                timeout=10
            )
            if response.ok:
                token_info = response.json()
                logger.info("Google token verified via direct API")
        except (requests.RequestException, requests.Timeout) as e:
            logger.warning(f"Direct Google API verification failed: {e}")

        # Способ 2: Локальная верификация JWT (без проверки подписи)
        if not token_info:
            try:
                # ВНИМАНИЕ: Это менее безопасно, используйте только в development
                # Декодируем payload JWT токена
                payload = token.split('.')[1]
                # Добавляем padding если нужно
                payload += '=' * (4 - len(payload) % 4)
                decoded_payload = base64.urlsafe_b64decode(payload)
                token_info = json.loads(decoded_payload.decode('utf-8'))

                # Основные проверки
                if not token_info.get('email'):
                    raise ValueError("Email not found in token")

                # Проверяем издателя
                if token_info.get('iss') not in ['https://accounts.google.com', 'accounts.google.com']:
                    raise ValueError("Invalid token issuer")

                logger.info("Google token verified locally (development mode)")

            except Exception as e:
                logger.error(f"Local token verification failed: {e}")
                return Response({
                    "error": "Token verification failed",
                    "details": "Не удалось проверить Google токен. Возможно, проблемы с подключением к Google сервисам.",
                    "suggestion": "Попробуйте использовать обычную регистрацию по email или fallback метод"
                }, status=400)

        email = token_info.get('email')
        if not email:
            return Response({"error": "Email not found in token"}, status=400)

        # Находим или создаем пользователя
        try:
            user = User.objects.get(email=email)
            # Обновляем данные, если они изменились
            updated = False
            if 'given_name' in token_info and token_info['given_name'] and user.first_name != token_info['given_name']:
                user.first_name = token_info['given_name']
                updated = True
            if 'family_name' in token_info and token_info['family_name'] and user.last_name != token_info[
                'family_name']:
                user.last_name = token_info['family_name']
                updated = True
            if updated:
                user.save()
            logger.info(f"Updated existing user: {email}")

        except User.DoesNotExist:
            # Создаем нового пользователя
            username = email.split('@')[0]
            # Проверка уникальности username
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1

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
            logger.info(f"Created new user: {email} as {user_type}")

        # Создаем JWT токены
        refresh = RefreshToken.for_user(user)

        # Формируем ответ с данными пользователя
        user_data = UserSerializer(user).data

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_data,
            'message': 'Authentication successful'
        })

    except Exception as e:
        logger.error(f"Google authentication error: {str(e)}", exc_info=True)
        return Response({
            "error": "Authentication failed",
            "details": str(e),
            "suggestion": "Попробуйте использовать обычную регистрацию по email или fallback метод"
        }, status=500)


@extend_schema(
    summary="Fallback авторизация",
    description="Резервный метод авторизации когда Google недоступен. Создает пользователя по минимальным данным.",
    request={
        'type': 'object',
        'properties': {
            'email': {
                'type': 'string',
                'format': 'email',
                'description': 'Email пользователя',
                'example': 'user@example.com'
            },
            'name': {
                'type': 'string',
                'description': 'Полное имя пользователя',
                'example': 'Иван Иванов'
            },
            'user_type': {
                'type': 'string',
                'enum': ['client', 'barber'],
                'default': 'client',
                'description': 'Тип пользователя'
            }
        },
        'required': ['email']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'access': {'type': 'string', 'description': 'JWT Access Token'},
                'refresh': {'type': 'string', 'description': 'JWT Refresh Token'},
                'user': {'type': 'object', 'description': 'Данные пользователя'},
                'message': {'type': 'string', 'example': 'Fallback authentication successful'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string', 'example': 'Email is required'}
            }
        }
    },
    tags=['auth']
)
@api_view(['POST'])
@permission_classes([AllowAny])
def fallback_auth(request):
    """Резервный метод аутентификации когда Google недоступен"""
    email = request.data.get('email')
    name = request.data.get('name', '')
    user_type = request.data.get('user_type', 'client')

    if not email:
        return Response({"error": "Email is required"}, status=400)

    try:
        # Пытаемся найти существующего пользователя
        try:
            user = User.objects.get(email=email)
            logger.info(f"Fallback auth for existing user: {email}")
        except User.DoesNotExist:
            # Создаем нового пользователя
            username = email.split('@')[0]
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1

            # Парсим имя
            name_parts = name.split(' ', 1) if name else ['', '']
            first_name = name_parts[0] if len(name_parts) > 0 else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=None
            )

            # Создаем или обновляем профиль
            try:
                profile = user.profile
                profile.user_type = user_type
                profile.save()
            except:
                # Если профиля нет, создаем новый
                from .models import UserProfile
                UserProfile.objects.create(
                    user=user,
                    user_type=user_type
                )

            logger.info(f"Created new user via fallback: {email}")

        # Создаем токены
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'message': 'Fallback authentication successful'
        })

    except Exception as e:
        # Логируем детальную ошибку
        logger.error(f"Fallback auth error for {email}: {str(e)}", exc_info=True)
        return Response({
            "error": "Ошибка fallback авторизации",
            "details": str(e)  # Добавляем детали для отладки
        }, status=500)

@extend_schema(
    summary="Регистрация Google пользователя",
    description="Регистрирует пользователя через Google OAuth (устаревший метод, используйте google_auth)",
    request={
        'type': 'object',
        'properties': {
            'email': {'type': 'string', 'format': 'email', 'example': 'user@gmail.com'},
            'first_name': {'type': 'string', 'example': 'Иван'},
            'last_name': {'type': 'string', 'example': 'Иванов'},
            'picture': {'type': 'string', 'format': 'uri', 'example': 'https://example.com/photo.jpg'}
        },
        'required': ['email']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'username': {'type': 'string'},
                'email': {'type': 'string'},
                'first_name': {'type': 'string'},
                'last_name': {'type': 'string'},
                'profile': {
                    'type': 'object',
                    'properties': {
                        'user_type': {'type': 'string'},
                        'photo': {'type': 'string', 'nullable': True}
                    }
                }
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string'}
            }
        }
    },
    tags=['auth'],
    deprecated=True
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_google_user(request):
    """
    Регистрация пользователя через Google (устаревший метод)
    """
    email = request.data.get('email')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    picture = request.data.get('picture', '')

    if not email:
        return Response({"error": "Email is required"}, status=400)

    try:
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
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1

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
        profile.save()

        logger.info(f"Google user registered/updated: {email}")

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
    except Exception as e:
        logger.error(f"Error in register_google_user for {email}: {str(e)}")
        return Response({"error": "Ошибка регистрации Google пользователя"}, status=500)


@csrf_exempt
@require_http_methods(["GET", "HEAD"])
def health_check(request):
    """Health check endpoint для проверки доступности сервера"""

    status_data = {
        'status': 'ok',
        'timestamp': timezone.now().isoformat(),
        'services': {
            'database': 'ok',
            'google_api': 'unknown'
        }
    }

    # Проверяем базу данных
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        status_data['services']['database'] = 'ok'
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        status_data['services']['database'] = 'error'
        status_data['status'] = 'degraded'

    # Проверяем Google API (если нужно)
    try:
        response = requests.get(
            'https://www.googleapis.com/oauth2/v3/certs',
            timeout=3
        )
        if response.status_code == 200:
            status_data['services']['google_api'] = 'ok'
        else:
            status_data['services']['google_api'] = 'unavailable'
    except Exception:
        status_data['services']['google_api'] = 'unavailable'

    return JsonResponse(status_data)


@extend_schema(
    summary="Профиль текущего пользователя",
    description="Получает или обновляет профиль текущего авторизованного пользователя",
    responses={
        200: {
            'type': 'object',
            'description': 'Данные пользователя с профилем'
        }
    },
    tags=['users']
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(
    summary="Обновить профиль пользователя",
    description="Обновляет профиль текущего пользователя. Поддерживает как JSON, так и FormData для загрузки файлов.",
    request={
        'type': 'object',
        'properties': {
            'user_type': {'type': 'string', 'enum': ['client', 'barber']},
            'phone': {'type': 'string', 'example': '+996700123456'},
            'photo': {'type': 'string', 'format': 'binary', 'description': 'Фото профиля'},
            'whatsapp': {'type': 'string', 'example': '+996700123456'},
            'telegram': {'type': 'string', 'example': 'username'},
            'address': {'type': 'string', 'example': 'Бишкек, ул. Манаса 45'},
            'offers_home_service': {'type': 'boolean'},
            'bio': {'type': 'string', 'description': 'Информация о барбере'},
            'working_hours_from': {'type': 'string', 'format': 'time', 'example': '09:00'},
            'working_hours_to': {'type': 'string', 'format': 'time', 'example': '20:00'},
            'working_days': {
                'type': 'array',
                'items': {'type': 'string', 'enum': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']},
                'example': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
            },
            'latitude': {'type': 'number', 'format': 'float', 'example': 42.8746},
            'longitude': {'type': 'number', 'format': 'float', 'example': 74.5698}
        }
    },
    responses={
        200: {
            'type': 'object',
            'description': 'Обновленные данные профиля'
        },
        400: {
            'type': 'object',
            'properties': {
                'field_name': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'example': ['Это поле обязательно.']
                }
            }
        }
    },
    tags=['users']
)
class UserProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)  # Делаем PATCH по умолчанию
        instance = self.get_object()

        # Логирование входящих данных
        logger.debug(f"Content-Type: {request.content_type}")
        logger.debug(f"Request data: {request.data}")

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

        logger.debug(f"Processed data: {data}")

        serializer = self.get_serializer(instance, data=data, partial=partial)

        if not serializer.is_valid():
            logger.warning(f"Profile update validation errors for user {request.user.id}: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_update(serializer)
        logger.info(f"Profile updated for user {request.user.id}")

        return Response(serializer.data)
