from django.db import models
from django.contrib.auth.models import User


class Service(models.Model):
    barber = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    title = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration = models.IntegerField(help_text="Продолжительность в минутах", default=30)
    type = models.CharField(max_length=50)
    length = models.CharField(max_length=20, choices=[
        ('short', 'Короткие'),
        ('medium', 'Средние'),
        ('long', 'Длинные'),
    ])
    style = models.CharField(max_length=50)
    location = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    views = models.IntegerField(default=0)  # Добавляем счетчик просмотров
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.barber.username}"

    class Meta:
        ordering = ['-views', '-created_at']  # Сортировка по популярности


class ServiceImage(models.Model):
    """Модель для хранения нескольких изображений услуги"""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='services/')
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-uploaded_at']


class ServiceView(models.Model):
    """Модель для отслеживания просмотров"""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='service_views')
    viewer_ip = models.GenericIPAddressField()
    session_key = models.CharField(max_length=40, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('service', 'viewer_ip', 'session_key')