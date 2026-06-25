from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.db import models
from django.utils.html import format_html, mark_safe

from .models import (
    UserSession, Video, VideoProgress,
    RoadSign, Category, TestQuestion, TestAnswer,
    TestResult, UserTestAnswer, Book,
    UserSubscription, PaymentRequest,
    PaymentCard, Comment, SiteSettings, ChatMessage, OTP,
)


# ==================== FOYDALANUVCHILAR ====================

class UserSessionInline(admin.StackedInline):
    model = UserSession
    fk_name = 'user'
    can_delete = False
    extra = 0
    fields = ['role', 'created_by', 'device_id', 'last_login_ip', 'created_at', 'updated_at']
    readonly_fields = ['device_id', 'last_login_ip', 'created_at', 'updated_at']
    verbose_name = "Sessiya va rol"
    verbose_name_plural = "Sessiya va rol"


class UserSubscriptionInline(admin.StackedInline):
    model = UserSubscription
    can_delete = False
    extra = 0
    fields = ['is_active', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    verbose_name = "Obuna"
    verbose_name_plural = "Obuna"


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(DjangoUserAdmin):
    list_display = [
        'username', 'full_name', 'email', 'role_badge', 'subscription_badge',
        'approved_payment_amount', 'purchased_books_count', 'video_progress_count',
        'is_active', 'is_staff', 'date_joined',
    ]
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined', 'session_device__role', 'subscription__is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'session_device__created_by__username']
    list_select_related = ['session_device', 'subscription']
    inlines = [UserSessionInline, UserSubscriptionInline]
    readonly_fields = DjangoUserAdmin.readonly_fields + (
        'role_badge', 'created_by_admin', 'last_login_ip', 'device_id',
        'subscription_badge', 'approved_payment_amount', 'pending_payments_count',
        'purchased_books_list', 'video_progress_summary', 'test_summary',
    )
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Loyha ma'lumotlari", {
            'fields': (
                'role_badge', 'created_by_admin', 'last_login_ip', 'device_id',
                'subscription_badge', 'approved_payment_amount', 'pending_payments_count',
                'purchased_books_list', 'video_progress_summary', 'test_summary',
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session_device', 'subscription')

    def full_name(self, obj):
        return obj.get_full_name() or '—'
    full_name.short_description = "F.I.Sh"

    def role_badge(self, obj):
        try:
            role = obj.session_device.role
        except Exception:
            role = 'user'
        color = '#28a745' if role == 'admin' else '#007bff'
        label = 'Admin' if role == 'admin' else 'Foydalanuvchi'
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', color, label)
    role_badge.short_description = "Rol"

    def created_by_admin(self, obj):
        try:
            admin_user = obj.session_device.created_by
        except Exception:
            admin_user = None
        return admin_user.get_full_name() or admin_user.username if admin_user else '—'
    created_by_admin.short_description = "Qo'shgan admin"

    def last_login_ip(self, obj):
        try:
            return obj.session_device.last_login_ip or '—'
        except Exception:
            return '—'
    last_login_ip.short_description = "Oxirgi IP"

    def device_id(self, obj):
        try:
            return obj.session_device.device_id or '—'
        except Exception:
            return '—'
    device_id.short_description = "Device ID"

    def subscription_badge(self, obj):
        try:
            active = obj.subscription.is_active
        except Exception:
            active = False
        if active:
            return mark_safe('<span style="color:#28a745;font-weight:bold;">&#10004; Faol</span>')
        return mark_safe('<span style="color:#dc3545;">&#10008; Nofaol</span>')
    subscription_badge.short_description = "Obuna"

    def approved_payment_amount(self, obj):
        total = PaymentRequest.objects.filter(user=obj, status='approved').aggregate(total=models.Sum('amount'))['total'] or 0
        return f"{total:,} so'm"
    approved_payment_amount.short_description = "Tasdiqlangan to'lov"

    def pending_payments_count(self, obj):
        return PaymentRequest.objects.filter(user=obj, status='pending').count()
    pending_payments_count.short_description = "Kutilayotgan to'lovlar"

    def purchased_books_count(self, obj):
        return PaymentRequest.objects.filter(user=obj, status='approved', book__isnull=False).values('book_id').distinct().count()
    purchased_books_count.short_description = "Kitoblar"

    def purchased_books_list(self, obj):
        books = Book.objects.filter(payment_requests__user=obj, payment_requests__status='approved').distinct()
        if not books.exists():
            return '—'
        return format_html('<br>'.join([f"{book.title} ({book.price:,} so'm)" for book in books]))
    purchased_books_list.short_description = "Sotib olingan kitoblar"

    def video_progress_count(self, obj):
        return VideoProgress.objects.filter(user=obj, watched_seconds__gt=0).count()
    video_progress_count.short_description = "Ko'rgan videolar"

    def video_progress_summary(self, obj):
        qs = VideoProgress.objects.filter(user=obj).select_related('video').order_by('-last_watched')[:10]
        if not qs:
            return '—'
        rows = [
            f"{p.video.title}: {p.watched_seconds}s" + (" (tugagan)" if p.is_completed else "")
            for p in qs
        ]
        return format_html('<br>'.join(rows))
    video_progress_summary.short_description = "Video progress"

    def test_summary(self, obj):
        total = TestResult.objects.filter(user=obj).count()
        passed = TestResult.objects.filter(user=obj, passed=True).count()
        return f"{passed}/{total} test o'tgan"
    test_summary.short_description = "Test natijalari"


# ==================== USER SESSION ====================

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'created_by', 'device_id', 'last_login_ip', 'updated_at']
    list_filter = ['role']
    list_editable = ['role']
    search_fields = ['user__username', 'device_id', 'last_login_ip', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25

    def has_add_permission(self, request):
        return False


# ==================== VIDEO ====================

class VideoTestQuestionInline(admin.StackedInline):
    model = TestQuestion
    extra = 0
    show_change_link = True
    fields = ['question_text', 'photo', 'video', 'difficulty', 'order', 'is_active']
    verbose_name = "Test savoli"
    verbose_name_plural = "Video testlari"


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'duration', 'order', 'is_paid', 'is_active', 'thumbnail_preview', 'created_at']
    list_filter = ['is_active', 'is_paid']
    search_fields = ['title', 'title_ru', 'description']
    list_editable = ['order', 'is_paid', 'is_active']
    readonly_fields = ['created_at', 'thumbnail_preview']
    ordering = ['order', 'created_at']
    inlines = [VideoTestQuestionInline]
    list_per_page = 20
    fieldsets = (
        ("Asosiy ma'lumot", {
            'fields': ('title', 'title_ru', 'description', 'description_ru')
        }),
        ("Media", {
            'fields': ('video_file', 'video_url', 'thumbnail', 'thumbnail_preview', 'duration')
        }),
        ("Sozlamalar", {
            'fields': ('order', 'is_paid', 'is_active', 'created_at')
        }),
    )

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="height:50px; border-radius:4px;" />',
                obj.thumbnail.url
            )
        return "—"
    thumbnail_preview.short_description = "Ko'rinish"


