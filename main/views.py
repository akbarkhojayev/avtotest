import json

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import Prefetch
from django.http import QueryDict
from django.shortcuts import get_object_or_404

from rest_framework import status, generics
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.utils import timezone
from datetime import timedelta

from .models import (
    Video, VideoProgress, RoadSign, UserSession,
    Category, TestQuestion, TestAnswer, TestResult, UserTestAnswer,
    Book, PaymentRequest, UserSubscription,
)
from .serializers import (
    LoginSerializer, UserSerializer, RegisterSerializer, UserUpdateSerializer,
    AdminUserSerializer, AdminUserCreateSerializer, AdminUserUpdateSerializer,
    VideoSerializer, VideoWriteSerializer,
    RoadSignSerializer, RoadSignWriteSerializer,
    UpdateProgressSerializer,
    CategorySerializer, CategoryWriteSerializer,
    TestQuestionSerializer, TestQuestionDetailSerializer,
    TestQuestionWriteSerializer, TestQuestionWithAnswersWriteSerializer,
    TestAnswerWriteSerializer,
    TestResultSerializer, TestResultListSerializer,
    SubmitTestSerializer,
    BookSerializer, BookWriteSerializer,
    SubscriptionSerializer,
    PaymentRequestCreateSerializer, PaymentRequestSerializer,
    PaymentRequestAdminSerializer, PaymentReviewSerializer,
)



