from django.urls import path
from .views import UserProfileView, UserProfileUpdateView
from .views import register_google_user

urlpatterns = [
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile-update'),
    path('register-google/', register_google_user, name='register-google'),

]