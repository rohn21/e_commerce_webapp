from django.urls import path, include
from accounts.views import UserCreateAPIView, ProfileAPIView
from dj_rest_auth.views import LoginView, LogoutView
from dj_rest_auth.registration.views import (RegisterView,
                                             ConfirmEmailView, ResendEmailVerificationView, VerifyEmailView
                                             )

app_name = 'accounts'

urlpatterns = [
    # path('user/', UserCreateAPIView.as_view(), name='user-create'),
    path('login/', LoginView.as_view(), name='rest_login'),
    path('logout/', LogoutView.as_view(), name='rest_logout'),
    path('register/', UserCreateAPIView.as_view(), name='rest_register'),
    path('user/profile/<int:pk>/', ProfileAPIView.as_view(), name='user_profile'),
]