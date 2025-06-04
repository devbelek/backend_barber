from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class BarbershopApplication(models.Model):
    """Заявка на регистрацию барбершопа"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает рассмотрения'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
    ]

    # Данные заявителя
    applicant_name = models.CharField(
        max_length=200,
        verbose_name='ФИО заявителя'
    )
    applicant_email = models.EmailField(
        verbose_name='Email заявителя'
    )
    applicant_phone = models.CharField(
        max_length=20,
        verbose_name='Телефон заявителя'
    )

    # Данные барбершопа
    barbershop_name = models.CharField(
        max_length=200,
        verbose_name='Название барбершопа'
    )
    barbershop_address = models.TextField(
        verbose_name='Адрес барбершопа'
    )
    barbershop_description = models.TextField(
        verbose_name='Описание барбершопа'
    )

    # Контактные данные барбершопа
    barbershop_phone = models.CharField(
        max_length=20,
        verbose_name='Телефон барбершопа'
    )
    barbershop_whatsapp = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='WhatsApp'
    )
    barbershop_instagram = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Instagram'
    )

    # Дополнительная информация
    barbers_count = models.IntegerField(
        default=1,
        verbose_name='Количество барберов'
    )
    working_experience = models.TextField(
        verbose_name='Опыт работы',
        help_text='Расскажите о вашем опыте в барбер-индустрии'
    )
    additional_info = models.TextField(
        blank=True,
        null=True,
        verbose_name='Дополнительная информация'
    )

    # Статус заявки
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )

    # Связь с созданным барбершопом (после одобрения)
    created_barbershop = models.OneToOneField(
        'Barbershop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='application',
        verbose_name='Созданный барбершоп'
    )

    # Примечания админа
    admin_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Примечания администратора'
    )

    # Даты
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата подачи'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата рассмотрения'
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications',
        verbose_name='Рассмотрел'
    )

    class Meta:
        verbose_name = 'Заявка на барбершоп'
        verbose_name_plural = 'Заявки на барбершопы'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заявка: {self.barbershop_name} ({self.get_status_display()})"

    def approve(self, admin_user):
        """Одобрить заявку и создать барбершоп"""
        if self.status != 'pending':
            raise ValueError('Можно одобрить только ожидающие заявки')

        # Создаем пользователя для владельца
        from django.contrib.auth.models import User
        username = self.applicant_email.split('@')[0]
        if User.objects.filter(username=username).exists():
            username = f"{username}_{User.objects.count()}"

        owner = User.objects.create_user(
            username=username,
            email=self.applicant_email,
            first_name=self.applicant_name.split()[0] if self.applicant_name else '',
            last_name=' '.join(self.applicant_name.split()[1:]) if len(self.applicant_name.split()) > 1 else ''
        )

        # Создаем профиль владельца
        from users.models import UserProfile
        UserProfile.objects.filter(user=owner).update(
            user_type='barber',
            phone=self.applicant_phone
        )

        # Создаем барбершоп
        barbershop = Barbershop.objects.create(
            owner=owner,
            name=self.barbershop_name,
            description=self.barbershop_description,
            address=self.barbershop_address,
            phone=self.barbershop_phone,
            whatsapp=self.barbershop_whatsapp,
            instagram=self.barbershop_instagram,
            latitude=0,  # Позже владелец сможет указать
            longitude=0,  # Позже владелец сможет указать
            is_verified=True  # Уже проверен админом
        )

        # Добавляем владельца как staff
        BarbershopStaff.objects.create(
            barbershop=barbershop,
            user=owner,
            role='owner'
        )

        # Обновляем заявку
        self.status = 'approved'
        self.created_barbershop = barbershop
        self.reviewed_at = timezone.now()
        self.reviewed_by = admin_user
        self.save()

        return barbershop

    def reject(self, admin_user, reason=None):
        """Отклонить заявку"""
        if self.status != 'pending':
            raise ValueError('Можно отклонить только ожидающие заявки')

        self.status = 'rejected'
        self.reviewed_at = timezone.now()
        self.reviewed_by = admin_user
        if reason:
            self.admin_notes = reason
        self.save()


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
        """Средний рейтинг барбершопа на основе отзывов о барбершопе"""
        reviews = self.barbershop_reviews.all()
        if reviews.exists():
            return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0

    @property
    def review_count(self):
        """Количество отзывов о барбершопе"""
        return self.barbershop_reviews.count()

    @property
    def barbers_rating(self):
        """Средний рейтинг барберов барбершопа"""
        from profiles.models import Review
        reviews = Review.objects.filter(barber__barbershop_staff__barbershop=self)
        if reviews.exists():
            return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0


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


class BarbershopReview(models.Model):
    """Отзывы о барбершопах"""
    RATING_CHOICES = [(i, f'{i} звезд{"а" if i == 1 else "ы" if i in [2, 3, 4] else ""}') for i in range(1, 6)]

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='barbershop_reviews',
        verbose_name='Автор'
    )
    barbershop = models.ForeignKey(
        Barbershop,
        on_delete=models.CASCADE,
        related_name='barbershop_reviews',
        verbose_name='Барбершоп'
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        verbose_name='Рейтинг',
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(
        verbose_name='Комментарий'
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
        verbose_name = 'Отзыв о барбершопе'
        verbose_name_plural = 'Отзывы о барбершопах'
        ordering = ['-created_at']
        unique_together = ('author', 'barbershop')

    def __str__(self):
        return f"{self.author.username} → {self.barbershop.name} - {self.rating}★"