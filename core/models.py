import uuid
from django.db import models


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.telegram_id})"


class Quest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True, help_text="Широта")
    longitude = models.FloatField(null=True, blank=True, help_text="Долгота")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PromoCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='promocodes')
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.quest.name})"


class UserQuestProgress(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'На проверке'
        APPROVED = 'approved', 'Подтверждено'
        REJECTED = 'rejected', 'Отклонено'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quest_progress')
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='quest_photos/')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)
    admin_comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('user', 'quest')

    def __str__(self):
        return f"{self.user.name} - {self.quest.name} ({self.status})"


class Point(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    text_content = models.TextField(blank=True, null=True)
    audio_file = models.FileField(upload_to='get_audio_path', blank=True, null=True)
    photo = models.ImageField(upload_to='get_photo_path', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_points')
    video_file = models.FileField(upload_to='get_video_path', null=True, blank=True)

    def get_photo_path(self, filename):
        """Генерирует путь для фото"""
        ext = filename.split('.')[-1]
        return f'points/photos/{self.name}.{ext}'

    def get_audio_path(self, filename):
        """Генерирует путь для аудио"""
        ext = filename.split('.')[-1]
        return f'points/audio/{self.name}.{ext}'

    def get_video_path(self, filename):
        """Генерирует путь для видео"""
        ext = filename.split('.')[-1]
        return f'points/videos/{self.name}.{ext}'

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Точка'
        verbose_name_plural = 'Точки'


class Route(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_routes')
    points = models.ManyToManyField(Point, through='RoutePoint')

    def __str__(self):
        return self.name


class RoutePoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    point = models.ForeignKey(Point, on_delete=models.CASCADE)
    order = models.IntegerField()  # Порядок точки в маршруте

    class Meta:
        ordering = ['order']
        unique_together = ('route', 'point')

    def __str__(self):
        return f"{self.point.name} (Маршрут: {self.route.name}, порядок: {self.order})" 