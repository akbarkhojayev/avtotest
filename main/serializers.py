from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Category, Video, VideoProgress, RoadSign, UserSession,
    TestQuestion, TestAnswer, TestResult, UserTestAnswer
)


# ==================== AUTH ====================

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    device_id = serializers.CharField(help_text="Qurilma identifikatori (browser fingerprint)")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


# ==================== KATEGORIYA ====================

class CategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'order']


class CategoryListSerializer(serializers.ModelSerializer):
    video_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'order', 'video_count']

    def get_video_count(self, obj):
        return obj.videos.filter(is_active=True).count()


class VideoProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoProgress
        fields = ['video', 'watched_seconds', 'is_completed', 'last_watched']


class VideoSerializer(serializers.ModelSerializer):
    user_progress = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            'id', 'title', 'description', 'thumbnail',
            'duration', 'order', 'youtube_url',
            'video_url', 'user_progress'
        ]

    def get_video_url(self, obj):
        if obj.video_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/api/videos/{obj.id}/stream/')
        return None

    def get_user_progress(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                progress = VideoProgress.objects.get(user=request.user, video=obj)
                return VideoProgressSerializer(progress).data
            except VideoProgress.DoesNotExist:
                return None
        return None


class VideoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = [
            'id', 'category', 'title', 'description',
            'video_file', 'youtube_url', 'thumbnail',
            'duration', 'order', 'is_active'
        ]


class CategorySerializer(serializers.ModelSerializer):
    videos = VideoSerializer(many=True, read_only=True)
    video_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'order', 'video_count', 'videos']

    def get_video_count(self, obj):
        return obj.videos.filter(is_active=True).count()


# ==================== YO'L BELGILARI ====================

class RoadSignSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = RoadSign
        fields = [
            'id', 'category', 'category_display', 'name',
            'code', 'description', 'image', 'order'
        ]


class RoadSignWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadSign
        fields = [
            'id', 'category', 'name', 'code',
            'description', 'image', 'order', 'is_active'
        ]


# ==================== PROGRESS ====================

class UpdateProgressSerializer(serializers.Serializer):
    watched_seconds = serializers.IntegerField(min_value=0)
    is_completed = serializers.BooleanField(default=False)


# ==================== TEST ====================

class TestAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAnswer
        fields = ['id', 'answer_text', 'order']


class TestAnswerWithCorrectSerializer(serializers.ModelSerializer):
    """Admin uchun - to'g'ri javob ko'rsatadi"""
    class Meta:
        model = TestAnswer
        fields = ['id', 'answer_text', 'is_correct', 'order']


class TestQuestionSerializer(serializers.ModelSerializer):
    """Foydalanuvchi uchun - to'g'ri javob ko'rsatmaydi"""
    answers = TestAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = TestQuestion
        fields = ['id', 'question_text', 'difficulty', 'answers']


class TestQuestionDetailSerializer(serializers.ModelSerializer):
    """Admin uchun - to'g'ri javob ko'rsatadi"""
    answers = TestAnswerWithCorrectSerializer(many=True, read_only=True)

    class Meta:
        model = TestQuestion
        fields = ['id', 'category', 'question_text', 'difficulty', 'order', 'is_active', 'answers']


class TestQuestionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestQuestion
        fields = ['id', 'category', 'question_text', 'difficulty', 'order', 'is_active']


class TestAnswerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAnswer
        fields = ['id', 'question', 'answer_text', 'is_correct', 'order']


class UserTestAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    selected_answer_text = serializers.CharField(source='selected_answer.answer_text', read_only=True)
    correct_answer_text = serializers.SerializerMethodField()

    class Meta:
        model = UserTestAnswer
        fields = ['id', 'question_text', 'selected_answer_text', 'correct_answer_text', 'is_correct']

    def get_correct_answer_text(self, obj):
        correct = obj.question.answers.filter(is_correct=True).first()
        return correct.answer_text if correct else None


class TestResultSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    user_answers = UserTestAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = TestResult
        fields = [
            'id', 'category_name', 'total_questions',
            'correct_answers', 'score_percent', 'passed',
            'completed_at', 'user_answers'
        ]


class TestResultListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = TestResult
        fields = [
            'id', 'category_name', 'total_questions',
            'correct_answers', 'score_percent', 'passed', 'completed_at'
        ]


class SubmitTestSerializer(serializers.Serializer):
    """Test javoblarini yuborish"""
    answers = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField(),
            help_text='{"question_id": answer_id}'
        )
    )

    def validate_answers(self, value):
        if not value:
            raise serializers.ValidationError("Javoblar bo'sh bo'lishi mumkin emas.")
        return value
