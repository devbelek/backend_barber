from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from .models import Service, ServiceImage, ServiceView

class ServiceImageInline(TabularInline):
    model = ServiceImage
    extra = 1
    fields = ['image', 'is_primary', 'order']

@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    inlines = [ServiceImageInline]
    list_display = [
        'display_thumbnail', 'title', 'display_barber', 'price',
        'type', 'display_views', 'created_at'
    ]
    list_filter = [
        'type',  # Standard filter for type
        'length',  # Standard filter for length
        'style',  # Standard filter for style
        ('created_at', admin.DateFieldListFilter),  # Standard date filter
        'barber'
    ]
    search_fields = ['title', 'description', 'barber__username', 'barber__first_name', 'barber__last_name']
    readonly_fields = ['views', 'created_at', 'updated_at']
    actions = ["export_action", "import_action"]
    export_form = ExportForm
    import_form = ImportForm

    fieldsets = (
        ('Основная информация', {
            'fields': ('barber', 'title', 'price', 'duration', 'description')
        }),
        ('Категории', {
            'fields': ('type', 'length', 'style')
        }),
        ('Местоположение', {
            'fields': ('location',)
        }),
        ('Статистика', {
            'fields': ('views', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    @display(description="Изображение")
    def display_thumbnail(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />',
                primary_image.image.url
            )
        return "—"

    @display(description="Барбер", ordering="barber__first_name")
    def display_barber(self, obj):
        return obj.barber.get_full_name() or obj.barber.username

    @display(description="Просмотры", ordering="views")
    def display_views(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            '#22c55e' if obj.views > 100 else '#f59e0b' if obj.views > 50 else '#6b7280',
            obj.views
        )