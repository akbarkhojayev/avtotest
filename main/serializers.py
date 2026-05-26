from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Video, VideoProgress, RoadSign, UserSession,
    TestQuestion, TestAnswer, TestResult, UserTestAnswer,
    Book, PaymentRequest, UserSubscription,
)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    device_id = serializers.CharField(help_text="Qurilma identifikatori (browser fingerprint)")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, label="Parolni tasdiqlang")

    class Meta:
        model = User
        fields = ['username', 'password', 'password2', 'first_name', 'last_name', 'email']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'email': {'required': False},
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password2": "Parollar mos kelmaydi."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        UserSession.objects.get_or_create(user=user, defaults={'role': 'user'})
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, required=False, allow_blank=True)
    password2 = serializers.CharField(write_only=True, required=False, allow_blank=True, label="Parolni tasdiqlang")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'password2']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'email': {'required': False},
        }

    def validate(self, data):
        password = data.get('password', '').strip()
        password2 = data.get('password2', '').strip()
        if password or password2:
            if password != password2:
                raise serializers.ValidationError({"password2": "Parollar mos kelmaydi."})
            if len(password) < 6:
                raise serializers.ValidationError({"password": "Parol kamida 6 ta belgidan iborat bo'lishi kerak."})
        return data

    def update(self, instance, validated_data):
        validated_data.pop('password2', None)
        password = validated_data.pop('password', '').strip()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role']

    def get_role(self, obj):
        try:
            return obj.session_device.role
        except Exception:
            return 'user'


class AdminUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role', 'is_active', 'date_joined']
        read_only_fields = ['date_joined']

    def get_role(self, obj):
        try:
            return obj.session_device.role
        except Exception:
            return 'user'


class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=['user', 'admin'], default='user', required=False)

    class Meta:
        model = User
        fields = ['username', 'password', 'first_name', 'last_name', 'email', 'is_active', 'role']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'email': {'required': False},
            'is_active': {'default': True, 'required': False},
        }

    def create(self, validated_data):
        role = validated_data.pop('role', 'user')
        password = validated_data.pop('password')
        if role == 'admin':
            validated_data['is_staff'] = True
        user = User.objects.create_user(password=password, **validated_data)
        UserSession.objects.create(user=user, role=role)
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=['user', 'admin'], required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active', 'password', 'role']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'email': {'required': False},
            'is_active': {'required': False},
        }

    def update(self, instance, validated_data):
        role = validated_data.pop('role', None)
        password = validated_data.pop('password', '').strip()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if role is not None:
            instance.is_staff = (role == 'admin')
            session, _ = UserSession.objects.get_or_create(user=instance)
            session.role = role
            session.save()
        instance.save()
        return instance


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
            'duration', 'order', 'youtube_url', 'is_paid',
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
            'duration', 'order', 'is_paid', 'is_active'
        ]
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'is_paid': {'default': False, 'required': False},
            'order': {'default': 0, 'required': False},
        }

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
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'order': {'default': 0, 'required': False},
            'code': {'required': False},
        }


class UpdateProgressSerializer(serializers.Serializer):
    watched_seconds = serializers.IntegerField(min_value=0)
    is_completed = serializers.BooleanField(default=False)


class TestAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAnswer
        fields = ['id', 'answer_text', 'order']
        ref_name = 'TestAnswerRead'


class TestAnswerWithCorrectSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAnswer
        fields = ['id', 'answer_text', 'is_correct', 'order']
        ref_name = 'TestAnswerWithCorrect'


class TestQuestionSerializer(serializers.ModelSerializer):
    answers = TestAnswerSerializer(many=True, read_only=True)
    lesson_video_title = serializers.CharField(source='lesson_video.title', read_only=True, allow_null=True)

    class Meta:
        model = TestQuestion
        fields = ['id', 'lesson_video', 'lesson_video_title', 'question_text', 'photo', 'video', 'difficulty', 'answers']


class TestQuestionDetailSerializer(serializers.ModelSerializer):
    answers = TestAnswerWithCorrectSerializer(many=True, read_only=True)
    lesson_video_title = serializers.CharField(source='lesson_video.title', read_only=True, allow_null=True)

    class Meta:
        model = TestQuestion
        fields = ['id', 'lesson_video', 'lesson_video_title', 'question_text', 'photo', 'video', 'difficulty', 'order', 'is_active', 'answers']


