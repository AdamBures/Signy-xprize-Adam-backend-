import os
import tempfile
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.text import slugify

from .models import Category, Word, UserProgress
from .serializers import CategorySerializer, WordSerializer, WordListSerializer, UserProgressSerializer

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class WordListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = WordListSerializer

    def get_queryset(self):
        queryset = Word.objects.all()
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

class WordDetailView(generics.RetrieveAPIView):
    queryset = Word.objects.all()
    serializer_class = WordSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

class UserProgressListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        progress = UserProgress.objects.filter(user=request.user)
        serializer = UserProgressSerializer(progress, many=True)
        return Response(serializer.data)

class UploadVideoWordView(APIView):
    """
    API Endpoint allowing admin users or developers to upload an MP4 video file.
    The backend uses OpenCV + MediaPipe to extract hand landmarks and create/update a Word.
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        video_file = request.FILES.get('video')
        word_name = request.data.get('name')
        category_name = request.data.get('category', 'Uploaded Videos')
        is_premium = request.data.get('is_premium', 'false').lower() == 'true'

        if not video_file or not word_name:
            return Response({'error': 'Fields video and name are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Save uploaded file temporarily to process with OpenCV
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
