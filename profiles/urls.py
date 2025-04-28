from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FavoriteViewSet, ReviewViewSet, BarberListView

router = DefaultRouter()
router.register(r'favorites', FavoriteViewSet, basename='favorite')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls)),
    path('barbers/', BarberListView.as_view(), name='barber-list'),
]