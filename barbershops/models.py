from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Barbershop(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_barbershops',
        verbose_name='Владелец'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название'
    )
    logo = models.ImageField(
        upload_to='barbershops/logos/',
        blank=True,
        null=True,
        verbose_name='Логотип'
    )
    description = models.TextField(
        verbose_name='Описание'
    )
    address = models.TextField(
        verbose_name='Адрес'
    )
    latitude = models.FloatField(
        verbose_name='Широта',
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.FloatField(
        verbose_name='Долгота',
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    phone = models.CharField(
        max_length=20,
        verbose_name='Телефон'
    )
    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='WhatsApp'
    )
    telegram = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Telegram'
    )
    instagram = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Instagram'
    )
    working_hours_from = models.TimeField(
        default='09:00',
        verbose_name='Начало работы'
    )
    working_hours_to = models.TimeField(
        default='21:00',
        verbose_name='Конец работы'
    )
    working_days = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Рабочие дни'
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Проверен'
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
        verbose_name = 'Барбершоп'
        verbose_name_plural = 'Барбершопы'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def rating(self):
        """Средний рейтинг барбершопа на основе рейтингов барберов"""
        from profiles.models import Review
        reviews = Review.objects.filter(barber__barbershop_staff__barbershop=self)
        if reviews.exists():
            return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0

    @property
    def review_count(self):
        """Количество отзывов для барберов барбершопа"""
        from profiles.models import Review
        return Review.objects.filter(barber__barbershop_staff__barbershop=self).count()


class BarbershopPhoto(models.Model):
    barbershop = models.ForeignKey(
        Barbershop,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name='Барбершоп'
    )
    photo = models.ImageField(
        upload_to='barbershops/photos/',
        verbose_name='Фото'
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
        verbose_name = 'Фото барбершопа'
        verbose_name_plural = 'Фото барбершопов'
        ordering = ['order', '-uploaded_at']

    def __str__(self):
        return f"Фото {self.barbershop.name}"


class BarbershopStaff(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Владелец'),
        ('manager', 'Менеджер'),
        ('barber', 'Барбер'),
    ]

    barbershop = models.ForeignKey(
        Barbershop,
        on_delete=models.CASCADE,
        related_name='staff',
        verbose_name='Барбершоп'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='barbershop_staff',
        verbose_name='Сотрудник'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='barber',
        verbose_name='Роль'
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата присоединения'
    )

    class Meta:
        verbose_name = 'Сотрудник барбершопа'
        verbose_name_plural = 'Сотрудники барбершопов'
        unique_together = ['barbershop', 'user']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.barbershop.name}"