@admin.register(VideoProgress)
class VideoProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'watched_seconds', 'is_completed', 'last_watched']
    list_filter = ['is_completed']
    search_fields = ['user__username', 'video__title']
    readonly_fields = ['last_watched']
    list_per_page = 25

    def has_add_permission(self, request):
        return False


# ==================== YO'L BELGILARI ====================

@admin.register(RoadSign)
class RoadSignAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'order', 'is_active', 'sign_image_preview']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'code', 'description']
    list_editable = ['order', 'is_active']
    readonly_fields = ['created_at', 'sign_image_preview']
    ordering = ['category', 'order', 'code']
    list_per_page = 20
    fieldsets = (
        ("Asosiy ma'lumot", {
            'fields': ('category', 'name', 'code', 'description')
        }),
        ("Media", {
            'fields': ('image', 'sign_image_preview')
        }),
        ("Sozlamalar", {
            'fields': ('order', 'is_active', 'created_at')
        }),
    )

    def sign_image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:60px;" />', obj.image.url)
        return "—"
    sign_image_preview.short_description = "Rasm"


# ==================== KATEGORIYA ====================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'name_ru', 'order', 'is_active', 'question_count']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'name_ru']
    list_per_page = 25

    def question_count(self, obj):
        return obj.questions.filter(is_active=True).count()
    question_count.short_description = "Savollar"