_VIDEO_FORM_PARAMS = [
    openapi.Parameter('title',          openapi.IN_FORM, type=openapi.TYPE_STRING,  required=True,  description='Sarlavha (UZ)'),
    openapi.Parameter('title_ru',       openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Sarlavha (RU)'),
    openapi.Parameter('description',    openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Tavsif (UZ)'),
    openapi.Parameter('description_ru', openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Tavsif (RU)'),
    openapi.Parameter('video_file',     openapi.IN_FORM, type=openapi.TYPE_FILE,                    description='Video fayli (mp4) — video_file yoki video_url dan biri shart'),
    openapi.Parameter('video_url',      openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Video URL (YouTube embed va h.k.) — video_file yoki video_url dan biri shart'),
    openapi.Parameter('thumbnail',      openapi.IN_FORM, type=openapi.TYPE_FILE,                    description='Muqova rasmi'),
    openapi.Parameter('duration',       openapi.IN_FORM, type=openapi.TYPE_STRING,                  description='Davomiyligi, masalan: 10:30'),
    openapi.Parameter('order',          openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=0),
    openapi.Parameter('is_paid',        openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, default=False,  description='Pullik dars (true) yoki Tekin (false)'),
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
    openapi.Parameter('category',       openapi.IN_FORM, type=openapi.TYPE_INTEGER,                 description='Kategoriya ID (ixtiyoriy)'),
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


def _extract_multipart_data(request, json_fields=()):

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

    for key, file in request.FILES.items():
        data[key] = file

    return data


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class LoginView(APIView):
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

        default_role = 'admin' if user.is_staff else 'user'
        session, created = UserSession.objects.get_or_create(
            user=user, defaults={'role': default_role}
        )
        old_device = session.device_id
        session.device_id = device_id
        session.last_login_ip = get_client_ip(request)
        session.token_jti = token_jti
        if created:
            session.role = default_role
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



def _check_subscription(user, video):
    """Pullik video uchun obuna tekshiruvi. Xato bo'lsa Response qaytaradi, aks holda None."""
    if not video.is_paid or user.is_staff:
        return None
    try:
        if user.subscription.is_active:
            return None
    except UserSubscription.DoesNotExist:
        pass
    return Response(
        {"detail": "Bu dars pullik. Obuna sotib oling."},
        status=status.HTTP_403_FORBIDDEN,
    )


def _video_queryset_with_prefetch(user):
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
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return VideoWriteSerializer
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
        operation_description="Videolar ro'yxati",
        responses={200: VideoSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Yangi video qo'shish (faqat admin). video_file yoki video_url dan biri bo'lishi kerak.",
        manual_parameters=_VIDEO_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={201: VideoSerializer()},
    )
    def create(self, request, *args, **kwargs):
        serializer = VideoWriteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        video = serializer.save()
        return Response(
            VideoSerializer(video, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class VideoRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return VideoWriteSerializer
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
        operation_description="Video ma'lumotlari",
        responses={200: VideoSerializer()},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        manual_parameters=_VIDEO_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={200: VideoSerializer()},
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = VideoWriteSerializer(instance, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        video = serializer.save()
        return Response(VideoSerializer(video, context={'request': request}).data)

    @swagger_auto_schema(
        manual_parameters=_VIDEO_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={200: VideoSerializer()},
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = VideoWriteSerializer(instance, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        video = serializer.save()
        return Response(VideoSerializer(video, context={'request': request}).data)


class UpdateProgressView(APIView):
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


class RoadSignCategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = [
            {"key": key, "label": label}
            for key, label in RoadSign.SIGN_CATEGORIES
        ]
        return Response(categories)


class RoadSignListCreateView(generics.ListCreateAPIView):
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


class VideoTestQuestionListView(generics.ListAPIView):
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
        video = get_object_or_404(Video, pk=self.kwargs['pk'], is_active=True)
        err = _check_subscription(request.user, video)
        if err:
            return err
        queryset = self.filter_queryset(self.get_queryset())
        if not queryset.exists():
            return Response(
                {"detail": "Bu video uchun test mavjud emas."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class VideoTestSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=SubmitTestSerializer)
    def post(self, request, pk):
        video = get_object_or_404(Video, pk=pk, is_active=True)
        err = _check_subscription(request.user, video)
        if err:
            return err
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
    permission_classes = [IsAuthenticated]
    serializer_class = TestResultListSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TestResult.objects.none()
        video = get_object_or_404(Video, pk=self.kwargs['pk'], is_active=True)
        return TestResult.objects.filter(
            user=self.request.user, lesson_video=video
        ).order_by('-completed_at')




class CategoryListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CategoryWriteSerializer
        return CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(is_active=True)

    @swagger_auto_schema(
        request_body=CategoryWriteSerializer,
        responses={201: CategorySerializer()},
    )
    def create(self, request, *args, **kwargs):
        serializer = CategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return CategoryWriteSerializer
        return CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(is_active=True)

    @swagger_auto_schema(request_body=CategoryWriteSerializer, responses={200: CategorySerializer()})
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = CategoryWriteSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(CategorySerializer(serializer.save()).data)

    @swagger_auto_schema(request_body=CategoryWriteSerializer, responses={200: CategorySerializer()})
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = CategoryWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(CategorySerializer(serializer.save()).data)


class TestQuestionListView(generics.ListCreateAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return TestQuestionWriteSerializer
        if self.request.method == 'POST':
            return TestQuestionWithAnswersWriteSerializer
        return TestQuestionSerializer

    def get_queryset(self):
        qs = TestQuestion.objects.filter(is_active=True).prefetch_related('answers')
        category_id = self.request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs

    @swagger_auto_schema(
        operation_description=(
            "Yangi savol + variantlar qo'shish (faqat admin).\n\n"
            "`answers` — JSON string sifatida yuboring:\n"
            '`[{"answer_text":"A","is_correct":false,"order":1},{"answer_text":"B","is_correct":true,"order":2}]`\n\n'
            "Rasmsiz yuborish uchun `photo` maydonini bo'sh qoldiring."
        ),
        manual_parameters=_QUESTION_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={201: TestQuestionDetailSerializer()},
    )
    def create(self, request, *args, **kwargs):
        data = _extract_multipart_data(request, json_fields=('answers',))
        serializer = TestQuestionWithAnswersWriteSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        return Response(
            TestQuestionDetailSerializer(question, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class TestQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return TestQuestionWriteSerializer
        if self.request.method in ('PUT', 'PATCH'):
            return TestQuestionWithAnswersWriteSerializer
        return TestQuestionDetailSerializer

    def get_queryset(self):
        return TestQuestion.objects.filter(is_active=True).prefetch_related('answers')

    @swagger_auto_schema(
        manual_parameters=_QUESTION_FORM_PARAMS,
        consumes=['multipart/form-data'],
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
        consumes=['multipart/form-data'],
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
    permission_classes = [IsAdminUser]
    serializer_class = TestAnswerWriteSerializer

    def get_queryset(self):
        question_id = self.request.query_params.get('question')
        if question_id:
            return TestAnswer.objects.filter(question_id=question_id)
        return TestAnswer.objects.all()


class TestAnswerDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = TestAnswerWriteSerializer
    queryset = TestAnswer.objects.all()


class SubmitTestView(APIView):
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
    permission_classes = [IsAuthenticated]
    serializer_class = TestResultListSerializer

    def get_queryset(self):
        return TestResult.objects.filter(user=self.request.user).order_by('-completed_at')


class TestResultDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TestResultSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TestResult.objects.none()
        return TestResult.objects.filter(user=self.request.user)


class TestStatisticsView(APIView):
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


# ==================== DASHBOARD ====================

class DashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_users      = User.objects.filter(is_staff=False).count()
        new_users_month  = User.objects.filter(is_staff=False, date_joined__gte=month_start).count()
        active_subs      = UserSubscription.objects.filter(expires_at__gt=now).count()

        payments_month   = PaymentRequest.objects.filter(created_at__gte=month_start)
        payments_pending = payments_month.filter(status='pending').count()
        payments_approved= payments_month.filter(status='approved').count()
        payments_total   = payments_month.count()
        payments_amount  = payments_month.filter(status='approved').aggregate(
            total=models.Sum('amount')
        )['total'] or 0

        total_videos     = Video.objects.filter(is_active=True).count()
        paid_videos      = Video.objects.filter(is_active=True, is_paid=True).count()
        free_videos      = total_videos - paid_videos

        total_questions  = TestQuestion.objects.filter(is_active=True).count()
        total_road_signs = RoadSign.objects.filter(is_active=True).count()
        total_books      = Book.objects.filter(is_active=True).count()

        tests_month      = TestResult.objects.filter(completed_at__gte=month_start)
        tests_passed     = tests_month.filter(passed=True).count()

        return Response({
            "users": {
                "total":          total_users,
                "new_this_month": new_users_month,
                "active_subs":    active_subs,
            },
            "payments": {
                "this_month_total":    payments_total,
                "this_month_approved": payments_approved,
                "this_month_pending":  payments_pending,
                "this_month_amount":   payments_amount,
            },
            "content": {
                "videos":      total_videos,
                "paid_videos": paid_videos,
                "free_videos": free_videos,
                "questions":   total_questions,
                "road_signs":  total_road_signs,
                "books":       total_books,
            },
            "tests": {
                "this_month_total":  tests_month.count(),
                "this_month_passed": tests_passed,
            },
        })


_PAYMENT_FORM_PARAMS = [
    openapi.Parameter('amount',  openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=True, description="To'langan summa (so'mda)"),
    openapi.Parameter('receipt', openapi.IN_FORM, type=openapi.TYPE_FILE,    required=True, description="To'lov cheki rasmi"),
    openapi.Parameter('comment', openapi.IN_FORM, type=openapi.TYPE_STRING,                description="Izoh (ixtiyoriy)"),
]


class PaymentRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Foydalanuvchi o'z to'lov so'rovlarini ko'radi.",
        responses={200: PaymentRequestSerializer(many=True)},
    )
    def get(self, request):
        qs = PaymentRequest.objects.filter(user=request.user)
        return Response(PaymentRequestSerializer(qs, many=True, context={'request': request}).data)

    @swagger_auto_schema(
        operation_description="To'lov cheki yuborish. multipart/form-data",
        manual_parameters=_PAYMENT_FORM_PARAMS,
        consumes=['multipart/form-data'],
        responses={201: PaymentRequestSerializer()},
    )
    def post(self, request):
        if PaymentRequest.objects.filter(user=request.user, status='pending').exists():
            return Response(
                {"detail": "Sizning kutilayotgan to'lov so'rovingiz mavjud. Avval u ko'rib chiqilishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PaymentRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save(user=request.user)
        return Response(
            PaymentRequestSerializer(payment, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub = request.user.subscription
            return Response(SubscriptionSerializer(sub).data)
        except UserSubscription.DoesNotExist:
            return Response({"detail": "Faol obuna mavjud emas.", "is_active": False})


class PaymentAdminListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = PaymentRequestAdminSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PaymentRequest.objects.none()
        qs = PaymentRequest.objects.select_related('user', 'reviewed_by').all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class PaymentReviewView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        request_body=PaymentReviewSerializer,
        responses={200: openapi.Response(
            description="Natija",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING),
                    'payment': openapi.Schema(type=openapi.TYPE_OBJECT),
                },
            )
        )},
    )
    def post(self, request, pk):
        serializer = PaymentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action            = serializer.validated_data['action']
        admin_note        = serializer.validated_data.get('admin_note', '')
        subscription_days = serializer.validated_data.get('subscription_days', 30)

        with transaction.atomic():
            # select_for_update — ikki admin bir vaqtda tasdiqlamasin
            payment = PaymentRequest.objects.select_for_update().filter(pk=pk).first()
            if not payment:
                return Response({"detail": "To'lov topilmadi."}, status=status.HTTP_404_NOT_FOUND)

            if payment.status != 'pending':
                return Response(
                    {"detail": "Bu so'rov allaqachon ko'rib chiqilgan."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment.admin_note   = admin_note
            payment.reviewed_by  = request.user
            payment.reviewed_at  = timezone.now()

            if action == 'approve':
                payment.status           = 'approved'
                payment.subscription_days = subscription_days
                payment.save()

                now = timezone.now()
                try:
                    sub = UserSubscription.objects.select_for_update().get(user=payment.user)
                    sub.expires_at = (sub.expires_at if sub.expires_at > now else now) + timedelta(days=subscription_days)
                    sub.save()
                except UserSubscription.DoesNotExist:
                    UserSubscription.objects.create(
                        user=payment.user,
                        expires_at=now + timedelta(days=subscription_days),
                    )

                return Response({
                    "detail": f"Tasdiqlandi. Foydalanuvchiga {subscription_days} kunlik obuna berildi.",
                    "payment": PaymentRequestAdminSerializer(payment, context={'request': request}).data,
                })
            else:
                payment.status = 'rejected'
                payment.save()
                return Response({
                    "detail": "Rad etildi.",
                    "payment": PaymentRequestAdminSerializer(payment, context={'request': request}).data,
                })