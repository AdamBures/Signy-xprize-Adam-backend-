import os
import time
import glob
import json
import urllib.request
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings
from google import genai
from lessons.models import Category, Word
from lessons.management.commands.video_to_landmarks import process_video_landmarks

WLASL_JSON_URL = "https://raw.githubusercontent.com/dxli94/WLASL/master/start_kit/WLASL_v0.3.json"

class Command(BaseCommand):
    help = 'Automatically identifies raw videos using WLASL index or Gemini, extracts landmarks, and imports them to the DB (first 1000 free, rest premium)'

    def add_arguments(self, parser):
        parser.add_argument('--folder-path', type=str, default='raw_videos', help='Path to raw videos folder relative to root')
        parser.add_argument('--category', type=str, default='WLASL English Vocabulary', help='Category name')
        parser.add_argument('--limit', type=int, default=None, help='Limit number of videos processed')

    def handle(self, *args, **options):
        folder_path = options['folder_path']
        category_name = options['category']
        limit = options['limit']

        if not os.path.isabs(folder_path):
            folder_path = os.path.join(settings.BASE_DIR, folder_path)

        if not os.path.isdir(folder_path):
            self.stdout.write(self.style.ERROR(f"Folder not found: {folder_path}"))
            return

        # 1. Fetch WLASL Mapping
        self.stdout.write(f"Fetching WLASL dataset index from {WLASL_JSON_URL}...")
        wlasl_mapping = {}
        try:
            req = urllib.request.Request(WLASL_JSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                wlasl_data = json.loads(resp.read().decode('utf-8'))
                for entry in wlasl_data:
                    word = entry.get('gloss', '').title()
                    for inst in entry.get('instances', []):
                        vid_id = inst.get('video_id')
                        if vid_id:
                            # Normalize video_id to 5 digits or whatever format
                            wlasl_mapping[str(vid_id)] = word
                            wlasl_mapping[str(int(vid_id))] = word  # also allow integer string mapping
            self.stdout.write(self.style.SUCCESS(f"Successfully loaded WLASL index. Mapped {len(wlasl_mapping)} video IDs."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not load WLASL index: {e}. Will rely on Gemini Vision for all videos."))

        # 2. Get list of local video files
        video_files = []
        for ext in ['*.mp4', '*.avi', '*.mov', '*.webm']:
            video_files.extend(glob.glob(os.path.join(folder_path, ext)))
            video_files.extend(glob.glob(os.path.join(folder_path, ext.upper())))

        if not video_files:
            self.stdout.write(self.style.WARNING(f"No video files found in: {folder_path}"))
            return

        video_files.sort()
        if limit:
            video_files = video_files[:limit]

        self.stdout.write(self.style.SUCCESS(f"Found {len(video_files)} video files to process."))
        category, _ = Category.objects.get_or_create(name=category_name)

        # Initialize Gemini Client only if needed
        client = None
        api_key = settings.GEMINI_API_KEY

        success_count = 0
        for video_path in video_files:
            filename = os.path.basename(video_path)
            base_name, ext = os.path.splitext(filename)
            
            # Determine word name
            word_name = None
            
            # Try WLASL mapping first
            normalized_id = str(base_name).zfill(5)
            if normalized_id in wlasl_mapping:
                word_name = wlasl_mapping[normalized_id]
                self.stdout.write(f"'{filename}' mapped to '{word_name}' via WLASL index.")
            elif str(base_name) in wlasl_mapping:
                word_name = wlasl_mapping[str(base_name)]
                self.stdout.write(f"'{filename}' mapped to '{word_name}' via WLASL index.")
            
            # Fallback to Gemini if not in mapping
            if not word_name:
                if not api_key:
                    self.stdout.write(self.style.ERROR(f"Skipping '{filename}': Not in WLASL index and GEMINI_API_KEY is not set."))
                    continue
                
                if client is None:
                    client = genai.Client(api_key=api_key)

                self.stdout.write(f"Uploading '{filename}' to Gemini to recognize sign...")
                try:
                    file_ref = client.files.upload(file=video_path)
                    while file_ref.state.name == "PROCESSING":
                        time.sleep(2)
                        file_ref = client.files.get(name=file_ref.name)
                    
                    if file_ref.state.name != "ACTIVE":
                        self.stdout.write(self.style.ERROR(f"Failed to process '{filename}' on Gemini server."))
                        continue

                    response = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=[
                            file_ref,
                            "Identify the sign language word demonstrated in this video. Respond with only the single English word, in Title Case, without extra explanation or punctuation."
                        ]
                    )
                    word_name = response.text.strip().replace('"', '').replace("'", "").replace(".", "")
                    self.stdout.write(self.style.SUCCESS(f"Gemini recognized '{filename}' as '{word_name}'"))
                    
                    # Clean up file ref
                    try:
                        client.files.delete(name=file_ref.name)
                    except Exception:
                        pass
                except Exception as ex:
                    self.stdout.write(self.style.ERROR(f"Gemini recognition error on '{filename}': {ex}"))
                    continue

            if not word_name or len(word_name.split()) > 3:
                self.stdout.write(self.style.WARNING(f"Could not identify a valid word for '{filename}'. Skipping."))
                continue

            # Extract hand landmarks
            self.stdout.write(f"Extracting landmarks for '{word_name}'...")
            try:
                landmarks_sequence = process_video_landmarks(video_path)
                if not landmarks_sequence:
                    self.stdout.write(self.style.WARNING(f"No landmarks detected for '{word_name}'. Skipping."))
                    continue

                slug = slugify(word_name) or word_name.lower().replace(' ', '-')

                # Determine premium state: First 1000 words are free
                free_words_count = Word.objects.filter(is_premium=False).count()
                is_premium = free_words_count >= 1000

                word, created = Word.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'name': word_name,
                        'category': category,
                        'description': f"ASL sign for '{word_name}' from raw video '{filename}'",
                        'video_url': f"/raw_videos/{filename}",
                        'is_premium': is_premium,
                        'reference_landmarks': landmarks_sequence
                    }
                )

                status_str = "created" if created else "updated"
                premium_str = "Premium" if is_premium else "Free"
                self.stdout.write(self.style.SUCCESS(f"Successfully {status_str} '{word_name}' ({len(landmarks_sequence)} frames, {premium_str})."))
                success_count += 1
            except Exception as ex:
                self.stdout.write(self.style.ERROR(f"MediaPipe extraction error on '{filename}': {ex}"))

        self.stdout.write(self.style.SUCCESS(f"Import process complete. Successfully imported {success_count} words."))