# ==================== TEST ====================

class TestAnswerInline(admin.TabularInline):
    model = TestAnswer
    extra = 4
    fields = ['answer_text', 'is_correct', 'order']


@admin.register(TestQuestion)
class TestQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'short_text', 'category', 'lesson_video', 'difficulty', 'order', 'is_active', 'answer_count']
    list_filter = ['category', 'lesson_video', 'difficulty', 'is_active']
    search_fields = ['question_text', 'lesson_video__title', 'category__name']
    list_editable = ['order', 'is_active']
    readonly_fields = ['created_at']
    ordering = ['category', 'order']
    inlines = [TestAnswerInline]
    list_per_page = 20
    fieldsets = (
        ("Savol", {
            'fields': ('category', 'lesson_video', 'question_text', 'photo', 'video')
        }),
        ("Sozlamalar", {
            'fields': ('difficulty', 'order', 'is_active', 'created_at')
        }),
    )

    def short_text(self, obj):
        text = obj.question_text
        return text[:65] + '…' if len(text) > 65 else text
    short_text.short_description = "Savol matni"

    def answer_count(self, obj):
        total = obj.answers.count()
        correct = obj.answers.filter(is_correct=True).count()
        return format_html("{} ta (<b>{}</b> to'g'ri)", total, correct)
    answer_count.short_description = "Javoblar"


@admin.register(TestAnswer)
class TestAnswerAdmin(admin.ModelAdmin):
    list_display = ['question_short', 'answer_text', 'is_correct', 'order']
    list_filter = ['is_correct']
    search_fields = ['answer_text', 'question__question_text']
    list_editable = ['is_correct', 'order']
    list_per_page = 25

    def question_short(self, obj):
        return obj.question.question_text[:55]
    question_short.short_description = "Savol"


class UserTestAnswerInline(admin.TabularInline):
    model = UserTestAnswer
    extra = 0
    readonly_fields = ['question', 'selected_answer', 'is_correct']
    can_delete = False


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'lesson_video', 'total_questions', 'correct_answers',
        'score_percent', 'passed_badge', 'completed_at',
    ]
    list_filter = ['passed', 'lesson_video', 'completed_at']
    search_fields = ['user__username', 'lesson_video__title']
    readonly_fields = [
        'user', 'lesson_video', 'total_questions', 'correct_answers',
        'score_percent', 'passed', 'completed_at',
    ]
    ordering = ['-completed_at']
    inlines = [UserTestAnswerInline]
    list_per_page = 20

    def passed_badge(self, obj):
        if obj.passed:
            return mark_safe('<span style="color:#28a745;font-weight:bold;">&#10004; O\'tdi</span>')
        return mark_safe('<span style="color:#dc3545;">&#10008; O\'tmadi</span>')
    passed_badge.short_description = "Natija"

    def has_add_permission(self, request):
        return False


# ==================== KITOBLAR ====================

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'year', 'price', 'pages', 'order', 'is_active', 'book_cover_preview', 'created_at']
    list_filter = ['is_active', 'year']
    search_fields = ['title', 'title_ru', 'description']
    list_editable = ['order', 'is_active', 'price']
    readonly_fields = ['created_at', 'book_cover_preview']
    ordering = ['order', 'created_at']
    list_per_page = 20
    fieldsets = (
        ("Asosiy ma'lumot", {
            'fields': ('title', 'title_ru', 'description', 'description_ru')
        }),
        ("Media", {
            'fields': ('image', 'book_cover_preview', 'file')
        }),
        ("Kitob ma'lumotlari", {
            'fields': ('price', 'year', 'pages')
        }),
        ("Sozlamalar", {
            'fields': ('order', 'is_active', 'created_at')
        }),
    )

    def book_cover_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:60px; border-radius:4px;" />', obj.image.url)
        return "—"
    book_cover_preview.short_description = "Muqova"


