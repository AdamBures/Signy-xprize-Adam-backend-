from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    has_premium = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'is_subscribed', 'first_name', 'last_name', 'avatar',
            'language_level', 'daily_goal_minutes', 'onboarding_completed', 'xp', 'coins',
            'premium_expires_at', 'has_premium', 'country', 'pronouns', 'skin_tone'
        ]
        read_only_fields = ['id', 'is_subscribed', 'xp', 'coins', 'premium_expires_at', 'has_premium']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'avatar']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            avatar=validated_data.get('avatar', '👤')
        )
        return user
