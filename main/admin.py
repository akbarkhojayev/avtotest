from django.contrib import admin
from django.utils.html import format_html, mark_safe

from .models import (
    UserSession, Video, VideoProgress,
    RoadSign, Category, TestQuestion, TestAnswer,
    TestResult, UserTestAnswer, Book,
    UserSubscription, PaymentRequest,
    PaymentCard, Comment, SiteSettings, ChatMessage, OTP,
)


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
    list_display = ['user', 'book', 'amount', 'status_badge', 'reviewed_by', 'created_at']
    list_filter = ['status', 'book', 'created_at']
    search_fields = ['user__username', 'book__title']
    readonly_fields = ['user', 'book', 'amount', 'receipt', 'comment', 'created_at', 'reviewed_at', 'receipt_preview']
    ordering = ['-created_at']
    list_per_page = 25
    fieldsets = (
        ("Foydalanuvchi", {
            'fields': ('user', 'book', 'amount', 'comment', 'receipt', 'receipt_preview', 'created_at')
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
