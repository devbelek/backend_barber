from django.urls import path
from .views import (
    UserProfileView, UserProfileUpdateView,
    register_google_user, google_auth,
    delete_account, register_client, login_client, change_user_type
)

urlpatterns = [
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile-update'),
    path('register-google/', register_google_user, name='register-google'),
    path('auth/google/', google_auth, name='google-auth'),
    path('delete-account/', delete_account, name='delete-account'),
    path('change-user-type/', change_user_type, name='change-user-type'),

    # Новые эндпоинты для клиентов
    path('register/', register_client, name='register-client'),
    path('login/', login_client, name='login-client'),
]