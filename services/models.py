from django.db import models
from django.contrib.auth.models import User


class Service(models.Model):
    barber = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='services/')
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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.barber.username}"

    class Meta:
        ordering = ['-created_at']