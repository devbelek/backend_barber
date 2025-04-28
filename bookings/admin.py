from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['client', 'service', 'date', 'time', 'status']
    list_filter = ['status', 'date']
    search_fields = ['client__username', 'service__title']
    date_hierarchy = 'date'