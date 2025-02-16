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

class UserDetailsSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()
    is_email_verified = serializers.ReadOnlyField(source='user.is_email_verified')

    class Meta:
        model = Profile
        fields = ['id', 'profile_pic', 'user', 'is_email_verified']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        user_instance = instance.user_profile

        if user_data:
            user_serializer = CustomUserSerializer(user_instance, data=user_data, partial=True)  # Partial updates for user
            if user_serializer.is_valid():
                user_serializer.save()  # Save changes to the user
            else:
                raise serializers.ValidationError(user_serializer.errors)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
