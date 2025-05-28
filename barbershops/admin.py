from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Barbershop, BarbershopPhoto, BarbershopStaff


@admin.register(Barbershop)
class BarbershopAdmin(ModelAdmin):
    list_display = ['name', 'owner', 'phone', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['name', 'address', 'phone']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BarbershopPhoto)
class BarbershopPhotoAdmin(ModelAdmin):
    list_display = ['barbershop', 'order', 'uploaded_at']
    list_filter = ['barbershop']


@admin.register(BarbershopStaff)
class BarbershopStaffAdmin(ModelAdmin):
    list_display = ['barbershop', 'user', 'role', 'joined_at']
    list_filter = ['role', 'barbershop']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']