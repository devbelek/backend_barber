from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class GoogleAuthentication(BaseAuthentication):
    """
    Аутентификация для пользователей, которые входят через Google.
    """
    def authenticate(self, request):
        # Проверяем наличие специальных заголовков для Google-аутентификации
        google_auth = request.headers.get('X-Google-Auth')
        google_email = request.headers.get('X-Google-Email')

        if not google_auth or not google_email:
            return None

        try:
            # Находим пользователя по email
            user = User.objects.get(email=google_email)
            return (user, None)  # второй элемент - это токен аутентификации, но для нас он не нужен
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Пользователь с таким email не найден'))