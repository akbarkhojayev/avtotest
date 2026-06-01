from django.urls import path
from .views import (
    LoginView, LogoutView, RegisterView, ProfileView,
    AdminUserListCreateView, AdminUserDetailView,
    VideoListCreateView, VideoRetrieveUpdateDestroyView,
    UpdateProgressView,
    CategoryListCreateView, CategoryDetailView,
    VideoTestQuestionListView, VideoTestSubmitView, VideoTestResultListView,
    RoadSignListCreateView, RoadSignRetrieveUpdateDestroyView,
    RoadSignCategoryListView,
    TestQuestionListView, TestQuestionDetailView,
    TestAnswerListCreateView, TestAnswerDetailView,
    SubmitTestView, TestResultListView, TestResultDetailView,
    TestStatisticsView,
    BookListCreateView, BookRetrieveUpdateDestroyView,
    PaymentRequestCreateView, SubscriptionStatusView,
    PaymentAdminListView, PaymentReviewView, AdminPaymentAddView,
    DashboardView,
    PaymentCardListCreateView, PaymentCardDetailView,
    CommentListCreateView, CommentDetailView,
    SiteSettingsView,
    NotificationListView, NotificationReadView, NotificationReadAllView,
)

urlpatterns = [
    # Dashboard
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),

    # Auth
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path('api/profile/', ProfileView.as_view(), name='profile'),

    # Foydalanuvchilar (admin)
    path('api/users/', AdminUserListCreateView.as_view(), name='admin-user-list'),
    path('api/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),

    # Videolar
    path('api/videos/', VideoListCreateView.as_view(), name='video-list-create'),
    path('api/videos/<int:pk>/', VideoRetrieveUpdateDestroyView.as_view(), name='video-detail'),
    path('api/videos/<int:pk>/progress/', UpdateProgressView.as_view(), name='update-progress'),

    # Video testlari
    path('api/videos/<int:pk>/tests/', VideoTestQuestionListView.as_view(), name='video-test-questions'),
    path('api/videos/<int:pk>/tests/submit/', VideoTestSubmitView.as_view(), name='video-test-submit'),
    path('api/videos/<int:pk>/tests/results/', VideoTestResultListView.as_view(), name='video-test-results'),

    # Yo'l belgilari
    path('api/road-signs/', RoadSignListCreateView.as_view(), name='road-sign-list-create'),
    path('api/road-signs/categories/', RoadSignCategoryListView.as_view(), name='road-sign-categories'),
    path('api/road-signs/<int:pk>/', RoadSignRetrieveUpdateDestroyView.as_view(), name='road-sign-detail'),

    # Kategoriyalar
    path('api/tests/categories/', CategoryListCreateView.as_view(), name='category-list'),
    path('api/tests/categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),

    # Test (umumiy)
    path('api/tests/questions/', TestQuestionListView.as_view(), name='test-question-list'),
    path('api/tests/questions/<int:pk>/', TestQuestionDetailView.as_view(), name='test-question-detail'),
    path('api/tests/answers/', TestAnswerListCreateView.as_view(), name='test-answer-list'),
    path('api/tests/answers/<int:pk>/', TestAnswerDetailView.as_view(), name='test-answer-detail'),
    path('api/tests/submit/', SubmitTestView.as_view(), name='submit-test'),
    path('api/tests/results/', TestResultListView.as_view(), name='test-results'),
    path('api/tests/results/<int:pk>/', TestResultDetailView.as_view(), name='test-result-detail'),
    path('api/tests/statistics/', TestStatisticsView.as_view(), name='test-statistics'),

    # Kitoblar
    path('api/books/', BookListCreateView.as_view(), name='book-list-create'),
    path('api/books/<int:pk>/', BookRetrieveUpdateDestroyView.as_view(), name='book-detail'),

    # To'lov
    path('api/payments/', PaymentRequestCreateView.as_view(), name='payment-list-create'),
    path('api/payments/subscription/', SubscriptionStatusView.as_view(), name='subscription-status'),
    path('api/payments/admin/', PaymentAdminListView.as_view(), name='payment-admin-list'),
    path('api/payments/admin/add/', AdminPaymentAddView.as_view(), name='payment-admin-add'),
    path('api/payments/<int:pk>/review/', PaymentReviewView.as_view(), name='payment-review'),

    # To'lov kartalari
    path('api/cards/', PaymentCardListCreateView.as_view(), name='card-list'),
    path('api/cards/<int:pk>/', PaymentCardDetailView.as_view(), name='card-detail'),

    # Izohlar
    path('api/comments/', CommentListCreateView.as_view(), name='comment-list'),
    path('api/comments/<int:pk>/', CommentDetailView.as_view(), name='comment-detail'),

    # Sayt sozlamalari
    path('api/settings/', SiteSettingsView.as_view(), name='site-settings'),

    # Bildirishnomalar
    path('api/notifications/', NotificationListView.as_view(), name='notification-list'),
    path('api/notifications/<int:pk>/read/', NotificationReadView.as_view(), name='notification-read'),
    path('api/notifications/read-all/', NotificationReadAllView.as_view(), name='notification-read-all'),
]
