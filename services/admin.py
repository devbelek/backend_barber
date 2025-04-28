from django.contrib import admin
from .models import Service

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['title', 'barber', 'price', 'type', 'length', 'location']
    list_filter = ['type', 'length', 'style', 'location']
    search_fields = ['title', 'description', 'barber__username']