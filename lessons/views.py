import os
import tempfile
from datetime import timedelta
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.text import slugify
from django.db.models import Avg, Count

from .models import Category, Word, UserProgress
from .serializers import CategorySerializer, WordSerializer, WordListSerializer, UserProgressSerializer

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class WordListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        words = Word.objects.all()
        category_id = request.query_params.get('category')
        if category_id:
            words = words.filter(category_id=category_id)

        # Get completed word IDs if user is authenticated
        completed_word_ids = set()
        user_scores = {}
        if request.user.is_authenticated:
            for p in UserProgress.objects.filter(user=request.user):
                if p.completed:
                    completed_word_ids.add(p.word_id)
                user_scores[p.word_id] = round(p.best_score)

        results = []
        for w in words:
            score_str = f"{user_scores[w.id]}%" if w.id in user_scores else 'New'
            results.append({
                'id': w.id,
                'name': w.name,
                'slug': w.slug,
                'category_name': w.category.name if w.category else 'General',
                'description': w.description,
                'video_url': w.video_url,
                'is_premium': w.is_premium,
                'level': 'Essential' if w.is_premium else 'Beginner',
                'time': '4 min',
                'score': score_str,
                'completed': w.id in completed_word_ids
            })

        return Response({'results': results, 'count': len(results)})

class WordDetailView(generics.RetrieveAPIView):
    queryset = Word.objects.all()
    serializer_class = WordSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

class UserProgressListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            # Fallback for unauthenticated guest
            return Response({
                'streak': 1,
                'completed': 0,
                'accuracy': 0,
                'practice_time': '0m',
                'week_bars': [0, 0, 0, 0, 0, 0, 0],
                'results': []
            })

        user = request.user
        progress_qs = UserProgress.objects.filter(user=user)
        completed_count = progress_qs.filter(completed=True).count()
        total_attempts = progress_qs.count()

        # Real average accuracy
        avg_score = progress_qs.aggregate(Avg('best_score'))['best_score__avg']
        accuracy = round(avg_score, 1) if avg_score is not None else 0.0

        # Real practice time (approx 3 minutes per attempted sign)
        practice_time_minutes = total_attempts * 3
        practice_time_str = f"{practice_time_minutes}m" if practice_time_minutes < 60 else f"{practice_time_minutes // 60}h {practice_time_minutes % 60}m"

        # Real weekly bar chart calculation (Mon..Sun for current week)
        now = timezone.now()
        start_of_week = now.date() - timedelta(days=now.weekday())
        week_bars = [0] * 7

        for p in progress_qs:
            if p.updated_at:
                p_date = p.updated_at.date()
                delta_days = (p_date - start_of_week).days
                if 0 <= delta_days < 7:
                    # Bar height based on score on that day (max 100)
                    week_bars[delta_days] = max(week_bars[delta_days], int(p.best_score))

        # Real streak calculation
        streak = 0
        current_date = now.date()
        while True:
            has_activity = progress_qs.filter(updated_at__date=current_date).exists()
            if has_activity:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                if streak == 0 and current_date == now.date():
                    # Check yesterday if today hasn't had activity yet
                    current_date -= timedelta(days=1)
                    continue
                break

        if streak == 0 and total_attempts > 0:
            streak = 1

        serializer = UserProgressSerializer(progress_qs, many=True)
        return Response({
            'streak': streak,
            'completed': completed_count,
            'accuracy': accuracy,
            'practice_time': practice_time_str,
            'week_bars': week_bars,
            'results': serializer.data
        })

class UploadVideoWordView(APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        video_file = request.FILES.get('video')
        word_name = request.data.get('name')
        category_name = request.data.get('category', 'Uploaded Videos')
        is_premium = request.data.get('is_premium', 'false').lower() == 'true'

        if not video_file or not word_name:
            return Response({'error': 'Fields video and name are required.'}, status=status.HTTP_400_BAD_REQUEST)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
            for chunk in video_file.chunks():
                temp_video.write(chunk)
            temp_video_path = temp_video.name

        try:
            from lessons.management.commands.video_to_landmarks import process_video_landmarks
            landmarks_sequence = process_video_landmarks(temp_video_path)
        except Exception as e:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            return Response({'error': f'Failed to process video with MediaPipe: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

        if not landmarks_sequence:
            return Response({'error': 'No hand landmarks detected in uploaded video.'}, status=status.HTTP_400_BAD_REQUEST)

        category, _ = Category.objects.get_or_create(name=category_name)
        slug = slugify(word_name) or word_name.lower().replace(' ', '-')

        word, created = Word.objects.update_or_create(
            slug=slug,
            defaults={
                'name': word_name,
                'category': category,
                'description': f"Extracted from uploaded video ({len(landmarks_sequence)} frames)",
                'is_premium': is_premium,
                'reference_landmarks': landmarks_sequence
            }
        )

        return Response({
            'message': f"Word '{word_name}' successfully {'created' if created else 'updated'}.",
            'word_id': word.id,
            'frame_count': len(landmarks_sequence),
            'word': WordSerializer(word).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
