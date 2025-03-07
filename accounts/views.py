from django.shortcuts import render
from django.contrib.auth import authenticate, login
from rest_framework import generics, permissions, authentication, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from dj_rest_auth.registration.views import RegisterView
from allauth.account.utils import send_email_confirmation
from allauth.account.signals import user_signed_up
from accounts.models import Profile
from accounts.serializers import (
    CustomUserSerializer, UserProfileSerializer, UserDetailsSerializer
)
from accounts.permissions import IsOwnerOrReadonly
from django.contrib.auth import get_user_model

User = get_user_model()

class UserCreateAPIView(RegisterView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        user_signed_up.send(sender=self.__class__, request=self.request, user=user)  #manual trigger of signal
        return user

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # user = self.perform_create(serializer)
        # send_email_confirmation(request, user)  # when ACCOUNT_EMAIL_VERIFICATION is 'mandatory'

        headers = self.get_success_headers(serializer.validated_data)

        return Response({"detail": "Check the inbox and confirm your email !!!"}, status=status.HTTP_201_CREATED, headers=headers)


class ProfileAPIView(generics.RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = UserDetailsSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsOwnerOrReadonly]

    def get_object(self):
        user = self.request.user
        profile, created = Profile.objects.get_or_create(user=user)
        return profile