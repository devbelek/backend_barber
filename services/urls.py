from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet, ActiveBannerAPIView

router = DefaultRouter()
router.register(r'', ServiceViewSet, basename='service')

urlpatterns = [
    path('', include(router.urls)),
    path('banners/', ActiveBannerAPIView.as_view(), name='active-banners'),
]
