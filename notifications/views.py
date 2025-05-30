from django.utils import timezone
from rest_framework import views, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import TelegramUser, Notification
from .serializers import (
    TelegramUserSerializer,
    NotificationSerializer,
    TelegramRegistrationSerializer
)
import logging
from drf_spectacular.utils import extend_schema

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Зарегистрировать Telegram аккаунт",
    description="Регистрирует или обновляет Telegram аккаунт барбера для получения уведомлений о новых бронированиях",
    request={
        'type': 'object',
        'properties': {
            'username': {
                'type': 'string',
                'description': 'Telegram username без символа @',
                'example': 'my_telegram_username',
                'pattern': '^[a-zA-Z0-9_]+$'
            }
        },
        'required': ['username']
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'detail': {'type': 'string', 'example': 'Ваш Telegram аккаунт уже подключен'}
            }
        },
        201: {
            'type': 'object',
            'properties': {
                'detail': {'type': 'string', 'example': 'Ваш Telegram аккаунт успешно подключен'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'detail': {'type': 'string', 'example': 'Этот Telegram username уже зарегистрирован другим барбером'},
                'username': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'example': ['Имя пользователя Telegram может содержать только буквы, цифры и символ подчеркивания']
                }
            }
        },
        403: {
            'type': 'object',
            'properties': {
                'detail': {'type': 'string', 'example': 'Только барберы могут регистрировать Telegram аккаунт для уведомлений'}
            }
        }
    },
    tags=['notifications']
)
class TelegramRegistrationView(views.APIView):
    """
    API для регистрации Telegram аккаунта барбера.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Проверяем, что пользователь является барбером
        if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'barber':
            return Response(
                {"detail": "Только барберы могут регистрировать Telegram аккаунт для уведомлений"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = TelegramRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username'].lower()

            # Проверяем, не зарегистрирован ли уже этот username
            if TelegramUser.objects.filter(username=username).exists():
                existing_user = TelegramUser.objects.get(username=username)

                # Если этот Telegram аккаунт уже связан с этим барбером, возвращаем успех
                if existing_user.barber == request.user:
                    return Response(
                        {"detail": "Ваш Telegram аккаунт уже подключен"},
                        status=status.HTTP_200_OK
                    )

                # Иначе возвращаем ошибку, что этот username уже используется другим барбером
                return Response(
                    {"detail": "Этот Telegram username уже зарегистрирован другим барбером"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Проверяем, есть ли у текущего барбера уже зарегистрированный аккаунт
            try:
                telegram_user = TelegramUser.objects.get(barber=request.user)
                # Обновляем username
                telegram_user.username = username
                telegram_user.save()

                # Отправляем тестовое уведомление
                self._send_test_notification(request.user, username)

                return Response(
                    {"detail": "Ваш Telegram аккаунт успешно обновлен"},
                    status=status.HTTP_200_OK
                )
            except TelegramUser.DoesNotExist:
                # Создаем новую запись
                TelegramUser.objects.create(
                    barber=request.user,
                    username=username
                )

                # Отправляем тестовое уведомление
                self._send_test_notification(request.user, username)

                return Response(
                    {"detail": "Ваш Telegram аккаунт успешно подключен"},
                    status=status.HTTP_201_CREATED
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _send_test_notification(self, user, username):
        """Отправляет тестовое уведомление для проверки подключения."""
        try:
            # Создаем системное уведомление
            notification = Notification.objects.create(
                recipient=user,
                type='system',
                title='Подключение уведомлений',
                content=f'Вы успешно подключили уведомления через Telegram! Теперь вы будете получать информацию о новых бронированиях.',
                status='pending'
            )

            # ИСПРАВЛЕНО: Импортируем и используем функцию из bot.py
            from .bot import send_test_message

            # Отправляем уведомление через Telegram (синхронно)
            success = send_test_message(
                username=username,
                title='Подключение успешно!',
                message='Вы успешно подключили уведомления BarberHub! Теперь вы будете получать уведомления о новых бронированиях ваших услуг.'
            )

            # Обновляем статус уведомления
            if success:
                notification.status = 'sent'
                notification.sent_at = timezone.now()
            else:
                notification.status = 'failed'

            notification.save()

        except Exception as e:
            logger.error(f"Error sending test notification to {username}: {str(e)}")


@extend_schema(
    summary="Статус подключения Telegram",
    description="Проверяет статус подключения Telegram аккаунта текущего барбера",
    responses={
        200: {
            'type': 'object',
            'properties': {
                'registered': {'type': 'boolean', 'description': 'Зарегистрирован ли Telegram аккаунт'},
                'username': {'type': 'string', 'description': 'Telegram username (если зарегистрирован)'},
                'is_active': {'type': 'boolean', 'description': 'Активен ли аккаунт'},
                'connected_at': {'type': 'string', 'format': 'date-time', 'description': 'Дата подключения'}
            },
            'example': {
                'registered': True,
                'username': 'my_username',
                'is_active': True,
                'connected_at': '2025-05-30T10:00:00Z'
            }
        },
        403: {
            'type': 'object',
            'properties': {
                'detail': {'type': 'string', 'example': 'Только барберы могут использовать Telegram для уведомлений'}
            }
        }
    },
    tags=['notifications']
)
class TelegramStatusView(views.APIView):
    """
    API для проверки статуса подключения Telegram.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Проверяем, что пользователь является барбером
        if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'barber':
            return Response(
                {"detail": "Только барберы могут использовать Telegram для уведомлений"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            telegram_user = TelegramUser.objects.get(barber=request.user)
            return Response({
                "registered": True,
                "username": telegram_user.username,
                "is_active": telegram_user.is_active,
                "connected_at": telegram_user.connected_at
            })
        except TelegramUser.DoesNotExist:
            return Response({
                "registered": False
            })


@extend_schema(
    summary="Список уведомлений",
    description="Возвращает список последних 50 уведомлений для текущего пользователя",
    responses={
        200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'type': {'type': 'string', 'enum': ['booking_new', 'booking_confirmed', 'booking_cancelled', 'booking_reminder', 'system']},
                    'type_display': {'type': 'string', 'description': 'Отображаемое название типа'},
                    'title': {'type': 'string'},
                    'content': {'type': 'string'},
                    'status': {'type': 'string', 'enum': ['pending', 'sent', 'failed', 'read']},
                    'status_display': {'type': 'string', 'description': 'Отображаемое название статуса'},
                    'created_at': {'type': 'string', 'format': 'date-time'},
                    'sent_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                    'read_at': {'type': 'string', 'format': 'date-time', 'nullable': True}
                }
            }
        }
    },
    tags=['notifications']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_notifications(request):
    """
    Возвращает список уведомлений для текущего пользователя.
    """
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:50]
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Отметить уведомление как прочитанное",
    description="Помечает конкретное уведомление как прочитанное",
    responses={
        200: {
            'type': 'object',
            'properties': {
                'status': {'type': 'string', 'example': 'success'}
            }
        },
        404: {
            'type': 'object',
            'properties': {
                'detail': {'type': 'string', 'example': 'Уведомление не найдено'}
            }
        }
    },
    tags=['notifications']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_as_read(request, notification_id):
    """
    Отмечает уведомление как прочитанное.
    """
    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.status = 'read'
        notification.read_at = timezone.now()
        notification.save()
        return Response({"status": "success"})
    except Notification.DoesNotExist:
        return Response(
            {"detail": "Уведомление не найдено"},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    summary="Отметить все уведомления как прочитанные",
    description="Помечает все неприроченные уведомления пользователя как прочитанные",
    responses={
        200: {
            'type': 'object',
            'properties': {
                'status': {'type': 'string', 'example': 'success'}
            }
        }
    },
    tags=['notifications']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_as_read(request):
    """
    Отмечает все уведомления пользователя как прочитанные.
    """
    Notification.objects.filter(recipient=request.user, status__in=['sent', 'pending']).update(
        status='read',
        read_at=timezone.now()
    )
    return Response({"status": "success"})