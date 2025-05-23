from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class TelegramUser(models.Model):
    """Модель для хранения связи между пользователем Telegram и барбером."""
    barber = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='telegram_account',
        verbose_name=_('Барбер')
    )
    username = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_('Username в Telegram')
    )
    chat_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('ID чата в Telegram')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активен')
    )
    connected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата подключения')
    )
    last_notification = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Дата последнего уведомления')
    )

    class Meta:
        verbose_name = _('Telegram пользователь')
        verbose_name_plural = _('Telegram пользователи')

    def __str__(self):
        return f"{self.barber.get_full_name()} (@{self.username})"


class Notification(models.Model):
    """Модель для хранения уведомлений."""
    TYPE_CHOICES = (
        ('booking_new', _('Новое бронирование')),
        ('booking_confirmed', _('Бронирование подтверждено')),
        ('booking_cancelled', _('Бронирование отменено')),
        ('booking_reminder', _('Напоминание о бронировании')),
        ('system', _('Системное уведомление')),
    )

    STATUS_CHOICES = (
        ('pending', _('Ожидает отправки')),
        ('sent', _('Отправлено')),
        ('failed', _('Ошибка отправки')),
        ('read', _('Прочитано')),
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Получатель')
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name=_('Тип уведомления')
    )
    title = models.CharField(
        max_length=100,
        verbose_name=_('Заголовок')
    )
    content = models.TextField(
        verbose_name=_('Содержание')
    )
    related_object_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('ID связанного объекта')
    )
    related_object_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('Тип связанного объекта')
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Статус')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Создано')
    )
    sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Отправлено')
    )
    read_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Прочитано')
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Уведомление')
        verbose_name_plural = _('Уведомления')

    def __str__(self):
        return f"{self.get_type_display()} - {self.recipient.username}"


class TelegramAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='telegram_account_data')
    username = models.CharField(max_length=100, unique=True)
    chat_id = models.BigIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"@{self.username} - {self.user.username}"