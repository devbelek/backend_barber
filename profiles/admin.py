from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Favorite, Review

@admin.register(Favorite)
class FavoriteAdmin(ModelAdmin):
    list_display = ['display_user', 'display_service', 'created_at']
    list_filter = [
        ('created_at', admin.DateFieldListFilter),  # Standard date filter
        'service__barber'
    ]
    search_fields = [
        'user__username', 'user__email',
        'service__title', 'service__barber__username'
    ]
    readonly_fields = ['created_at']

    @display(description="Пользователь", ordering="user__username")
    def display_user(self, obj):
        return f"{obj.user.get_full_name() or obj.user.username} ({obj.user.email})"

    @display(description="Услуга", ordering="service__title")
    def display_service(self, obj):
        return f"{obj.service.title} - {obj.service.barber.get_full_name()}"

@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = [
        'display_author', 'display_barber', 'display_rating',
        'display_comment_preview', 'created_at'
    ]
    list_filter = [
        'rating',  # Standard filter for rating
        ('created_at', admin.DateFieldListFilter),  # Standard date filter
        'barber'
    ]
    search_fields = [
        'author__username', 'author__email',
        'barber__username', 'barber__email',
        'comment'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('author', 'barber', 'rating')
        }),
        ('Отзыв', {
            'fields': ('comment',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    @display(description="Автор", ordering="author__username")
    def display_author(self, obj):
        return obj.author.get_full_name() or obj.author.username

    @display(description="Барбер", ordering="barber__username")
    def display_barber(self, obj):
        return obj.barber.get_full_name() or obj.barber.username

    @display(description="Рейтинг")
    def display_rating(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        colors = {
            1: '#ef4444',
            2: '#f97316',
            3: '#f59e0b',
            4: '#84cc16',
            5: '#22c55e'
        }
        return format_html(
            '<span style="color: {}; font-size: 16px;">{}</span>',
            colors.get(obj.rating, '#6b7280'),
            stars
        )

    @display(description="Комментарий")
    def display_comment_preview(self, obj):
        if len(obj.comment) > 50:
            return f"{obj.comment[:50]}..."
        return obj.comment