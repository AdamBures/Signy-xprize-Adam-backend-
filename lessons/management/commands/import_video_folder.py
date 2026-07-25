import os
import glob
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from lessons.models import Category, Word
from lessons.management.commands.video_to_landmarks import process_video_landmarks

class Command(BaseCommand):
    help = 'Processes a folder of MP4/AVI/MOV video files with MediaPipe and extracts 3D hand landmarks into Word models'

    def add_arguments(self, parser):
        parser.add_argument('--folder-path', type=str, required=True, help='Path to local folder containing sign videos')
        parser.add_argument('--category', type=str, default='Imported Videos', help='Category name for the imported words')
        parser.add_argument('--premium', action='store_true', help='Set imported words as premium words')

    def handle(self, *args, **options):
        folder_path = options['folder_path']
        category_name = options['category']
        is_premium = options['premium']

        if not os.path.isdir(folder_path):
            self.stdout.write(self.style.ERROR(f"Folder not found or is not a directory: {folder_path}"))
            return

        # Find all common video formats
        video_extensions = ['*.mp4', '*.avi', '*.mov', '*.webm']
        video_files = []
        for ext in video_extensions:
            video_files.extend(glob.glob(os.path.join(folder_path, ext)))
            video_files.extend(glob.glob(os.path.join(folder_path, ext.upper())))

        if not video_files:
            self.stdout.write(self.style.WARNING(f"No video files found in folder: {folder_path}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {len(video_files)} video files. Starting import..."))
        category, _ = Category.objects.get_or_create(name=category_name)

        success_count = 0
        for video_path in video_files:
            filename = os.path.basename(video_path)
            # Use the filename (without extension) as the word name
            word_name = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
            
            self.stdout.write(f"Processing '{filename}' -> word '{word_name}'...")
            try:
                landmarks_sequence = process_video_landmarks(video_path)
                if not landmarks_sequence:
                    self.stdout.write(self.style.WARNING(f"Skipping '{filename}': No hand landmarks detected."))
                    continue

                slug = slugify(word_name) or word_name.lower().replace(' ', '-')
                word, created = Word.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'name': word_name,
                        'category': category,
                        'description': f"Extracted from custom video file '{filename}' ({len(landmarks_sequence)} frames)",
                        'is_premium': is_premium,
                        'reference_landmarks': landmarks_sequence
                    }
                )
                status_str = "created" if created else "updated"
                self.stdout.write(self.style.SUCCESS(f"Successfully {status_str} word '{word_name}' ({len(landmarks_sequence)} frames)."))
                success_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing '{filename}': {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Import complete! Successfully imported {success_count} of {len(video_files)} videos."))
