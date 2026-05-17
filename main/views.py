import json
import os
import re
import mimetypes

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import Prefetch
from django.http import QueryDict, StreamingHttpResponse, Http404
from django.shortcuts import get_object_or_404

from rest_framework import status, generics
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import (
    Video, VideoProgress, RoadSign, UserSession,
    TestQuestion, TestAnswer, TestResult, UserTestAnswer,
)
from .serializers import (
    LoginSerializer, UserSerializer, RegisterSerializer, UserUpdateSerializer,
    AdminUserSerializer, AdminUserCreateSerializer, AdminUserUpdateSerializer,
    VideoSerializer, VideoWriteSerializer,
    RoadSignSerializer, RoadSignWriteSerializer,
    UpdateProgressSerializer,
    TestQuestionSerializer, TestQuestionDetailSerializer,
    TestQuestionWriteSerializer, TestQuestionWithAnswersWriteSerializer,
    TestAnswerSerializer, TestAnswerWriteSerializer,
    TestResultSerializer, TestResultListSerializer,
    SubmitTestSerializer, BulkQuestionCreateSerializer,
    BookSerializer, BookWriteSerializer,
)
from .models import Book


# ==================== SWAGGER PARAMETRLAR ====================

_VIDEO_FORM_PARAMS = [
    openapi.Parameter('title',          openapi.IN_FORM, type=openapi.TYPE_STRING,  required=True,  description='Sarlavha (UZ)'),
    openapi.Parameter('title_ru',       openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Sarlavha (RU)'),
    openapi.Parameter('description',    openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Tavsif (UZ)'),
    openapi.Parameter('description_ru', openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Tavsif (RU)'),
    openapi.Parameter('video_file',     openapi.IN_FORM, type=openapi.TYPE_FILE,                    description='Video fayli (mp4)'),
    openapi.Parameter('youtube_url',    openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='YouTube embed URL'),
    openapi.Parameter('thumbnail',      openapi.IN_FORM, type=openapi.TYPE_FILE,                    description='Muqova rasmi'),
    openapi.Parameter('duration',       openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Davomiyligi, masalan: 10:30'),
    openapi.Parameter('order',          openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=0),
    openapi.Parameter('is_active',      openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, default=True),
]

_ROAD_SIGN_FORM_PARAMS = [
    openapi.Parameter('category',    openapi.IN_FORM, type=openapi.TYPE_STRING,  required=True, description='warning | prohibitory | mandatory | informational | priority | special'),
    openapi.Parameter('name',        openapi.IN_FORM, type=openapi.TYPE_STRING,  required=True),
    openapi.Parameter('code',        openapi.IN_FORM, type=openapi.TYPE_STRING,                 description='Masalan: 1.1, 2.5'),
    openapi.Parameter('description', openapi.IN_FORM, type=openapi.TYPE_STRING,  required=True),
    openapi.Parameter('image',       openapi.IN_FORM, type=openapi.TYPE_FILE,    required=True, description='Belgi rasmi'),
    openapi.Parameter('order',       openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=0),
    openapi.Parameter('is_active',   openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, default=True),
]

_QUESTION_FORM_PARAMS = [
    openapi.Parameter('lesson_video',   openapi.IN_FORM, type=openapi.TYPE_INTEGER,                 description='Video ID (ixtiyoriy)'),
    openapi.Parameter('question_text',  openapi.IN_FORM, type=openapi.TYPE_STRING,  required=True,  description='Savol matni'),
    openapi.Parameter('photo',          openapi.IN_FORM, type=openapi.TYPE_FILE,                    description='Savol rasmi'),
    openapi.Parameter('video',          openapi.IN_FORM, type=openapi.TYPE_FILE,                    description='Savol video klipi'),
    openapi.Parameter('difficulty',     openapi.IN_FORM, type=openapi.TYPE_STRING,  default='medium', description='easy | medium | hard'),
    openapi.Parameter('order',          openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=0),
    openapi.Parameter('is_active',      openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, default=True),
    openapi.Parameter(
        'answers', openapi.IN_FORM, type=openapi.TYPE_STRING,
        description='JSON: [{"answer_text":"A","is_correct":false,"order":1}, {"answer_text":"B","is_correct":true,"order":2}]',
    ),
]

_BULK_QUESTION_FORM_PARAMS = [
    openapi.Parameter(
        'lesson_video', openapi.IN_FORM, type=openapi.TYPE_INTEGER,
        description='Video ID (ixtiyoriy)',
    ),
    openapi.Parameter(
        'questions', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
        description=(
            'JSON array:\n'
            '[{"question_text":"Savol?","difficulty":"medium","order":1,'
            '"answers":[{"answer_text":"A","is_correct":false},{"answer_text":"B","is_correct":true}]}]'
        ),
    ),
    openapi.Parameter('photo_0',          openapi.IN_FORM, type=openapi.TYPE_FILE, description='0-savol rasmi'),
    openapi.Parameter('photo_1',          openapi.IN_FORM, type=openapi.TYPE_FILE, description='1-savol rasmi'),
    openapi.Parameter('photo_2',          openapi.IN_FORM, type=openapi.TYPE_FILE, description='2-savol rasmi'),
    openapi.Parameter('question_video_0', openapi.IN_FORM, type=openapi.TYPE_FILE, description='0-savol video klipi'),
    openapi.Parameter('question_video_1', openapi.IN_FORM, type=openapi.TYPE_FILE, description='1-savol video klipi'),
    openapi.Parameter('question_video_2', openapi.IN_FORM, type=openapi.TYPE_FILE, description='2-savol video klipi'),
]


# ==================== YORDAMCHI FUNKSIYALAR ====================

def _extract_multipart_data(request, json_fields=()):
    """
    QueryDict (multipart) dan JSON string maydonlarni parse qilib dict qaytaradi.
    JSON so'rovlarda o'zgartirmasdan qaytaradi.
    """
    if not isinstance(request.data, QueryDict):
        return request.data

    data = {}
    for key in request.data:
        val = request.data[key]
        if key in json_fields and isinstance(val, str):
            try:
                val = json.loads(val)
            except json.JSONDecodeError:
                pass
        data[key] = val
    return data


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ==================== AUTH ====================

class LoginView(APIView):
    """Foydalanuvchi login. device_id - qurilma identifikatori."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        device_id = serializer.validated_data['device_id']

        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {"detail": "Login yoki parol noto'g'ri."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if not user.is_active:
            return Response(
                {"detail": "Hisobingiz faol emas. Admin bilan bog'laning."},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        token_jti = str(access_token.get('jti', ''))

        session, created = UserSession.objects.get_or_create(user=user)
        old_device = session.device_id
        session.device_id = device_id
        session.last_login_ip = get_client_ip(request)
        session.token_jti = token_jti
        session.save()

        message = "Muvaffaqiyatli kirdingiz."
        if not created and old_device and old_device != device_id:
            message = "Yangi qurilmadan kirdingiz. Eski sessiya bekor qilindi."

        return Response({
            "message": message,
            "access": str(access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data
        })


class LogoutView(APIView):
    """Foydalanuvchi logout."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_OBJECT, description="Bo'sh body"))
    def post(self, request):
        try:
            session = UserSession.objects.get(user=request.user)
            session.token_jti = None
            session.device_id = None
            session.save()
        except UserSession.DoesNotExist:
            pass
        return Response({"message": "Muvaffaqiyatli chiqdingiz."})


class RegisterView(APIView):
    """Yangi foydalanuvchi ro'yxatdan o'tkazish."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=RegisterSerializer)
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "message": "Muvaffaqiyatli ro'yxatdan o'tdingiz.",
            "user": UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)


class AdminUserListCreateView(generics.ListCreateAPIView):
    """
    GET  - Barcha foydalanuvchilar (faqat admin)
    POST - Yangi foydalanuvchi qo'shish (faqat admin)
    """
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return AdminUserSerializer
        if self.request.method == 'POST':
            return AdminUserCreateSerializer
        return AdminUserSerializer

    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(email__icontains=search)
            )
        return queryset

    @swagger_auto_schema(request_body=AdminUserCreateSerializer, responses={201: AdminUserSerializer()})
    def create(self, request, *args, **kwargs):
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AdminUserSerializer(user).data, status=status.HTTP_201_CREATED)


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    - Foydalanuvchi ma'lumotlari (faqat admin)
    PATCH  - Qisman yangilash (faqat admin)
    PUT    - To'liq yangilash (faqat admin)
    DELETE - O'chirish (faqat admin)
    """
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return AdminUserSerializer
        if self.request.method in ('PUT', 'PATCH'):
            return AdminUserUpdateSerializer
        return AdminUserSerializer

    @swagger_auto_schema(request_body=AdminUserUpdateSerializer, responses={200: AdminUserSerializer()})
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = AdminUserUpdateSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AdminUserSerializer(user).data)

    @swagger_auto_schema(request_body=AdminUserUpdateSerializer, responses={200: AdminUserSerializer()})
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = AdminUserUpdateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AdminUserSerializer(user).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance == request.user:
            return Response(
                {"detail": "O'z hisobingizni bu yerdan o'chira olmaysiz."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileView(APIView):
    """
    GET    - Profil va statistika
    PATCH  - Profilni yangilash (ism, email, parol)
    DELETE - Hisobni o'chirish
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        completed = VideoProgress.objects.filter(user=user, is_completed=True).count()
        total = Video.objects.filter(is_active=True).count()
        return Response({
            "user": UserSerializer(user).data,
            "stats": {
                "completed_videos": completed,
                "total_videos": total,
                "progress_percent": round((completed / total * 100) if total > 0 else 0, 1)
            }
        })

    @swagger_auto_schema(request_body=UserUpdateSerializer)
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "message": "Profil yangilandi.",
            "user": UserSerializer(user).data,
        })

    @swagger_auto_schema(request_body=UserUpdateSerializer)
    def put(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "message": "Profil yangilandi.",
            "user": UserSerializer(user).data,
        })

    def delete(self, request):
        user = request.user
        try:
            session = UserSession.objects.get(user=user)
            session.delete()
        except UserSession.DoesNotExist:
            pass
        user.delete()
        return Response(
            {"message": "Hisobingiz muvaffaqiyatli o'chirildi."},
            status=status.HTTP_204_NO_CONTENT,
        )


# ==================== VIDEO ====================

def _video_queryset_with_prefetch(user):
    """Video queryset — N+1 muammosini oldini olish uchun prefetch_related."""
    return Video.objects.filter(is_active=True).prefetch_related(
        Prefetch(
            'progress',
            queryset=VideoProgress.objects.filter(user=user),
            to_attr='_user_progress_cache',
        ),
        Prefetch(
            'test_questions',
            queryset=TestQuestion.objects.filter(is_active=True),
            to_attr='_active_test_questions_cache',
        ),
        Prefetch(
            'test_results',
            queryset=TestResult.objects.filter(user=user, passed=True),
            to_attr='_passed_test_results_cache',
        ),
    )


class VideoListCreateView(generics.ListCreateAPIView):
    """
    GET  - Barcha faol videolar
    POST - Yangi video qo'shish (faqat admin) — multipart/form-data
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return VideoSerializer
        if self.request.method == 'POST':
            return VideoWriteSerializer
        return VideoSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Video.objects.none()
        if self.request.method == 'GET':
            return _video_queryset_with_prefetch(self.request.user)
        return Video.objects.filter(is_active=True)

    @swagger_auto_schema(
        operation_description="Yangi video qo'shish (faqat admin). video_file yoki youtube_url dan biri bo'lishi kerak.",
        manual_parameters=_VIDEO_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={201: VideoSerializer()},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class VideoRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    - Video ma'lumotlari
    PUT    - Yangilash (faqat admin) — multipart/form-data
    PATCH  - Qisman yangilash (faqat admin) — multipart/form-data
    DELETE - O'chirish (faqat admin)
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return VideoSerializer
        if self.request.method in ('PUT', 'PATCH'):
            return VideoWriteSerializer
        return VideoSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Video.objects.none()
        if self.request.method == 'GET':
            return _video_queryset_with_prefetch(self.request.user)
        return Video.objects.filter(is_active=True)

    @swagger_auto_schema(
        manual_parameters=_VIDEO_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={200: VideoSerializer()},
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        manual_parameters=_VIDEO_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={200: VideoSerializer()},
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)


class VideoStreamView(APIView):
    """Video streaming - yuklab olishni oldini olish."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        video = get_object_or_404(Video, pk=pk, is_active=True)

        if not video.video_file:
            return Response(
                {"detail": "Video fayli mavjud emas."},
                status=status.HTTP_404_NOT_FOUND
            )

        video_path = video.video_file.path
        if not os.path.exists(video_path):
            raise Http404("Video fayli topilmadi.")

        file_size = os.path.getsize(video_path)
        content_type, _ = mimetypes.guess_type(video_path)
        if not content_type:
            content_type = 'video/mp4'

        range_header = request.META.get('HTTP_RANGE', '').strip()
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header) if range_header else None

        if range_match:
            first_byte = int(range_match.group(1))
            last_byte = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            last_byte = min(last_byte, file_size - 1)
            length = last_byte - first_byte + 1

            response = StreamingHttpResponse(
                self._file_iterator(video_path, offset=first_byte, length=length),
                status=206,
                content_type=content_type
            )
            response['Content-Range'] = f'bytes {first_byte}-{last_byte}/{file_size}'
            response['Content-Length'] = str(length)
        else:
            response = StreamingHttpResponse(
                self._file_iterator(video_path),
                content_type=content_type
            )
            response['Content-Length'] = str(file_size)

        response['Content-Disposition'] = 'inline'
        response['Accept-Ranges'] = 'bytes'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        return response

    @staticmethod
    def _file_iterator(path, offset=0, length=None, chunk_size=8192):
        with open(path, 'rb') as f:
            f.seek(offset)
            remaining = length
            while True:
                read_size = chunk_size if remaining is None else min(chunk_size, remaining)
                chunk = f.read(read_size)
                if not chunk:
                    break
                yield chunk
                if remaining is not None:
                    remaining -= len(chunk)
                    if remaining <= 0:
                        break


class UpdateProgressView(APIView):
    """Video ko'rish progressini yangilash."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=UpdateProgressSerializer)
    def post(self, request, pk):
        video = get_object_or_404(Video, pk=pk, is_active=True)
        serializer = UpdateProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        progress, _ = VideoProgress.objects.get_or_create(
            user=request.user, video=video
        )
        progress.watched_seconds = serializer.validated_data['watched_seconds']
        progress.is_completed = serializer.validated_data['is_completed']
        progress.save()

        return Response({
            "message": "Progress saqlandi.",
            "is_completed": progress.is_completed
        })


# ==================== YO'L BELGILARI ====================

class RoadSignCategoryListView(APIView):
    """Yo'l belgilari kategoriyalari ro'yxati."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = [
            {"key": key, "label": label}
            for key, label in RoadSign.SIGN_CATEGORIES
        ]
        return Response(categories)


class RoadSignListCreateView(generics.ListCreateAPIView):
    """
    GET  - Barcha yo'l belgilari. ?category=<key> filter
    POST - Yangi yo'l belgisi qo'shish (faqat admin) — multipart/form-data
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return RoadSignSerializer
        if self.request.method == 'POST':
            return RoadSignWriteSerializer
        return RoadSignSerializer

    def get_queryset(self):
        queryset = RoadSign.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    @swagger_auto_schema(
        operation_description="Yangi yo'l belgisi qo'shish (faqat admin).",
        manual_parameters=_ROAD_SIGN_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={201: RoadSignSerializer()},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class RoadSignRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    - Yo'l belgisi ma'lumotlari
    PUT    - Yangilash (faqat admin) — multipart/form-data
    PATCH  - Qisman yangilash (faqat admin) — multipart/form-data
    DELETE - O'chirish (faqat admin)
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return RoadSignSerializer
        if self.request.method in ('PUT', 'PATCH'):
            return RoadSignWriteSerializer
        return RoadSignSerializer

    def get_queryset(self):
        return RoadSign.objects.filter(is_active=True)

    @swagger_auto_schema(
        manual_parameters=_ROAD_SIGN_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={200: RoadSignSerializer()},
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        manual_parameters=_ROAD_SIGN_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={200: RoadSignSerializer()},
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)


# ==================== TEST ====================

class VideoTestQuestionListView(generics.ListAPIView):
    """
    GET /api/videos/<pk>/tests/ — Video darsiga tegishli test savollari.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TestQuestionSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TestQuestion.objects.none()
        video = get_object_or_404(Video, pk=self.kwargs['pk'], is_active=True)
        return TestQuestion.objects.filter(
            lesson_video=video, is_active=True
        ).prefetch_related('answers')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if not queryset.exists():
            return Response(
                {"detail": "Bu video uchun test mavjud emas."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class VideoTestSubmitView(APIView):
    """
    POST /api/videos/<pk>/tests/submit/ — Video testi javoblarini yuborish.
    Body: {"answers": [{"question_id": 1, "answer_id": 3}, ...]}
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=SubmitTestSerializer)
    def post(self, request, pk):
        video = get_object_or_404(Video, pk=pk, is_active=True)
        serializer = SubmitTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answers_data = serializer.validated_data['answers']
        questions = TestQuestion.objects.filter(
            lesson_video=video, is_active=True
        ).prefetch_related('answers')

        total = questions.count()

        if total == 0:
            return Response(
                {"detail": "Bu video uchun test mavjud emas."},
                status=status.HTTP_404_NOT_FOUND
            )

        if len(answers_data) != total:
            return Response(
                {
                    "detail": (
                        f"Barcha savollarga javob berish kerak. "
                        f"Kutilgan: {total}, "
                        f"Olingan: {len(answers_data)}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        correct_count = 0
        user_answers_list = []

        for answer_data in answers_data:
            question_id = answer_data.get('question_id')
            answer_id = answer_data.get('answer_id')

            try:
                question = questions.get(id=question_id)
                answer = TestAnswer.objects.get(id=answer_id, question=question)
            except (TestQuestion.DoesNotExist, TestAnswer.DoesNotExist):
                return Response(
                    {
                        "detail": (
                            f"Savol yoki javob topilmadi. "
                            f"Question: {question_id}, Answer: {answer_id}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            is_correct = answer.is_correct
            if is_correct:
                correct_count += 1

            user_answers_list.append({
                'question': question,
                'answer': answer,
                'is_correct': is_correct,
            })

        score_percent = round((correct_count / total * 100) if total > 0 else 0, 1)
        passed = score_percent >= 70

        test_result = TestResult.objects.create(
            user=request.user,
            lesson_video=video,
            total_questions=total,
            correct_answers=correct_count,
            score_percent=score_percent,
            passed=passed,
        )

        for ua in user_answers_list:
            UserTestAnswer.objects.create(
                test_result=test_result,
                question=ua['question'],
                selected_answer=ua['answer'],
                is_correct=ua['is_correct'],
            )

        return Response({
            "message": "Test yuborildi.",
            "result": TestResultSerializer(test_result).data,
        }, status=status.HTTP_201_CREATED)


class VideoTestResultListView(generics.ListAPIView):
    """
    GET /api/videos/<pk>/tests/results/ — Foydalanuvchining bu video uchun test natijalari.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TestResultListSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TestResult.objects.none()
        video = get_object_or_404(Video, pk=self.kwargs['pk'], is_active=True)
        return TestResult.objects.filter(
            user=self.request.user, lesson_video=video
        ).order_by('-completed_at')


class BulkTestQuestionCreateView(APIView):
    """
    POST /api/tests/questions/bulk/
    JSON yoki multipart/form-data orqali bir so'rovda ko'p savol yaratish.
    Rasmlar: photo_0, photo_1, ... | Video kliplar: question_video_0, question_video_1, ...
    """
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description=(
            "Bir so'rovda ko'p savol yaratish.\n\n"
            "**JSON rejimi** (`application/json`):\n"
            "```json\n"
            "{\"lesson_video\":1,\"questions\":[{\"question_text\":\"Savol?\",\"difficulty\":\"medium\","
            "\"order\":1,\"answers\":[{\"answer_text\":\"A\",\"is_correct\":false},{\"answer_text\":\"B\","
            "\"is_correct\":true}]}]}\n"
            "```\n\n"
            "**Fayl rejimi** (`multipart/form-data`):\n"
            "`questions` ni JSON string sifatida yuboring, "
            "rasmlarni `photo_0`, `photo_1`, video kliplarni `question_video_0`, `question_video_1` orqali biriktiring."
        ),
        manual_parameters=_BULK_QUESTION_FORM_PARAMS,
        consumes=['multipart/form-data', 'application/json'],
        responses={
            201: openapi.Response(
                description="Savollar muvaffaqiyatli yaratildi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="3 ta savol muvaffaqiyatli yaratildi."),
                        'video': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        'questions': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT),
                        ),
                    }
                )
            )
        },
    )
    def post(self, request):
        data = _extract_multipart_data(request, json_fields=('questions',))

        serializer = BulkQuestionCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        lesson_video = serializer.validated_data.get('lesson_video')
        questions_data = serializer.validated_data['questions']

        created = []
        with transaction.atomic():
            for i, q_data in enumerate(questions_data):
                answers_data = q_data.pop('answers')
                question = TestQuestion.objects.create(
                    lesson_video=lesson_video,
                    question_text=q_data['question_text'],
                    difficulty=q_data['difficulty'],
                    order=q_data.get('order', i + 1),
                    is_active=True,
                )

                photo = request.FILES.get(f'photo_{i}')
                q_video = request.FILES.get(f'question_video_{i}')
                if photo or q_video:
                    if photo:
                        question.photo = photo
                    if q_video:
                        question.video = q_video
                    question.save()

                for j, ans in enumerate(answers_data, start=1):
                    TestAnswer.objects.create(
                        question=question,
                        answer_text=ans['answer_text'],
                        is_correct=ans.get('is_correct', False),
                        order=ans.get('order', j),
                    )
                created.append(question)

        return Response(
            {
                "message": f"{len(created)} ta savol muvaffaqiyatli yaratildi.",
                "video": lesson_video.title if lesson_video else None,
                "questions": TestQuestionDetailSerializer(
                    created, many=True, context={'request': request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class TestQuestionListView(generics.ListCreateAPIView):
    """
    GET  - Barcha faol test savollari
    POST - Yangi savol + javoblar qo'shish (faqat admin) — multipart/form-data yoki JSON
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return TestQuestionSerializer
        if self.request.method == 'POST':
            return TestQuestionWithAnswersWriteSerializer
        return TestQuestionSerializer

    def get_queryset(self):
        return TestQuestion.objects.filter(is_active=True).prefetch_related('answers')

    @swagger_auto_schema(
        operation_description=(
            "Yangi savol qo'shish. Javoblarni ham birga yuboring.\n\n"
            "**JSON rejimi**: `answers` ni list sifatida yuboring.\n"
            "**Fayl rejimi**: `answers` ni JSON string sifatida yuboring."
        ),
        manual_parameters=_QUESTION_FORM_PARAMS,
        consumes=['multipart/form-data', 'application/json'],
        responses={201: TestQuestionDetailSerializer()},
    )
    def create(self, request, *args, **kwargs):
        data = _extract_multipart_data(request, json_fields=('answers',))
        serializer = TestQuestionWithAnswersWriteSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        return Response(
            TestQuestionDetailSerializer(question, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class TestQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    - Savol batafsil (to'g'ri javob bilan)
    PUT    - Yangilash (faqat admin) — multipart/form-data yoki JSON
    PATCH  - Qisman yangilash (faqat admin) — multipart/form-data yoki JSON
    DELETE - O'chirish (faqat admin)
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return TestQuestionDetailSerializer
        if self.request.method in ('PUT', 'PATCH'):
            return TestQuestionWithAnswersWriteSerializer
        return TestQuestionDetailSerializer

    def get_queryset(self):
        return TestQuestion.objects.filter(is_active=True).prefetch_related('answers')

    @swagger_auto_schema(
        manual_parameters=_QUESTION_FORM_PARAMS,
        consumes=['multipart/form-data', 'application/json'],
        responses={200: TestQuestionDetailSerializer()},
    )
    def update(self, request, *args, **kwargs):
        data = _extract_multipart_data(request, json_fields=('answers',))
        instance = self.get_object()
        serializer = TestQuestionWithAnswersWriteSerializer(
            instance, data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        return Response(TestQuestionDetailSerializer(question, context={'request': request}).data)

    @swagger_auto_schema(
        manual_parameters=_QUESTION_FORM_PARAMS,
        consumes=['multipart/form-data', 'application/json'],
        responses={200: TestQuestionDetailSerializer()},
    )
    def partial_update(self, request, *args, **kwargs):
        data = _extract_multipart_data(request, json_fields=('answers',))
        instance = self.get_object()
        serializer = TestQuestionWithAnswersWriteSerializer(
            instance, data=data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        return Response(TestQuestionDetailSerializer(question, context={'request': request}).data)


class TestAnswerListCreateView(generics.ListCreateAPIView):
    """
    GET  - Savolga tegishli variantlar. ?question=<id> filter
    POST - Yangi variant qo'shish (faqat admin)
    """
    permission_classes = [IsAdminUser]
    serializer_class = TestAnswerWriteSerializer

    def get_queryset(self):
        question_id = self.request.query_params.get('question')
        if question_id:
            return TestAnswer.objects.filter(question_id=question_id)
        return TestAnswer.objects.all()


class TestAnswerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Variant yangilash/o'chirish (faqat admin)"""
    permission_classes = [IsAdminUser]
    serializer_class = TestAnswerWriteSerializer
    queryset = TestAnswer.objects.all()


class SubmitTestView(APIView):
    """
    Test javoblarini yuborish va natijani hisoblash.
    POST /api/tests/submit/
    Body: {"answers": [{"question_id": 1, "answer_id": 3}, ...]}
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=SubmitTestSerializer)
    def post(self, request):
        serializer = SubmitTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answers_data = serializer.validated_data['answers']

        questions = TestQuestion.objects.filter(
            is_active=True, lesson_video__isnull=True
        ).prefetch_related('answers')

        total = questions.count()

        if len(answers_data) != total:
            return Response(
                {
                    "detail": (
                        f"Barcha savollarga javob berish kerak. "
                        f"Kutilgan: {total}, "
                        f"Olingan: {len(answers_data)}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        correct_count = 0
        user_answers_list = []

        for answer_data in answers_data:
            question_id = answer_data.get('question_id')
            answer_id = answer_data.get('answer_id')

            try:
                question = questions.get(id=question_id)
                answer = TestAnswer.objects.get(id=answer_id, question=question)
            except (TestQuestion.DoesNotExist, TestAnswer.DoesNotExist):
                return Response(
                    {
                        "detail": (
                            f"Savol yoki javob topilmadi. "
                            f"Question: {question_id}, Answer: {answer_id}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            is_correct = answer.is_correct
            if is_correct:
                correct_count += 1

            user_answers_list.append({
                'question': question,
                'answer': answer,
                'is_correct': is_correct
            })

        score_percent = round((correct_count / total * 100) if total > 0 else 0, 1)
        passed = score_percent >= 70

        test_result = TestResult.objects.create(
            user=request.user,
            total_questions=total,
            correct_answers=correct_count,
            score_percent=score_percent,
            passed=passed
        )

        for user_answer in user_answers_list:
            UserTestAnswer.objects.create(
                test_result=test_result,
                question=user_answer['question'],
                selected_answer=user_answer['answer'],
                is_correct=user_answer['is_correct']
            )

        return Response({
            "message": "Test yuborildi.",
            "result": TestResultSerializer(test_result).data
        }, status=status.HTTP_201_CREATED)


class TestResultListView(generics.ListAPIView):
    """Foydalanuvchining test natijalari ro'yxati"""
    permission_classes = [IsAuthenticated]
    serializer_class = TestResultListSerializer

    def get_queryset(self):
        return TestResult.objects.filter(user=self.request.user).order_by('-completed_at')


class TestResultDetailView(generics.RetrieveAPIView):
    """Test natijasining batafsil ma'lumotlari"""
    permission_classes = [IsAuthenticated]
    serializer_class = TestResultSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TestResult.objects.none()
        return TestResult.objects.filter(user=self.request.user)


class TestStatisticsView(APIView):
    """Foydalanuvchining umumiy test statistikasi"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        results = TestResult.objects.filter(user=user)

        total_tests = results.count()
        passed_tests = results.filter(passed=True).count()
        avg_score = results.aggregate(
            models.Avg('score_percent')
        )['score_percent__avg'] or 0

        return Response({
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "average_score": round(avg_score, 1),
            "pass_rate": round(
                (passed_tests / total_tests * 100) if total_tests > 0 else 0, 1
            ),
        })


# ==================== KITOBLAR ====================

_BOOK_FORM_PARAMS = [
    openapi.Parameter('title',          openapi.IN_FORM, type=openapi.TYPE_STRING,  required=True,  description='Sarlavha (UZ)'),
    openapi.Parameter('title_ru',       openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Sarlavha (RU)'),
    openapi.Parameter('description',    openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Tavsif (UZ)'),
    openapi.Parameter('description_ru', openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Tavsif (RU)'),
    openapi.Parameter('price',          openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=0,      description='Narxi (so\'mda)'),
    openapi.Parameter('image',          openapi.IN_FORM, type=openapi.TYPE_FILE,                    description='Muqova rasmi'),
    openapi.Parameter('file',           openapi.IN_FORM, type=openapi.TYPE_FILE,    required=True,  description='Kitob fayli (PDF)'),
    openapi.Parameter('year',           openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=True,  description='Nashr yili, masalan: 2024'),
    openapi.Parameter('pages',          openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=0,      description='Sahifalar soni'),
    openapi.Parameter('order',          openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=0),
    openapi.Parameter('is_active',      openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, default=True),
]


class BookListCreateView(generics.ListCreateAPIView):
    """
    GET  - Faol kitoblar ro'yxati
    POST - Yangi kitob qo'shish (faqat admin) — multipart/form-data
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return BookSerializer
        if self.request.method == 'POST':
            return BookWriteSerializer
        return BookSerializer

    def get_queryset(self):
        return Book.objects.filter(is_active=True)

    @swagger_auto_schema(
        operation_description="Yangi kitob qo'shish (faqat admin). multipart/form-data",
        manual_parameters=_BOOK_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={201: BookSerializer()},
    )
    def create(self, request, *args, **kwargs):
        serializer = BookWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.save()
        return Response(BookSerializer(book).data, status=status.HTTP_201_CREATED)


class BookRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    - Kitob tafsilotlari
    PUT    - Yangilash (faqat admin)
    PATCH  - Qisman yangilash (faqat admin)
    DELETE - O'chirish (faqat admin)
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return BookSerializer
        if self.request.method in ('PUT', 'PATCH'):
            return BookWriteSerializer
        return BookSerializer

    def get_queryset(self):
        return Book.objects.filter(is_active=True)

    @swagger_auto_schema(
        manual_parameters=_BOOK_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={200: BookSerializer()},
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = BookWriteSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.save()
        return Response(BookSerializer(book).data)

    @swagger_auto_schema(
        manual_parameters=_BOOK_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={200: BookSerializer()},
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = BookWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        book = serializer.save()
        return Response(BookSerializer(book).data)