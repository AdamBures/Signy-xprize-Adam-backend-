from rest_framework import serializers
from .models import Category, Word, UserProgress

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'order']

class WordSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = Word
        fields = [
            'id', 'category', 'category_name', 'name', 'slug',
            'description', 'video_url', 'is_premium', 'reference_landmarks'
        ]

class WordListSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = Word
        # Exclude heavy reference_landmarks from general list query for speed
        fields = ['id', 'category', 'category_name', 'name', 'slug', 'description', 'video_url', 'is_premium']

class UserProgressSerializer(serializers.ModelSerializer):
    word_name = serializers.ReadOnlyField(source='word.name')

    class Meta:
        model = UserProgress
        fields = ['id', 'word', 'word_name', 'best_score', 'completed', 'updated_at']
