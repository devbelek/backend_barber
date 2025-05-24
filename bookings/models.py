from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from services.models import Service
import datetime


class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждено'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
    )

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='client_bookings',
        verbose_name='Клиент'
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Услуга'
    )
    date = models.DateField(
        verbose_name='Дата'
    )
    time = models.TimeField(
        verbose_name='Время'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Примечания'
    )
    client_name_contact = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Имя клиента (контакт)'
    )
    client_phone_contact = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Телефон клиента (контакт)'
    )

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-date', '-time']
        unique_together = ['service', 'date', 'time']

    def __str__(self):
        return f"{self.client_name} - {self.service.title} - {self.date} {self.time}"

    @property
    def client_name(self):
        if self.client_name_contact:
            return self.client_name_contact
        return self.client.get_full_name() or self.client.username

    @property
    def client_phone(self):
        if self.client_phone_contact:
            return self.client_phone_contact
        if hasattr(self.client, 'profile'):
            return self.client.profile.phone
        return None

    def clean(self):
        # Проверка, что дата не в прошлом
        if self.date < timezone.now().date():
            raise ValidationError('Нельзя создать бронирование на прошедшую дату')

        # Проверка рабочего времени барбера
        if hasattr(self.service.barber, 'profile'):
            profile = self.service.barber.profile
            if self.time < profile.working_hours_from or self.time > profile.working_hours_to:
                raise ValidationError('Время бронирования вне рабочих часов барбера')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)