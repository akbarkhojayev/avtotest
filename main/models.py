from django.db import models
from django.contrib.auth.models import User


class UserSession(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='session_device')
    device_id = models.CharField(max_length=255, blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    token_jti = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.device_id}"

    class Meta:
        verbose_name = "Foydalanuvchi Sessiyasi"
        verbose_name_plural = "Foydalanuvchi Sessiyalari"


class Category(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', 'name']


class Video(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to='videos/', blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True, help_text="YouTube embed URL (ixtiyoriy)")
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    duration = models.CharField(max_length=20, blank=True, help_text="Masalan: 10:30")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videolar"
        ordering = ['order', 'created_at']


class VideoProgress(models.Model):
    """Foydalanuvchi video ko'rish progressi"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_progress')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='progress')
    watched_seconds = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    last_watched = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.video.title}"

    class Meta:
        verbose_name = "Video Progress"
        verbose_name_plural = "Video Progresslar"
        unique_together = ['user', 'video']


class RoadSign(models.Model):
    SIGN_CATEGORIES = [
        ('warning', 'Ogohlantiruvchi belgilar'),
        ('prohibitory', 'Taqiqlovchi belgilar'),
        ('mandatory', 'Majburiy belgilar'),
        ('informational', 'Axborot belgilari'),
        ('priority', 'Ustunlik belgilari'),
        ('special', 'Maxsus belgilar'),
    ]

    category = models.CharField(max_length=50, choices=SIGN_CATEGORIES)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True, help_text="Masalan: 1.1, 2.5")
    description = models.TextField()
    image = models.ImageField(upload_to='road_signs/')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "Yo'l Belgisi"
        verbose_name_plural = "Yo'l Belgilari"
        ordering = ['category', 'order', 'code']


class TestQuestion(models.Model):
    """Imtixon savollari"""
    DIFFICULTY_CHOICES = [
        ('easy', 'Oson'),
        ('medium', 'O\'rta'),
        ('hard', 'Qiyin'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='test_questions')
    question_text = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category.name} - {self.question_text[:50]}"

    class Meta:
        verbose_name = "Test Savoli"
        verbose_name_plural = "Test Savollari"
        ordering = ['category', 'order']


class TestAnswer(models.Model):
    """Savol variantlari"""
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.question.question_text[:30]} - {self.answer_text[:30]}"

    class Meta:
        verbose_name = "Test Javob"
        verbose_name_plural = "Test Javoblari"
        ordering = ['question', 'order']


class TestResult(models.Model):
    """Foydalanuvchi test natijalari"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='test_results')
    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField()
    score_percent = models.FloatField()
    passed = models.BooleanField(default=False)  # 70% dan yuqori bo'lsa passed
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.category.name} ({self.score_percent}%)"

    class Meta:
        verbose_name = "Test Natijasi"
        verbose_name_plural = "Test Natijalari"
        ordering = ['-completed_at']


class UserTestAnswer(models.Model):
    """Foydalanuvchi javoblarini saqlash"""
    test_result = models.ForeignKey(TestResult, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(TestAnswer, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField()

    def __str__(self):
        return f"{self.test_result.user.username} - Q{self.question.id}"

    class Meta:
        verbose_name = "Foydalanuvchi Javob"
        verbose_name_plural = "Foydalanuvchi Javoblari"
