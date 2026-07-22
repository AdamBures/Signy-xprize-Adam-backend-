import os
import cv2
import mediapipe as mp
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from lessons.models import Category, Word

def process_video_landmarks(video_path, max_frames=60):
    """
    Extracts 21 3D MediaPipe hand landmarks for each frame in a video file using OpenCV & MediaPipe.
    """
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    cap = cv2.VideoCapture(video_path)
    sequence = []
    frame_count = 0

    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            hand_lms = results.multi_hand_landmarks[0]
            frame_coords = []
            for lm in hand_lms.landmark:
                frame_coords.append({
                    'x': round(lm.x, 4),
                    'y': round(lm.y, 4),
                    'z': round(lm.z, 4)
                })
            sequence.append(frame_coords)
            frame_count += 1

    cap.release()
    hands.close()
    return sequence

class Command(BaseCommand):
    help = 'Processes an MP4 video file with MediaPipe and extracts 3D hand landmarks into a Word model'

    def add_arguments(self, parser):
        parser.add_argument('--video-path', type=str, required=True, help='Path to local MP4 video file')
        parser.add_argument('--word-name', type=str, required=True, help='Name of the word (e.g. Milk, Apple)')
        parser.add_argument('--category', type=str, default='Custom Videos', help='Category name')
        parser.add_argument('--premium', action='store_true', help='Set as premium word')

    def handle(self, *args, **options):
        video_path = options['video_path']
        word_name = options['word_name']
        category_name = options['category']
        is_premium = options['premium']

        if not os.path.exists(video_path):
            self.stdout.write(self.style.ERROR(f"Video file not found: {video_path}"))
            return

        self.stdout.write(f"Processing video '{video_path}' with MediaPipe...")
        landmarks_sequence = process_video_landmarks(video_path)

        if not landmarks_sequence:
            self.stdout.write(self.style.ERROR("No hand landmarks were detected in the video."))
            return

        category, _ = Category.objects.get_or_create(name=category_name)
        slug = slugify(word_name) or word_name.lower().replace(' ', '-')

        word, created = Word.objects.update_or_create(
            slug=slug,
            defaults={
                'name': word_name,
                'category': category,
                'description': f"Extracted from video '{os.path.basename(video_path)}' ({len(landmarks_sequence)} frames)",
                'is_premium': is_premium,
                'reference_landmarks': landmarks_sequence
            }
        )

        status_str = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Successfully {status_str} word '{word_name}' with {len(landmarks_sequence)} landmark frames!"))
