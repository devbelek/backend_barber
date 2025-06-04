from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Barbershop, BarbershopStaff, BarbershopPhoto, BarbershopApplication, BarbershopReview


class BarbershopPhotoInline(admin.TabularInline):
    model = BarbershopPhoto
    extra = 1
    fields = ['photo', 'order', 'image_preview']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="100" height="100" />', obj.photo.url)
        return '-'

    image_preview.short_description = 'Превью'


class BarbershopStaffInline(admin.TabularInline):
    model = BarbershopStaff
    extra = 0
    fields = ['user', 'role', 'joined_at']
    readonly_fields = ['joined_at']
    autocomplete_fields = ['user']


@admin.register(Barbershop)
class BarbershopAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'phone', 'address', 'is_verified', 'rating', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['name', 'address', 'phone', 'owner__username', 'owner__email']
    readonly_fields = ['created_at', 'updated_at', 'rating', 'review_count']
    inlines = [BarbershopStaffInline, BarbershopPhotoInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'owner', 'description', 'logo', 'is_verified')
        }),
        ('Контакты', {
            'fields': ('phone', 'whatsapp', 'telegram', 'instagram')
        }),
        ('Адрес и местоположение', {
            'fields': ('address', 'latitude', 'longitude')
        }),
        ('Рабочее время', {
            'fields': ('working_hours_from', 'working_hours_to', 'working_days')
        }),
        ('Статистика', {
            'fields': ('rating', 'review_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def rating(self, obj):
        return f"{obj.rating} ⭐"

    rating.short_description = 'Рейтинг'

    def review_count(self, obj):
        return obj.review_count

    review_count.short_description = 'Количество отзывов'


@admin.register(BarbershopApplication)
class BarbershopApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'barbershop_name', 'applicant_name', 'applicant_email',
        'status_colored', 'created_at', 'application_actions'
    ]
    list_filter = ['status', 'created_at', 'reviewed_at']
    search_fields = [
        'barbershop_name', 'applicant_name', 'applicant_email',
        'barbershop_address', 'barbershop_phone'
    ]
    readonly_fields = [
        'created_at', 'reviewed_at', 'reviewed_by', 'created_barbershop',
        'status_info', 'contact_info', 'barbershop_info'
    ]

    fieldsets = (
        ('Статус заявки', {
            'fields': ('status_info', 'admin_notes')
        }),
        ('Информация о заявителе', {
            'fields': ('contact_info',)
        }),
        ('Информация о барбершопе', {
            'fields': ('barbershop_info',)
        }),
        ('Дополнительная информация', {
            'fields': ('barbers_count', 'working_experience', 'additional_info'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'reviewed_at', 'reviewed_by', 'created_barbershop'),
            'classes': ('collapse',)
        }),
    )

    def status_colored(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )

    status_colored.short_description = 'Статус'

    def status_info(self, obj):
        info = f"<strong>Статус:</strong> {obj.get_status_display()}<br>"
        if obj.reviewed_at:
            info += f"<strong>Рассмотрено:</strong> {obj.reviewed_at.strftime('%d.%m.%Y %H:%M')}<br>"
        if obj.reviewed_by:
            info += f"<strong>Рассмотрел:</strong> {obj.reviewed_by.get_full_name() or obj.reviewed_by.username}<br>"
        if obj.created_barbershop:
            barbershop_url = reverse('admin:barbershops_barbershop_change', args=[obj.created_barbershop.id])
            info += f'<strong>Созданный барбершоп:</strong> <a href="{barbershop_url}">{obj.created_barbershop.name}</a>'
        return mark_safe(info)

    status_info.short_description = 'Информация о статусе'

    def contact_info(self, obj):
        return mark_safe(f"""
        <strong>ФИО:</strong> {obj.applicant_name}<br>
        <strong>Email:</strong> <a href="mailto:{obj.applicant_email}">{obj.applicant_email}</a><br>
        <strong>Телефон:</strong> <a href="tel:{obj.applicant_phone}">{obj.applicant_phone}</a>
        """)

    contact_info.short_description = 'Контактные данные заявителя'

    def barbershop_info(self, obj):
        info = f"""
        <strong>Название:</strong> {obj.barbershop_name}<br>
        <strong>Адрес:</strong> {obj.barbershop_address}<br>
        <strong>Телефон:</strong> {obj.barbershop_phone}<br>
        """
        if obj.barbershop_whatsapp:
            info += f"<strong>WhatsApp:</strong> {obj.barbershop_whatsapp}<br>"
        if obj.barbershop_instagram:
            info += f"<strong>Instagram:</strong> @{obj.barbershop_instagram}<br>"
        info += f"<strong>Описание:</strong><br>{obj.barbershop_description}"
        return mark_safe(info)

    barbershop_info.short_description = 'Информация о барбершопе'

    def application_actions(self, obj):
        if obj.status == 'pending':
            approve_url = reverse('admin:barbershops_barbershopapplication_approve', args=[obj.id])
            reject_url = reverse('admin:barbershops_barbershopapplication_reject', args=[obj.id])
            return format_html(
                '<a class="button" href="{}" style="background-color: green; color: white;">Одобрить</a> '
                '<a class="button" href="{}" style="background-color: red; color: white;">Отклонить</a>',
                approve_url, reject_url
            )
        return '-'

    application_actions.short_description = 'Действия'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/approve/', self.admin_site.admin_view(self.approve_view),
                 name='barbershops_barbershopapplication_approve'),
            path('<int:pk>/reject/', self.admin_site.admin_view(self.reject_view),
                 name='barbershops_barbershopapplication_reject'),
        ]
        return custom_urls + urls

    def approve_view(self, request, pk):
        from django.shortcuts import redirect, get_object_or_404
        from django.contrib import messages

        application = get_object_or_404(BarbershopApplication, pk=pk)

        if request.method == 'POST':
            try:
                barbershop = application.approve(request.user)
                messages.success(request, f'Заявка одобрена. Создан барбершоп "{barbershop.name}"')

                # Отправляем email заявителю
                self._send_approval_email(application, barbershop)

            except ValueError as e:
                messages.error(request, str(e))

            return redirect('admin:barbershops_barbershopapplication_changelist')

        # Показываем страницу подтверждения
        from django.shortcuts import render
        return render(request, 'admin/barbershops/approve_application.html', {
            'application': application,
            'title': f'Одобрить заявку: {application.barbershop_name}'
        })

    def reject_view(self, request, pk):
        from django.shortcuts import redirect, get_object_or_404, render
        from django.contrib import messages

        application = get_object_or_404(BarbershopApplication, pk=pk)

        if request.method == 'POST':
            reason = request.POST.get('reason', '')
            try:
                application.reject(request.user, reason)
                messages.success(request, 'Заявка отклонена')

                # Отправляем email заявителю
                self._send_rejection_email(application, reason)

            except ValueError as e:
                messages.error(request, str(e))

            return redirect('admin:barbershops_barbershopapplication_changelist')

        return render(request, 'admin/barbershops/reject_application.html', {
            'application': application,
            'title': f'Отклонить заявку: {application.barbershop_name}'
        })

    def _send_approval_email(self, application, barbershop):
        # Здесь можно добавить отправку email
        pass

    def _send_rejection_email(self, application, reason):
        # Здесь можно добавить отправку email
        pass

    def has_add_permission(self, request):
        # Заявки создаются только через API
        return False


@admin.register(BarbershopReview)
class BarbershopReviewAdmin(admin.ModelAdmin):
    list_display = ['barbershop', 'author', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['barbershop__name', 'author__username', 'comment']
    readonly_fields = ['created_at', 'updated_at']


admin.site.register(BarbershopStaff)
admin.site.register(BarbershopPhoto)