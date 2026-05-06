from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Category, Video, VideoProgress, RoadSign, UserSession,
    TestQuestion, TestAnswer, TestResult, UserTestAnswer
)


# ==================== INLINE ====================

class VideoInline(admin.TabularInline):
    model = Video
    extra = 0
    fields = ['title', 'order', 'duration', 'is_active', 'thumbnail']
    show_change_link = True


class UserSessionInline(admin.StackedInline):
    model = UserSession
    can_delete = False
    verbose_name = "Qurilma Sessiyasi"
    fields = ['device_id', 'last_login_ip', 'updated_at']
    readonly_fields = ['device_id', 'last_login_ip', 'updated_at']


# ==================== ADMIN CLASSLAR ====================

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_id', 'last_login_ip', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['user__username', 'device_id', 'last_login_ip']
    readonly_fields = ['created_at', 'updated_at']

    def has_add_permission(self, request):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'video_count', 'created_at']
    list_editable = ['order']
    search_fields = ['name']
    inlines = [VideoInline]

    def video_count(self, obj):
        return obj.videos.count()
    video_count.short_description = "Videolar soni"


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'duration', 'order', 'is_active', 'created_at']
    list_filter = ['category', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('category', 'title', 'description', 'order', 'is_active')
        }),
        ('Media', {
            'fields': ('video_file', 'youtube_url', 'thumbnail', 'duration')
        }),
        ('Sana', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(VideoProgress)
class VideoProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'watched_seconds', 'is_completed', 'last_watched']
    list_filter = ['is_completed', 'last_watched']
    search_fields = ['user__username', 'video__title']
    readonly_fields = ['last_watched']

    def has_add_permission(self, request):
        return False


@admin.register(RoadSign)
class RoadSignAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'order', 'is_active']
    list_filter = ['category', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'code', 'description']
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('category', 'code', 'name', 'description', 'order', 'is_active')
        }),
        ('Rasm', {
            'fields': ('image',)
        }),
    )


# User admin ni kengaytirish
class CustomUserAdmin(BaseUserAdmin):
    inlines = list(BaseUserAdmin.inlines) + [UserSessionInline]
    list_display = ['username', 'first_name', 'last_name', 'email', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined']

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return (
                (None, {'fields': ('username', 'password1', 'password2')}),
                ('Shaxsiy ma\'lumotlar', {'fields': ('first_name', 'last_name', 'email')}),
                ('Ruxsatlar', {'fields': ('is_active',)}),
            )
        return super().get_fieldsets(request, obj)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Admin panel sarlavhalari
admin.site.site_header = "Haydovchilik Maktabi Admin"
admin.site.site_title = "Haydovchilik Maktabi"
admin.site.index_title = "Boshqaruv Paneli"


# ==================== TEST ====================

class TestAnswerInline(admin.TabularInline):
    model = TestAnswer
    extra = 1
    fields = ['answer_text', 'is_correct', 'order']


@admin.register(TestQuestion)
class TestQuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'category', 'difficulty', 'order', 'is_active']
    list_filter = ['category', 'difficulty', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['question_text']
    inlines = [TestAnswerInline]
    fieldsets = (
        ('Savol', {
            'fields': ('category', 'question_text', 'difficulty', 'order', 'is_active')
        }),
    )


@admin.register(TestAnswer)
class TestAnswerAdmin(admin.ModelAdmin):
    list_display = ['answer_text', 'question', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__category']
    list_editable = ['order', 'is_correct']
    search_fields = ['answer_text', 'question__question_text']


class UserTestAnswerInline(admin.TabularInline):
    model = UserTestAnswer
    extra = 0
    can_delete = False
    readonly_fields = ['question', 'selected_answer', 'is_correct']
    fields = ['question', 'selected_answer', 'is_correct']


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'score_percent', 'passed', 'completed_at']
    list_filter = ['category', 'passed', 'completed_at']
    search_fields = ['user__username', 'category__name']
    readonly_fields = ['user', 'category', 'total_questions', 'correct_answers', 'score_percent', 'passed', 'completed_at']
    inlines = [UserTestAnswerInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(UserTestAnswer)
class UserTestAnswerAdmin(admin.ModelAdmin):
    list_display = ['test_result', 'question', 'selected_answer', 'is_correct']
    list_filter = ['is_correct', 'test_result__category']
    search_fields = ['test_result__user__username', 'question__question_text']
    readonly_fields = ['test_result', 'question', 'selected_answer', 'is_correct']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
