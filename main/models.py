from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .storage import BunnyStorage

class UserSession(models.Model):
    ROLE_CHOICES = [
        ('user', 'Foydalanuvchi'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='session_device')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_users',
        verbose_name="Qo'shgan admin",
    )
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


class OTP(models.Model):
    email = models.EmailField(unique=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    user_data = models.JSONField(default=dict, help_text="Temporary user registration data")

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.email} - {self.code}"

    class Meta:
        verbose_name = "OTP"
        verbose_name_plural = "OTPlar"


class Video(models.Model):
    title = models.CharField(max_length=300)
    title_ru = models.CharField(max_length=300, blank=True, null=True)
    description = models.TextField(blank=True,null=True)
    description_ru = models.TextField(blank=True,null=True)
    video_file = models.FileField(upload_to='videos/', blank=True, null=True, storage=BunnyStorage)
    video_url = models.URLField(blank=True, null=True, help_text="YouTube embed URL (ixtiyoriy)")
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    duration = models.CharField(max_length=20, blank=True, help_text="Masalan: 10:30")

    order = models.PositiveIntegerField(default=0)
    is_paid = models.BooleanField(default=False, help_text="Pullik dars bo'lsa True")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videolar"
        ordering = ['order', 'created_at']


class VideoProgress(models.Model):
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

class Category(models.Model):
    name = models.CharField(max_length=200)
    name_ru = models.CharField(max_length=200, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', 'name']


class TestQuestion(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Oson'),
        ('medium', 'O\'rta'),
        ('hard', 'Qiyin'),
    ]

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        related_name='questions',
        null=True, blank=True,
        verbose_name="Kategoriya",
    )
    lesson_video = models.ForeignKey(
        'Video', on_delete=models.CASCADE,
        related_name='test_questions',
        null=True, blank=True,
        verbose_name="Video dars",
    )
    question_text = models.TextField()
    photo = models.ImageField(upload_to='test_questions/', blank=True, null=True)
    video = models.FileField(upload_to='test_questions/', blank=True, null=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.difficulty} - {self.question_text[:50]}"

    class Meta:
        verbose_name = "Test Savoli"
        verbose_name_plural = "Test Savollari"
        ordering = ['order',]


class TestAnswer(models.Model):
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results')
    lesson_video = models.ForeignKey(
        'Video', on_delete=models.SET_NULL,
        related_name='test_results',
        null=True, blank=True,
        verbose_name="Video dars",
    )
    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField()
    score_percent = models.FloatField()
    passed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.score_percent}%)"

    class Meta:
        verbose_name = "Test Natijasi"
        verbose_name_plural = "Test Natijalari"
        ordering = ['-completed_at']


class UserTestAnswer(models.Model):
    test_result = models.ForeignKey(TestResult, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(TestAnswer, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField()

    def __str__(self):
        return f"{self.test_result.user.username} - Q{self.question.id}"

    class Meta:
        verbose_name = "Foydalanuvchi Javob"
        verbose_name_plural = "Foydalanuvchi Javoblari"

class UserSubscription(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — {'Faol' if self.is_active else 'Nofaol'}"

    class Meta:
        verbose_name = "Obuna"
        verbose_name_plural = "Obunalar"


class PaymentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Kutilmoqda'),
        ('approved', 'Tasdiqlandi'),
        ('rejected', 'Rad etildi'),
    ]
    PAYMENT_TYPE_CHOICES = [
        ('subscription', 'Kurs/obuna'),
        ('book', 'Kitob'),
    ]

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_requests')
    payment_type = models.CharField(
        max_length=20, choices=PAYMENT_TYPE_CHOICES, default='subscription',
        help_text="To'lov turi: kurs/obuna yoki kitob"
    )
    book        = models.ForeignKey(
        'Book', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payment_requests', help_text="Kitob uchun to'lov bo'lsa tanlanadi"
    )
    amount      = models.PositiveIntegerField(help_text="To'langan summa (so'mda)")
    receipt     = models.ImageField(upload_to='receipts/', blank=True, null=True, help_text="To'lov cheki rasmi (ixtiyoriy)")
    comment     = models.TextField(blank=True, help_text="Foydalanuvchi izohi (ixtiyoriy)")
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_note  = models.TextField(blank=True, help_text="Admin izohi")
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_payments', verbose_name="Tekshirgan admin"
    )
    reviewed_at     = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.get_payment_type_display()} — {self.amount:,} so'm ({self.get_status_display()})"

    class Meta:
        verbose_name = "To'lov so'rovi"
        verbose_name_plural = "To'lov so'rovlari"
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    models.Q(('book__isnull', False), ('payment_type', 'book')),
                    models.Q(('book__isnull', True), ('payment_type', 'subscription')),
                    _connector='OR',
                ),
                name='payment_type_matches_book',
            ),
        ]


class ChatMessage(models.Model):
    video     = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='chat_messages')
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    text      = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → {self.video.title}: {self.text[:40]}"

    class Meta:
        verbose_name = "Chat xabari"
        verbose_name_plural = "Chat xabarlari"
        ordering = ['created_at']


class PaymentCard(models.Model):
    name         = models.CharField(max_length=200, help_text="Karta egasining ismi")
    card_number  = models.CharField(max_length=19, help_text="Karta raqami: 8600 0000 0000 0000")
    course_price = models.PositiveIntegerField(default=0, help_text="Kurs narxi (so'mda)")
    is_active    = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} — {self.card_number}"

    class Meta:
        verbose_name = "To'lov kartasi"
        verbose_name_plural = "To'lov kartalari"


class Comment(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active  = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}: {self.text[:50]}"

    class Meta:
        verbose_name = "Izoh"
        verbose_name_plural = "Izohlar"
        ordering = ['-created_at']


class SiteSettings(models.Model):
    phone         = models.CharField(max_length=20, blank=True)
    email         = models.EmailField(blank=True)
    telegram_url  = models.URLField(blank=True)
    address       = models.TextField(blank=True)
    working_hours = models.CharField(max_length=100, blank=True, help_text="Masalan: Dushanba–Juma: 09:00–18:00")
    latitude      = models.DecimalField(max_digits=9, decimal_places=6, default=41.2995)
    longitude     = models.DecimalField(max_digits=9, decimal_places=6, default=69.2401)

    def save(self, *args, **kwargs):
        self.pk = 1  # Har doim bitta instance
        super().save(*args, **kwargs)

    def __str__(self):
        return "Sayt sozlamalari"

    class Meta:
        verbose_name = "Sayt sozlamalari"
        verbose_name_plural = "Sayt sozlamalari"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('payment_received', "To'lov keldi"),
        ('payment_approved', "To'lov tasdiqlandi"),
        ('payment_rejected', "To'lov rad etildi"),
        ('general',          'Umumiy'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    type       = models.CharField(max_length=30, choices=TYPE_CHOICES, default='general')
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.title}"

    class Meta:
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        ordering = ['-created_at']


class Book(models.Model):
    title = models.CharField(max_length=200)
    title_ru = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True)
    description_ru = models.TextField(blank=True, null=True)
    price = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='books/', blank=True, null=True)
    file = models.FileField(upload_to='books/')
    year = models.PositiveSmallIntegerField(help_text="Nashr yili, masalan: 2024")
    pages = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Kitob"
        verbose_name_plural = "Kitoblar"
        ordering = ['order', 'created_at']
