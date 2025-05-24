from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    USER_TYPE_CHOICES = (
        ('client', 'Клиент'),
        ('barber', 'Барбер'),
    )

    WORKING_DAYS_CHOICES = [
        ('Пн', 'Понедельник'),
        ('Вт', 'Вторник'),
        ('Ср', 'Среда'),
        ('Чт', 'Четверг'),
        ('Пт', 'Пятница'),
        ('Сб', 'Суббота'),
        ('Вс', 'Воскресенье'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='client',
        verbose_name='Тип пользователя'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Телефон'
    )
    photo = models.ImageField(
        upload_to='profile_photos/',
        blank=True,
        null=True,
        verbose_name='Фото профиля'
    )
    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='WhatsApp',
        help_text='Номер WhatsApp для связи с клиентами'
    )
    telegram = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Telegram',
        help_text='Username в Telegram без @'
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name='Адрес'
    )
    offers_home_service = models.BooleanField(
        default=False,
        verbose_name='Выезд на дом',
        help_text='Предлагает ли барбер услуги с выездом на дом'
    )
    bio = models.TextField(
        blank=True,
        null=True,
        verbose_name='О себе'
    )
    working_hours_from = models.TimeField(
        default='09:00',
        verbose_name='Начало работы'
    )
    working_hours_to = models.TimeField(
        default='18:00',
        verbose_name='Конец работы'
    )
    working_days = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Рабочие дни'
    )
    latitude = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Широта'
    )
    longitude = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Долгота'
    )
    location_updated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Местоположение обновлено'
    )
    specialization = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Специализация'
    )

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
        ordering = ['-user__date_joined']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_user_type_display()}"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def is_barber(self):
        return self.user_type == 'barber'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()