from django.urls import path
from .views import UserProfileView, UserProfileUpdateView, register_google_user, google_auth

urlpatterns = [
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile-update'),
    path('register-google/', register_google_user, name='register-google'),
    path('auth/google/', google_auth, name='google-auth'),
]