import os
import re
import mimetypes

from django.contrib.auth import authenticate
from django.db import models
from django.http import StreamingHttpResponse, Http404
from django.shortcuts import get_object_or_404

from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Category, Video, VideoProgress, RoadSign, UserSession, TestQuestion, TestAnswer, TestResult, UserTestAnswer
from .serializers import (
    LoginSerializer, UserSerializer,
    CategoryListSerializer, CategorySerializer, CategoryWriteSerializer,
    VideoSerializer, VideoWriteSerializer,
    RoadSignSerializer, RoadSignWriteSerializer,
    UpdateProgressSerializer,
    TestQuestionSerializer, TestQuestionDetailSerializer, TestQuestionWriteSerializer,
    TestAnswerSerializer, TestAnswerWriteSerializer,
    TestResultSerializer, TestResultListSerializer,
    SubmitTestSerializer,
)


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


class ProfileView(APIView):
    """Foydalanuvchi profili va statistikasi."""
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


# ==================== KATEGORIYALAR ====================

class CategoryListCreateView(generics.ListCreateAPIView):
    """
    GET  - Barcha kategoriyalar (barcha autentifikatsiya qilingan foydalanuvchilar)
    POST - Yangi kategoriya qo'shish (faqat admin)
    """
    queryset = Category.objects.all()

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CategoryWriteSerializer
        return CategoryListSerializer


class CategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    - Kategoriya va videolari (barcha autentifikatsiya qilinganlar)
    PUT    - Kategoriyani yangilash (faqat admin)
    PATCH  - Qisman yangilash (faqat admin)
    DELETE - O'chirish (faqat admin)
    """
    queryset = Category.objects.all()

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return CategoryWriteSerializer
        return CategorySerializer


# ==================== VIDEOLAR ====================

class VideoListCreateView(generics.ListCreateAPIView):
    """
    GET  - Barcha faol videolar. ?category=<id> filter
    POST - Yangi video qo'shish (faqat admin)
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VideoWriteSerializer
        return VideoSerializer

    def get_queryset(self):
        queryset = Video.objects.filter(is_active=True)
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset


class VideoRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    - Video ma'lumotlari (barcha autentifikatsiya qilinganlar)
    PUT    - Yangilash (faqat admin)
    PATCH  - Qisman yangilash (faqat admin)
    DELETE - O'chirish (faqat admin)
    """
    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return VideoWriteSerializer
        return VideoSerializer

    def get_queryset(self):
        return Video.objects.filter(is_active=True)


class VideoStreamView(APIView):
    """Video streaming - yuklab olishni oldini olish. Range request orqali seeking ishlaydi."""
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
    POST - Yangi yo'l belgisi qo'shish (faqat admin)
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RoadSignWriteSerializer
        return RoadSignSerializer

    def get_queryset(self):
        queryset = RoadSign.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        return queryset


class RoadSignRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    - Yo'l belgisi ma'lumotlari (barcha autentifikatsiya qilinganlar)
    PUT    - Yangilash (faqat admin)
    PATCH  - Qisman yangilash (faqat admin)
    DELETE - O'chirish (faqat admin)
    """
    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return RoadSignWriteSerializer
        return RoadSignSerializer

    def get_queryset(self):
        return RoadSign.objects.filter(is_active=True)


# ==================== TEST ====================

class TestQuestionListView(generics.ListCreateAPIView):
    """
    GET  - Kategoriya bo'yicha test savollari. ?category=<id> filter
    POST - Yangi savol qo'shish (faqat admin)
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TestQuestionWriteSerializer
        return TestQuestionSerializer

    def get_queryset(self):
        queryset = TestQuestion.objects.filter(is_active=True)
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset


class TestQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    - Savol ma'lumotlari (barcha autentifikatsiya qilinganlar)
    PUT    - Yangilash (faqat admin)
    PATCH  - Qisman yangilash (faqat admin)
    DELETE - O'chirish (faqat admin)
    """
    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return TestQuestionWriteSerializer
        return TestQuestionDetailSerializer

    def get_queryset(self):
        return TestQuestion.objects.filter(is_active=True)


class TestAnswerListCreateView(generics.ListCreateAPIView):
    """
    GET  - Savol variantlari (faqat admin)
    POST - Yangi variant qo'shish (faqat admin)
    """
    permission_classes = [IsAdminUser]
    serializer_class = TestAnswerWriteSerializer
    queryset = TestAnswer.objects.all()

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
    POST /api/tests/submit/?category=<id>
    Body: {"answers": [{"question_id": answer_id}, ...]}
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=SubmitTestSerializer)
    def post(self, request):
        category_id = request.query_params.get('category')
        if not category_id:
            return Response(
                {"detail": "category query parameter kerak."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return Response(
                {"detail": "Kategoriya topilmadi."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SubmitTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answers_data = serializer.validated_data['answers']
        questions = TestQuestion.objects.filter(
            category=category, is_active=True
        ).prefetch_related('answers')

        if len(answers_data) != questions.count():
            return Response(
                {"detail": f"Barcha savollarga javob berish kerak. Kutilgan: {questions.count()}, Olingan: {len(answers_data)}"},
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
                    {"detail": f"Savol yoki javob topilmadi. Question: {question_id}, Answer: {answer_id}"},
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

        # Natija hisoblash
        total = questions.count()
        score_percent = round((correct_count / total * 100) if total > 0 else 0, 1)
        passed = score_percent >= 70

        # TestResult yaratish
        test_result = TestResult.objects.create(
            user=request.user,
            category=category,
            total_questions=total,
            correct_answers=correct_count,
            score_percent=score_percent,
            passed=passed
        )

        # UserTestAnswer yaratish
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
    """Foydalanuvchining test natijalari"""
    permission_classes = [IsAuthenticated]
    serializer_class = TestResultListSerializer

    def get_queryset(self):
        return TestResult.objects.filter(user=self.request.user)


class TestResultDetailView(generics.RetrieveAPIView):
    """Test natijasining batafsil ma'lumotlari"""
    permission_classes = [IsAuthenticated]
    serializer_class = TestResultSerializer

    def get_queryset(self):
        return TestResult.objects.filter(user=self.request.user)


class TestStatisticsView(APIView):
    """Foydalanuvchining test statistikasi"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        results = TestResult.objects.filter(user=user)

        total_tests = results.count()
        passed_tests = results.filter(passed=True).count()
        avg_score = results.aggregate(models.Avg('score_percent'))['score_percent__avg'] or 0

        category_stats = []
        for category in Category.objects.all():
            cat_results = results.filter(category=category)
            if cat_results.exists():
                best_score = cat_results.aggregate(models.Max('score_percent'))['score_percent__max']
                last_result = cat_results.latest('completed_at')
                category_stats.append({
                    'category_id': category.id,
                    'category_name': category.name,
                    'attempts': cat_results.count(),
                    'best_score': best_score,
                    'last_score': last_result.score_percent,
                    'passed': last_result.passed
                })

        return Response({
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "average_score": round(avg_score, 1),
            "pass_rate": round((passed_tests / total_tests * 100) if total_tests > 0 else 0, 1),
            "category_stats": category_stats
        })
