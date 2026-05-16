from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Video, VideoProgress, RoadSign, UserSession,
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


class VideoProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoProgress
        fields = ['video', 'watched_seconds', 'is_completed', 'last_watched']


class VideoSerializer(serializers.ModelSerializer):
    user_progress = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    has_test = serializers.SerializerMethodField()
    test_passed = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            'id', 'title', 'description', 'thumbnail',
            'duration', 'order', 'youtube_url',
            'video_url', 'user_progress',
            'has_test', 'test_passed',
        ]

    def get_video_url(self, obj):
        if obj.video_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/api/videos/{obj.id}/stream/')
        return None

    def get_user_progress(self, obj):
        request = self.context.get('request')
        if not (request and request.user.is_authenticated):
            return None
        if hasattr(obj, '_user_progress_cache'):
            cache = obj._user_progress_cache
            return VideoProgressSerializer(cache[0]).data if cache else None
        try:
            progress = VideoProgress.objects.get(user=request.user, video=obj)
            return VideoProgressSerializer(progress).data
        except VideoProgress.DoesNotExist:
            return None

    def get_has_test(self, obj):
        if hasattr(obj, '_active_test_questions_cache'):
            return len(obj._active_test_questions_cache) > 0
        return obj.test_questions.filter(is_active=True).exists()

    def get_test_passed(self, obj):
        request = self.context.get('request')
        if not (request and request.user.is_authenticated):
            return False
        if hasattr(obj, '_passed_test_results_cache'):
            return len(obj._passed_test_results_cache) > 0
        return obj.test_results.filter(user=request.user, passed=True).exists()


class VideoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = [
            'id', 'title', 'title_ru', 'description', 'description_ru',
            'video_file', 'youtube_url', 'thumbnail',
            'duration', 'order', 'is_active'
        ]
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
    answers = TestAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = TestQuestion
        fields = ['id', 'question_text', 'photo', 'video', 'difficulty', 'answers']


class TestQuestionDetailSerializer(serializers.ModelSerializer):
    answers = TestAnswerWithCorrectSerializer(many=True, read_only=True)

    class Meta:
        model = TestQuestion
        fields = ['id', 'question_text', 'photo', 'video', 'difficulty', 'order', 'is_active', 'answers']


class TestQuestionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestQuestion
        fields = ['id', 'lesson_video', 'question_text', 'photo', 'video', 'difficulty', 'order', 'is_active']


class TestAnswerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAnswer
        fields = ['id', 'question', 'answer_text', 'is_correct', 'order']


class UserTestAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    selected_answer_text = serializers.CharField(
        source='selected_answer.answer_text', read_only=True, allow_null=True
    )
    correct_answer_text = serializers.SerializerMethodField()

    class Meta:
        model = UserTestAnswer
        fields = ['id', 'question_text', 'selected_answer_text', 'correct_answer_text', 'is_correct']

    def get_correct_answer_text(self, obj):
        correct = obj.question.answers.filter(is_correct=True).first()
        return correct.answer_text if correct else None


class TestResultSerializer(serializers.ModelSerializer):
    user_answers = UserTestAnswerSerializer(many=True, read_only=True)
    video_title = serializers.CharField(source='lesson_video.title', read_only=True)

    class Meta:
        model = TestResult
        fields = [
            'id', 'lesson_video', 'video_title',
            'total_questions', 'correct_answers', 'score_percent', 'passed',
            'completed_at', 'user_answers',
        ]


class TestResultListSerializer(serializers.ModelSerializer):
    video_title = serializers.CharField(source='lesson_video.title', read_only=True)

    class Meta:
        model = TestResult
        fields = [
            'id', 'lesson_video', 'video_title',
            'total_questions', 'correct_answers', 'score_percent', 'passed', 'completed_at',
        ]


# ==================== BULK TEST YARATISH ====================

class AnswerInputSerializer(serializers.Serializer):
    answer_text = serializers.CharField(max_length=500)
    is_correct = serializers.BooleanField(default=False)
    order = serializers.IntegerField(default=0, min_value=0)


class QuestionInputSerializer(serializers.Serializer):
    question_text = serializers.CharField()
    difficulty = serializers.ChoiceField(
        choices=['easy', 'medium', 'hard'], default='medium'
    )
    order = serializers.IntegerField(default=0, min_value=0)
    answers = AnswerInputSerializer(many=True)

    def validate_answers(self, value):
        if len(value) < 2:
            raise serializers.ValidationError(
                "Har bir savolda kamida 2 ta javob bo'lishi kerak."
            )
        correct_count = sum(1 for a in value if a.get('is_correct'))
        if correct_count == 0:
            raise serializers.ValidationError(
                "Kamida bitta to'g'ri javob belgilanishi kerak."
            )
        if correct_count > 1:
            raise serializers.ValidationError(
                "Faqat bitta to'g'ri javob bo'lishi mumkin."
            )
        return value


class BulkQuestionCreateSerializer(serializers.Serializer):
    lesson_video = serializers.PrimaryKeyRelatedField(
        queryset=Video.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        help_text="Video ID (ixtiyoriy). Ko'rsatilmasa, umumiy test savoli bo'ladi.",
    )
    questions = QuestionInputSerializer(many=True)

    def validate_questions(self, value):
        if not value:
            raise serializers.ValidationError("Kamida bitta savol bo'lishi kerak.")
        return value


class SubmitTestSerializer(serializers.Serializer):
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
