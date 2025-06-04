from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BarbershopViewSet, BarbershopApplicationViewSet, BarbershopReviewViewSet

router = DefaultRouter()
router.register(r'', BarbershopViewSet, basename='barbershop')
router.register(r'applications', BarbershopApplicationViewSet, basename='barbershop-application')
router.register(r'reviews', BarbershopReviewViewSet, basename='barbershop-review')

urlpatterns = [
    path('', include(router.urls)),
]