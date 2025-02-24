from rest_framework import serializers
from accounts.models import Profile
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(style={'input_type': 'password'}, source='password2', write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'password', 'confirm_password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.pop('password2')  # used 'pop' method as 'password2 is not defined in User model'
        if password != password2:
            raise serializers.ValidationError(
                {"status": "error", "Message": "Password and Confirm Password Doesn't Match"})
        return attrs

    def create(self, validated_data):
        # validated_data = self.validated_data
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        profile = Profile.objects.create(user=user)

        return user

class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.ReadOnlyField(source='user.email')
    first_name = serializers.ReadOnlyField(source='user.first_name')
    last_name = serializers.ReadOnlyField(source='user.last_name')
    is_email_verified = serializers.ReadOnlyField(source="user.is_email_verified")

    class Meta:
        model = Profile
        fields = ['id', 'email', 'first_name', 'last_name', 'is_email_verified', 'mobile_number', 'gender', 'profile_pic', 'date_of_birth']

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'username']
        extra_kwargs = {'email': {'read_only': True}}

class UserDetailsSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False)
    is_email_verified = serializers.ReadOnlyField(source="user.is_email_verified")

    class Meta:
        model = Profile
        fields = ['id', 'profile_pic', 'user', 'is_email_verified', 'mobile_number', 'gender', 'profile_pic', 'date_of_birth']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        instance = super().update(instance, validated_data)

        if user_data:
            user = instance.user
            user.username = user_data.get('username', user.username)
            user.first_name = user_data.get('first_name', user.first_name)
            user.last_name = user_data.get('last_name', user.last_name)
            user.save()
        return instance
