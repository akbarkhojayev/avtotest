from django.urls import path
from .views import (
    LoginView, LogoutView, ProfileView,
    VideoListCreateView, VideoRetrieveUpdateDestroyView,
    VideoStreamView, UpdateProgressView,
    RoadSignListCreateView, RoadSignRetrieveUpdateDestroyView,
    RoadSignCategoryListView,
    TestQuestionListView, TestQuestionDetailView,
    TestAnswerListCreateView, TestAnswerDetailView,
    SubmitTestView, TestResultListView, TestResultDetailView,
    TestStatisticsView,
)

urlpatterns = [
    # Auth
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path('api/profile/', ProfileView.as_view(), name='profile'),
    # Videolar
    path('api/videos/', VideoListCreateView.as_view(), name='video-list-create'),
    path('api/videos/<int:pk>/', VideoRetrieveUpdateDestroyView.as_view(), name='video-detail'),
    path('api/videos/<int:pk>/stream/', VideoStreamView.as_view(), name='video-stream'),
    path('api/videos/<int:pk>/progress/', UpdateProgressView.as_view(), name='update-progress'),

    # Yo'l belgilari
    path('api/road-signs/', RoadSignListCreateView.as_view(), name='road-sign-list-create'),
    path('api/road-signs/categories/', RoadSignCategoryListView.as_view(), name='road-sign-categories'),
    path('api/road-signs/<int:pk>/', RoadSignRetrieveUpdateDestroyView.as_view(), name='road-sign-detail'),

    # Test
    path('api/tests/questions/', TestQuestionListView.as_view(), name='test-question-list'),
    path('api/tests/questions/<int:pk>/', TestQuestionDetailView.as_view(), name='test-question-detail'),
    path('api/tests/answers/', TestAnswerListCreateView.as_view(), name='test-answer-list'),
    path('api/tests/answers/<int:pk>/', TestAnswerDetailView.as_view(), name='test-answer-detail'),
    path('api/tests/submit/', SubmitTestView.as_view(), name='submit-test'),
    path('api/tests/results/', TestResultListView.as_view(), name='test-results'),
    path('api/tests/results/<int:pk>/', TestResultDetailView.as_view(), name='test-result-detail'),
    path('api/tests/statistics/', TestStatisticsView.as_view(), name='test-statistics'),
]
