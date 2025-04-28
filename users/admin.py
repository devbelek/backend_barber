from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'phone', 'whatsapp', 'telegram']
    list_filter = ['user_type', 'offers_home_service']
    search_fields = ['user__username', 'user__email', 'phone']