class TestQuestionWriteSerializer(serializers.ModelSerializer):
    answers = serializers.CharField(
        write_only=True, required=False,
        help_text='JSON string: [{"answer_text":"A","is_correct":false,"order":1},{"answer_text":"B","is_correct":true,"order":2}]'
    )

    class Meta:
        model = TestQuestion
        fields = ['id', 'lesson_video', 'question_text', 'photo', 'video', 'difficulty', 'order', 'is_active', 'answers']
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'order': {'default': 0, 'required': False},
            'difficulty': {'default': 'medium', 'required': False},
        }


class TestAnswerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAnswer
        fields = ['id', 'question', 'answer_text', 'is_correct', 'order']


class AnswerInputSerializer(serializers.Serializer):
    answer_text = serializers.CharField(max_length=500)
    is_correct = serializers.BooleanField(default=False)
    order = serializers.IntegerField(default=0, min_value=0)

    class Meta:
        ref_name = 'AnswerInput'


class TestQuestionWithAnswersWriteSerializer(serializers.ModelSerializer):

    answers = AnswerInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = TestQuestion
        fields = [
            'id', 'lesson_video', 'question_text', 'photo', 'video',
            'difficulty', 'order', 'is_active', 'answers',
        ]
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'order': {'default': 0, 'required': False},
            'difficulty': {'default': 'medium', 'required': False},
        }

    def validate_answers(self, value):
        if not value:
            return value
        correct = sum(1 for a in value if a.get('is_correct'))
        if correct > 1:
            raise serializers.ValidationError(
                "Faqat bitta to'g'ri javob (is_correct: true) bo'lishi mumkin."
            )
        return value

    def create(self, validated_data):
        answers_data = validated_data.pop('answers', [])
        question = TestQuestion.objects.create(**validated_data)
        for i, ans in enumerate(answers_data, start=1):
            TestAnswer.objects.create(
                question=question,
                answer_text=ans['answer_text'],
                is_correct=ans.get('is_correct', False),
                order=ans.get('order', i),
            )
        return question

    def update(self, instance, validated_data):
        validated_data.pop('answers', None)
        return super().update(instance, validated_data)


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


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'title_ru', 'description', 'description_ru',
            'price', 'image', 'file', 'year', 'pages', 'order', 'created_at',
        ]


class BookWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'title_ru', 'description', 'description_ru',
            'price', 'image', 'file', 'year', 'pages', 'order', 'is_active',
        ]
        extra_kwargs = {
            'is_active': {'default': True, 'required': False},
            'order': {'default': 0, 'required': False},
            'price': {'default': 0, 'required': False},
            'pages': {'default': 0, 'required': False},
            'image': {'required': False},
            'title_ru': {'required': False},
            'description': {'required': False},
            'description_ru': {'required': False},
        }


class SubscriptionSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSubscription
        fields = ['id', 'expires_at', 'is_active', 'created_at']


class PaymentRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRequest
        fields = ['id', 'amount', 'receipt', 'comment']
        extra_kwargs = {
            'comment': {'required': False},
        }


class PaymentRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PaymentRequest
        fields = [
            'id', 'amount', 'receipt', 'comment',
            'status', 'status_display', 'admin_note',
            'subscription_days', 'created_at',
        ]


class PaymentRequestAdminSerializer(serializers.ModelSerializer):
    status_display  = serializers.CharField(source='get_status_display', read_only=True)
    username        = serializers.CharField(source='user.username', read_only=True)
    full_name       = serializers.SerializerMethodField()
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True, allow_null=True)

    class Meta:
        model = PaymentRequest
        fields = [
            'id', 'username', 'full_name', 'amount', 'receipt', 'comment',
            'status', 'status_display', 'admin_note', 'subscription_days',
            'reviewed_by_name', 'reviewed_at', 'created_at',
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class PaymentReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    admin_note = serializers.CharField(required=False, allow_blank=True)
    subscription_days = serializers.IntegerField(min_value=1, default=30, required=False)

