from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Service(models.Model):
    TYPE_CHOICES = [
        ('classic', 'Классическая'),
        ('fade', 'Фейд'),
        ('undercut', 'Андеркат'),
        ('crop', 'Кроп'),
        ('pompadour', 'Помпадур'),
        ('textured', 'Текстурная'),
    ]

    LENGTH_CHOICES = [
        ('short', 'Короткие'),
        ('medium', 'Средние'),
        ('long', 'Длинные'),
    ]

    STYLE_CHOICES = [
        ('business', 'Деловой'),
        ('casual', 'Повседневный'),
        ('trendy', 'Трендовый'),
        ('vintage', 'Винтажный'),
        ('modern', 'Современный'),
    ]

    barber = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name='Барбер',
        limit_choices_to={'profile__user_type': 'barber'}
    )
    title = models.CharField(
        max_length=100,
        verbose_name='Название'
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Цена',
        validators=[MinValueValidator(0)]
    )
    duration = models.IntegerField(
        help_text="Продолжительность в минутах",
        default=30,
        verbose_name='Длительность',
        validators=[MinValueValidator(15), MaxValueValidator(240)]
    )
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        verbose_name='Тип стрижки'
    )
    length = models.CharField(
        max_length=20,
        choices=LENGTH_CHOICES,
        verbose_name='Длина волос'
    )
    style = models.CharField(
        max_length=50,
        choices=STYLE_CHOICES,
        verbose_name='Стиль'
    )
    location = models.CharField(
        max_length=100,
        verbose_name='Местоположение'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Описание'
    )
    views = models.IntegerField(
        default=0,
        verbose_name='Просмотры'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ['-views', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.barber.get_full_name()}"


class ServiceImage(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Услуга'
    )
    image = models.ImageField(
        upload_to='services/%Y/%m/',
        verbose_name='Изображение'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='Основное изображение'
    )
    order = models.IntegerField(
        default=0,
        verbose_name='Порядок'
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата загрузки'
    )

    class Meta:
        verbose_name = 'Изображение услуги'
        verbose_name_plural = 'Изображения услуг'
        ordering = ['order', '-uploaded_at']

    def __str__(self):
        return f"Изображение для {self.service.title}"

    def save(self, *args, **kwargs):
        # Если это основное изображение, сбросить флаг у других
        if self.is_primary:
            ServiceImage.objects.filter(
                service=self.service,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class ServiceView(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='service_views',
        verbose_name='Услуга'
    )
    viewer_ip = models.GenericIPAddressField(
        verbose_name='IP адрес'
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name='Ключ сессии'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Пользователь'
    )
    viewed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата просмотра'
    )

    class Meta:
        verbose_name = 'Просмотр услуги'
        verbose_name_plural = 'Просмотры услуг'
        unique_together = ('service', 'viewer_ip', 'session_key')
        ordering = ['-viewed_at']

    def __str__(self):
        return f"Просмотр {self.service.title} от {self.viewer_ip}"