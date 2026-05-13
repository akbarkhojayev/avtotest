from django.contrib import admin
from django.utils.html import format_html

from .models import (
    UserSession, Video, VideoProgress,
    RoadSign, TestQuestion, TestAnswer,
    TestResult, UserTestAnswer,
)


# ==================== USER SESSION ====================

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_id', 'last_login_ip', 'updated_at']
    search_fields = ['user__username', 'device_id', 'last_login_ip']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25

    def has_add_permission(self, request):
        return False


# ==================== VIDEO ====================

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'duration', 'order', 'is_active', 'thumbnail_preview', 'created_at']
    list_filter = ['is_active']
    search_fields = ['title', 'title_ru', 'description']
    list_editable = ['order', 'is_active']
    readonly_fields = ['created_at', 'thumbnail_preview']
    ordering = ['order', 'created_at']
    list_per_page = 20
    fieldsets = (
        ("Asosiy ma'lumot", {
            'fields': ('title', 'title_ru', 'description', 'description_ru')
        }),
        ("Media", {
            'fields': ('video_file', 'youtube_url', 'thumbnail', 'thumbnail_preview', 'duration')
        }),
        ("Sozlamalar", {
            'fields': ('order', 'is_active', 'created_at')
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


# ==================== TEST ====================

class TestAnswerInline(admin.TabularInline):
    model = TestAnswer
    extra = 4
    fields = ['answer_text', 'is_correct', 'order']


@admin.register(TestQuestion)
class TestQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'short_text', 'difficulty', 'order', 'is_active', 'answer_count']
    list_filter = ['difficulty', 'is_active']
    search_fields = ['question_text']
    list_editable = ['order', 'is_active']
    readonly_fields = ['created_at']
    ordering = ['order']
    inlines = [TestAnswerInline]
    list_per_page = 20
    fieldsets = (
        ("Savol", {
            'fields': ('question_text', 'photo', 'video')
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
        'user', 'total_questions', 'correct_answers',
        'score_percent', 'passed_badge', 'completed_at',
    ]
    list_filter = ['passed', 'completed_at']
    search_fields = ['user__username']
    readonly_fields = [
        'user', 'total_questions', 'correct_answers',
        'score_percent', 'passed', 'completed_at',
    ]
    ordering = ['-completed_at']
    inlines = [UserTestAnswerInline]
    list_per_page = 20

    def passed_badge(self, obj):
        if obj.passed:
            return format_html(
                '<span style="color:#28a745;font-weight:bold;">✔ O\'tdi</span>'
            )
        return format_html('<span style="color:#dc3545;">✘ O\'tmadi</span>')
    passed_badge.short_description = "Natija"

    def has_add_permission(self, request):
        return False
