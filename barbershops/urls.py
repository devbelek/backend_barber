from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BarbershopViewSet

router = DefaultRouter()
router.register(r'', BarbershopViewSet, basename='barbershop')

urlpatterns = [
    path('', include(router.urls)),
]