from django.urls import path
from .views import UserProfileView, UserProfileUpdateView

urlpatterns = [
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile-update'),
]