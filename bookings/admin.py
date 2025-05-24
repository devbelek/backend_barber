from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display
from django.urls import reverse
from django.utils import timezone
from .models import Booking

@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = [
        'display_service', 'display_client', 'date', 'time',
        'display_status', 'display_phone', 'created_at'
    ]
    list_filter = [
        'status',  # Standard filter for status
        ('date', admin.DateFieldListFilter),  # Standard date filter for booking date
        ('created_at', admin.DateFieldListFilter),  # Standard date filter for creation date
        'service__barber'  # Filter by barber of the service
    ]
    search_fields = [
        'client__username', 'client__email', 'client__first_name',
        'client__last_name', 'client_name_contact', 'client_phone_contact',
        'service__title'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    actions = ["confirm_bookings", "cancel_bookings"]

    fieldsets = (
        ('Информация о бронировании', {
            'fields': ('service', 'client', 'date', 'time', 'status')
        }),
        ('Контактная информация', {
            'fields': ('client_name_contact', 'client_phone_contact', 'notes')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    @display(description="Услуга", ordering="service__title")
    def display_service(self, obj):
        url = reverse("admin:services_service_change", args=[obj.service.pk])
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            url, obj.service.title, obj.service.barber.get_full_name()
        )

    @display(description="Клиент", ordering="client__first_name")
    def display_client(self, obj):
        return obj.client_name

    @display(description="Статус")
    def display_status(self, obj):
        colors = {
            'pending': '#f59e0b',
            'confirmed': '#3b82f6',
            'completed': '#22c55e',
            'cancelled': '#ef4444'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6b7280'),
            obj.get_status_display()
        )

    @display(description="Телефон")
    def display_phone(self, obj):
        phone = obj.client_phone
        if phone:
            return format_html(
                '<a href="tel:{}">{}</a>',
                phone, phone
            )
        return "—"

    def confirm_bookings(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='confirmed',
            updated_at=timezone.now()
        )
        self.message_user(request, f"Подтверждено бронирований: {updated}")
    confirm_bookings.short_description = "Подтвердить выбранные бронирования"

    def cancel_bookings(self, request, queryset):
        updated = queryset.exclude(status__in=['completed', 'cancelled']).update(
            status='cancelled',
            updated_at=timezone.now()
        )
        self.message_user(request, f"Отменено бронирований: {updated}")
    cancel_bookings.short_description = "Отменить выбранные бронирования"