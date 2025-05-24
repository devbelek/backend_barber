from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import display
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import UserProfile

User = get_user_model()

admin.site.unregister(User)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'Профиль'
    verbose_name_plural = 'Профиль'
    fields = (
        'user_type', 'phone', 'photo', 'whatsapp', 'telegram',
        'address', 'offers_home_service', 'bio',
        'working_hours_from', 'working_hours_to', 'working_days',
        'latitude', 'longitude'
    )

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "bio":
            kwargs["widget"] = WysiwygWidget
        return super().formfield_for_dbfield(db_field, **kwargs)


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined')


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin, ImportExportModelAdmin):
    resource_class = UserResource
    inlines = (UserProfileInline,)

    list_display = ['username', 'email', 'display_full_name', 'display_user_type', 'display_is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'profile__user_type', ('date_joined', RangeDateFilter)]
    search_fields = ['username', 'email', 'first_name', 'last_name']

    @display(description="Полное имя", ordering="first_name")
    def display_full_name(self, obj):
        return obj.get_full_name() or obj.username

    @display(description="Тип", ordering="profile__user_type")
    def display_user_type(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_user_type_display()
        return "—"

    @display(description="Активен", boolean=True)
    def display_is_active(self, obj):
        return obj.is_active


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ['display_user', 'user_type', 'phone', 'display_has_photo', 'offers_home_service']
    list_filter = ['user_type', 'offers_home_service']
    search_fields = ['user__username', 'user__email', 'phone', 'telegram', 'whatsapp']
    readonly_fields = ['location_updated_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'user_type', 'phone', 'photo')
        }),
        ('Контакты', {
            'fields': ('whatsapp', 'telegram')
        }),
        ('Адрес и локация', {
            'fields': ('address', 'latitude', 'longitude', 'location_updated_at')
        }),
        ('Для барберов', {
            'fields': ('bio', 'working_hours_from', 'working_hours_to', 'working_days',
                       'offers_home_service', 'specialization'),
            'classes': ('collapse',)
        })
    )

    @display(description="Пользователь", ordering="user__username")
    def display_user(self, obj):
        return f"{obj.full_name} ({obj.user.email})"

    @display(description="Фото", boolean=True)
    def display_has_photo(self, obj):
        return bool(obj.photo)