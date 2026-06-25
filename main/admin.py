from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, mark_safe

from .models import (
    UserSession, Video, VideoProgress,
    RoadSign, Category, TestQuestion, TestAnswer,
    TestResult, UserTestAnswer, Book,
    UserSubscription, PaymentRequest,
    PaymentCard, Comment, SiteSettings, ChatMessage, OTP,
)


def admin_object_link(obj, label=None):
    if not obj:
        return "-"
    url = reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
    return format_html('<a href="{}">{}</a>', url, label or str(obj))


def external_link(url, label="Ochish"):
    if not url:
        return "-"
    return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', url, label)


def money(value):
    return f"{value or 0:,} so'm"


def bool_badge(active, true_label="Faol", false_label="Nofaol"):
    if active:
        return format_html('<span style="color:#28a745;font-weight:bold;">&#10004; {}</span>', true_label)
    return format_html('<span style="color:#dc3545;font-weight:bold;">&#10008; {}</span>', false_label)


def payment_type_badge_value(payment_type):
    if payment_type == 'book':
        return mark_safe('<span style="color:#6f42c1;font-weight:bold;">Kitob</span>')
    return mark_safe('<span style="color:#007bff;font-weight:bold;">Kurs/obuna</span>')


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
    list_display = [
        'id', 'title', 'duration', 'order', 'access_badge', 'source_badge',
        'api_video_link', 'bunny_file_link', 'progress_count', 'test_count',
        'is_active', 'thumbnail_preview', 'created_at',
    ]
    list_filter = ['is_active', 'is_paid']
    search_fields = ['title', 'title_ru', 'description', 'video_url']
    list_editable = ['order', 'is_active']
    readonly_fields = ['created_at', 'thumbnail_preview', 'api_video_link', 'bunny_file_link', 'thumbnail_link', 'progress_count', 'test_count']
    ordering = ['order', 'created_at']
    inlines = [VideoTestQuestionInline]
    list_per_page = 20
    fieldsets = (
        ("Asosiy ma'lumot", {
            'fields': ('title', 'title_ru', 'description', 'description_ru')
        }),
        ("Media", {
            'fields': (
                'video_file', 'bunny_file_link', 'video_url', 'api_video_link',
                'thumbnail', 'thumbnail_preview', 'thumbnail_link', 'duration',
            )
        }),
        ("Sozlamalar", {
            'fields': ('order', 'is_paid', 'is_active', 'progress_count', 'test_count', 'created_at')
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


    def access_badge(self, obj):
        return bool_badge(obj.is_paid, "Pullik", "Bepul")
    access_badge.short_description = "Kirish"

    def source_badge(self, obj):
        if obj.video_file:
            return mark_safe('<span style="color:#28a745;font-weight:bold;">Bunny/file</span>')
        if obj.video_url:
            return mark_safe('<span style="color:#007bff;font-weight:bold;">URL</span>')
        return mark_safe('<span style="color:#dc3545;font-weight:bold;">Video yoq</span>')
    source_badge.short_description = "Manba"

    def api_video_link(self, obj):
        url = obj.video_url or (obj.video_file.url if obj.video_file else None)
        return external_link(url, "Video link")
    api_video_link.short_description = "API video_url"

    def bunny_file_link(self, obj):
        return external_link(obj.video_file.url if obj.video_file else None, "Bunny/file")
    bunny_file_link.short_description = "Yuklangan file"

    def thumbnail_link(self, obj):
        return external_link(obj.thumbnail.url if obj.thumbnail else None, "Thumbnail")
    thumbnail_link.short_description = "Thumbnail link"

    def progress_count(self, obj):
        return obj.progress.count()
    progress_count.short_description = "Progress"

    def test_count(self, obj):
        return obj.test_questions.count()
    test_count.short_description = "Testlar"


@admin.register(VideoProgress)
class VideoProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'video_link', 'watched_seconds', 'progress_badge', 'is_completed', 'last_watched']
    list_filter = ['is_completed', 'last_watched']
    search_fields = ['user__username', 'video__title']
    readonly_fields = ['user', 'video', 'watched_seconds', 'is_completed', 'last_watched']
    list_per_page = 25

    def video_link(self, obj):
        return admin_object_link(obj.video)
    video_link.short_description = "Video"

    def progress_badge(self, obj):
        return bool_badge(obj.is_completed, "Tugagan", "Jarayonda")
    progress_badge.short_description = "Holat"

    def has_add_permission(self, request):
        return False


# ==================== YO'L BELGILARI ====================

@admin.register(RoadSign)
class RoadSignAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'order', 'is_active', 'sign_image_preview']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'code', 'description']
    list_editable = ['order', 'is_active']
    readonly_fields = ['created_at', 'sign_image_preview', 'image_link']
    ordering = ['category', 'order', 'code']
    list_per_page = 20
    fieldsets = (
        ("Asosiy ma'lumot", {
            'fields': ('category', 'name', 'code', 'description')
        }),
        ("Media", {
            'fields': ('image', 'sign_image_preview', 'image_link')
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

    def image_link(self, obj):
        return external_link(obj.image.url if obj.image else None, "Rasm link")
    image_link.short_description = "Rasm URL"


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
    list_display = ['id', 'title', 'year', 'price_display', 'pages', 'buyer_count', 'approved_revenue', 'order', 'is_active', 'book_file_link', 'book_cover_preview', 'created_at']
    list_filter = ['is_active', 'year']
    search_fields = ['title', 'title_ru', 'description']
    list_editable = ['order', 'is_active']
    readonly_fields = ['created_at', 'book_cover_preview', 'book_file_link', 'cover_link', 'buyer_count', 'approved_revenue']
    ordering = ['order', 'created_at']
    list_per_page = 20
    fieldsets = (
        ("Asosiy ma'lumot", {
            'fields': ('title', 'title_ru', 'description', 'description_ru')
        }),
        ("Media", {
            'fields': ('image', 'book_cover_preview', 'cover_link', 'file', 'book_file_link')
        }),
        ("Kitob ma'lumotlari", {
            'fields': ('price', 'year', 'pages', 'buyer_count', 'approved_revenue')
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


    def price_display(self, obj):
        return money(obj.price)
    price_display.short_description = "Narx"

    def book_file_link(self, obj):
        return external_link(obj.file.url if obj.file else None, "PDF/file")
    book_file_link.short_description = "Kitob fayli"

    def cover_link(self, obj):
        return external_link(obj.image.url if obj.image else None, "Muqova link")
    cover_link.short_description = "Muqova URL"

    def buyer_count(self, obj):
        return obj.payment_requests.filter(status='approved', payment_type='book').values('user_id').distinct().count()
    buyer_count.short_description = "Sotib olganlar"

    def approved_revenue(self, obj):
        total = obj.payment_requests.filter(status='approved', payment_type='book').aggregate(total=models.Sum('amount'))['total'] or 0
        return money(total)
    approved_revenue.short_description = "Kitob tushumi"


# ==================== OBUNA ====================

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'subscription_active', 'approved_subscription_amount', 'created_at', 'updated_at']
    list_editable = []
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'approved_subscription_amount']
    list_per_page = 25

    def user_link(self, obj):
        return admin_object_link(obj.user)
    user_link.short_description = "Foydalanuvchi"

    def subscription_active(self, obj):
        return bool_badge(obj.is_active, "Faol", "Nofaol")
    subscription_active.short_description = "Holati"

    def approved_subscription_amount(self, obj):
        total = PaymentRequest.objects.filter(
            user=obj.user, payment_type='subscription', status='approved'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        return money(total)
    approved_subscription_amount.short_description = "Obuna to'lovlari"


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_link', 'payment_type_badge', 'payment_target', 'amount_display',
        'status_badge', 'receipt_link', 'reviewed_by', 'created_at',
    ]
    list_filter = ['status', 'payment_type', 'book', 'created_at', 'reviewed_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'book__title', 'comment', 'admin_note']
    readonly_fields = [
        'user', 'payment_type', 'book', 'amount', 'amount_display', 'receipt',
        'receipt_preview', 'receipt_link', 'comment', 'created_at', 'reviewed_at',
        'reviewed_by', 'payment_target',
    ]
    ordering = ['-created_at']
    list_per_page = 25
    actions = ['approve_selected_payments', 'reject_selected_payments']
    fieldsets = (
        ("To'lov ma'lumotlari", {
            'fields': (
                'user', 'payment_type', 'payment_target', 'book', 'amount', 'amount_display',
                'comment', 'receipt', 'receipt_preview', 'receipt_link', 'created_at',
            )
        }),
        ("Admin tekshiruvi", {
            'fields': ('status', 'admin_note', 'reviewed_by', 'reviewed_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'book', 'reviewed_by')

    def user_link(self, obj):
        return admin_object_link(obj.user)
    user_link.short_description = "Foydalanuvchi"

    def payment_type_badge(self, obj):
        return payment_type_badge_value(obj.payment_type)
    payment_type_badge.short_description = "To'lov turi"

    def payment_target(self, obj):
        if obj.payment_type == 'book':
            return admin_object_link(obj.book, obj.book.title if obj.book else "Kitob o'chirilgan")
        return "Kurs/obuna"
    payment_target.short_description = "Nima uchun"

    def amount_display(self, obj):
        return money(obj.amount)
    amount_display.short_description = "Summa"

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
            return format_html('<img src="{}" style="max-height:220px; border-radius:4px;" />', obj.receipt.url)
        return "-"
    receipt_preview.short_description = "Chek rasmi"

    def receipt_link(self, obj):
        return external_link(obj.receipt.url if obj.receipt else None, "Chek")
    receipt_link.short_description = "Chek link"

    def _apply_approval_effect(self, payment):
        if payment.payment_type == 'subscription':
            sub, _ = UserSubscription.objects.get_or_create(user=payment.user)
            if not sub.is_active:
                sub.is_active = True
                sub.save(update_fields=['is_active', 'updated_at'])

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = PaymentRequest.objects.filter(pk=obj.pk).values_list('status', flat=True).first()
        if change and old_status != obj.status and obj.status in ('approved', 'rejected'):
            obj.reviewed_by = obj.reviewed_by or request.user
            obj.reviewed_at = obj.reviewed_at or timezone.now()
        super().save_model(request, obj, form, change)
        if obj.status == 'approved' and old_status != 'approved':
            self._apply_approval_effect(obj)

    @admin.action(description="Tanlangan pending to'lovlarni tasdiqlash")
    def approve_selected_payments(self, request, queryset):
        approved = 0
        for payment in queryset.select_related('user', 'book').filter(status='pending'):
            payment.status = 'approved'
            payment.reviewed_by = request.user
            payment.reviewed_at = timezone.now()
            payment.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            self._apply_approval_effect(payment)
            approved += 1
        self.message_user(request, f"{approved} ta to'lov tasdiqlandi.")

    @admin.action(description="Tanlangan pending to'lovlarni rad etish")
    def reject_selected_payments(self, request, queryset):
        rejected = queryset.filter(status='pending').update(
            status='rejected', reviewed_by=request.user, reviewed_at=timezone.now()
        )
        self.message_user(request, f"{rejected} ta to'lov rad etildi.")


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