# ==================== OBUNA ====================

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'subscription_active', 'created_at']
    list_editable = []
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25

    def subscription_active(self, obj):
        if obj.is_active:
            return mark_safe('<span style="color:#28a745;font-weight:bold;">&#10004; Faol</span>')
        return mark_safe('<span style="color:#dc3545;">&#10008; Nofaol</span>')
    subscription_active.short_description = "Holati"


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'payment_type', 'book', 'amount', 'status_badge', 'reviewed_by', 'created_at']
    list_filter = ['status', 'payment_type', 'book', 'created_at']
    search_fields = ['user__username', 'book__title']
    readonly_fields = ['user', 'payment_type', 'book', 'amount', 'receipt', 'comment', 'created_at', 'reviewed_at', 'receipt_preview']
    ordering = ['-created_at']
    list_per_page = 25
    fieldsets = (
        ("Foydalanuvchi", {
            'fields': ('user', 'payment_type', 'book', 'amount', 'comment', 'receipt', 'receipt_preview', 'created_at')
        }),
        ("Admin tekshiruvi", {
            'fields': ('status', 'admin_note', 'reviewed_by', 'reviewed_at')
        }),
    )

    def status_badge(self, obj):
        colors = {'pending': '#f39c12', 'approved': '#28a745', 'rejected': '#dc3545'}
        color = colors.get(obj.status, '#888')
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Holat"

    def receipt_preview(self, obj):
        if obj.receipt:
            return format_html('<img src="{}" style="max-height:200px; border-radius:4px;" />', obj.receipt.url)
        return "—"
    receipt_preview.short_description = "Chek rasmi"


# ==================== CHAT ====================

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display  = ['user', 'video', 'short_text', 'is_active', 'created_at']
    list_filter   = ['is_active', 'video', 'created_at']
    list_editable = ['is_active']
    search_fields = ['user__username', 'text', 'video__title']
    readonly_fields = ['user', 'video', 'created_at']
    list_per_page = 30

    def short_text(self, obj):
        return obj.text[:70] + '…' if len(obj.text) > 70 else obj.text
    short_text.short_description = "Xabar"

    def has_add_permission(self, request):
        return False


# ==================== TO'LOV KARTASI ====================

@admin.register(PaymentCard)
class PaymentCardAdmin(admin.ModelAdmin):
    list_display  = ['name', 'card_number', 'course_price', 'is_active']
    list_editable = ['course_price', 'is_active']
    search_fields = ['name', 'card_number']
    list_per_page = 25


# ==================== IZOHLAR ====================

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = ['user', 'short_text', 'is_active', 'created_at']
    list_filter   = ['is_active', 'created_at']
    list_editable = ['is_active']
    search_fields = ['user__username', 'text']
    readonly_fields = ['user', 'created_at']
    list_per_page = 25

    def short_text(self, obj):
        return obj.text[:80] + '…' if len(obj.text) > 80 else obj.text
    short_text.short_description = "Izoh"

    def has_add_permission(self, request):
        return False


# ==================== SAYT SOZLAMALARI ====================

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Aloqa ma'lumotlari", {
            'fields': ('phone', 'email', 'telegram_url', 'address', 'working_hours')
        }),
        ("Xarita koordinatalari", {
            'fields': ('latitude', 'longitude')
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ==================== OTP ====================

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'code', 'is_verified', 'is_expired_status', 'created_at', 'expires_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['email', 'code']
    readonly_fields = ['created_at', 'expires_at']
    list_per_page = 25

    def is_expired_status(self, obj):
        if obj.is_expired():
            return mark_safe('<span style="color:#dc3545;font-weight:bold;">Tugagan</span>')
        return mark_safe('<span style="color:#28a745;font-weight:bold;">Faol</span>')
    is_expired_status.short_description = "Holati"
