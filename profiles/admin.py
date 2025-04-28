from django.contrib import admin
from .models import Favorite, Review

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'service', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'service__title']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['author', 'barber', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['author__username', 'barber__username', 'comment']