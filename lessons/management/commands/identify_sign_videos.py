import os
import time
import glob
from django.core.management.base import BaseCommand
from django.conf import settings
from google import genai

class Command(BaseCommand):
    help = 'Uses Gemini 1.5 Flash Vision API to identify the ASL sign/word in raw videos and renames the files'

    def add_arguments(self, parser):
        parser.add_argument('--folder-path', type=str, required=True, help='Path to folder containing unidentified raw videos')
        parser.add_argument('--rename', action='store_true', help='Actually rename the files based on Gemini predictions')

    def handle(self, *args, **options):
        folder_path = options['folder_path']
        do_rename = options['rename']

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            self.stdout.write(self.style.ERROR("GEMINI_API_KEY is not set in settings or .env file."))
            return

        if not os.path.isdir(folder_path):
            self.stdout.write(self.style.ERROR(f"Folder not found: {folder_path}"))
            return

        video_files = []
        for ext in ['*.mp4', '*.avi', '*.mov', '*.webm']:
            video_files.extend(glob.glob(os.path.join(folder_path, ext)))
            video_files.extend(glob.glob(os.path.join(folder_path, ext.upper())))

        if not video_files:
            self.stdout.write(self.style.WARNING(f"No video files found in: {folder_path}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {len(video_files)} video files. Initializing Gemini client..."))
        client = genai.Client(api_key=api_key)

        for video_path in video_files:
            filename = os.path.basename(video_path)
            # Skip files that are already capitalized single-word names (to avoid reprocessing if run multiple times)
            base_name, ext = os.path.splitext(filename)
            if base_name.istitle() and '_' not in base_name and '-' not in base_name and len(base_name.split()) == 1:
                self.stdout.write(f"Skipping '{filename}' (appears already named).")
                continue

            self.stdout.write(f"Uploading '{filename}' to Gemini API...")
            try:
                # Upload file
                file_ref = client.files.upload(file=video_path)
                
                # Wait for processing
                self.stdout.write("Waiting for video processing to complete...")
                while file_ref.state.name == "PROCESSING":
                    time.sleep(2)
                    file_ref = client.files.get(name=file_ref.name)

                if file_ref.state.name != "ACTIVE":
                    self.stdout.write(self.style.ERROR(f"Failed to process '{filename}' at Gemini side (State: {file_ref.state.name})"))
                    continue

                # Query Gemini to recognize the sign
                prompt = (
                    "What is the American Sign Language (ASL) sign or word being demonstrated in this video? "
                    "Respond with ONLY the English word or gloss, in Title Case (e.g. 'Milk', 'Water', 'Please'). "
                    "Do not include any introductory text, explanation, quotes, or punctuation."
                )
                
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=[file_ref, prompt]
                )
                
                recognized_word = response.text.strip().replace('"', '').replace("'", "").replace(".", "")
                
                # Validate response: ensure it's not a sentence
                if len(recognized_word.split()) > 3 or not recognized_word:
                    self.stdout.write(self.style.WARNING(f"Gemini returned an unexpected description: '{recognized_word}'. Skipping renaming."))
                    continue

                self.stdout.write(self.style.SUCCESS(f"-> Gemini recognized the sign as: '{recognized_word}'"))

                # Rename the file if requested
                if do_rename:
                    # Keep extension lowercase
                    new_filename = f"{recognized_word}{ext.lower()}"
                    new_path = os.path.join(folder_path, new_filename)
                    
                    if os.path.exists(new_path):
                        # Avoid overwriting
                        new_path = os.path.join(folder_path, f"{recognized_word}_{int(time.time()) % 1000}{ext.lower()}")
                    
                    os.rename(video_path, new_path)
                    self.stdout.write(self.style.SUCCESS(f"Renamed '{filename}' to '{os.path.basename(new_path)}'"))
                else:
                    self.stdout.write(f"Run with --rename flag to rename this file.")

                # Cleanup Gemini file ref to avoid cluttering account storage
                try:
                    client.files.delete(name=file_ref.name)
                except Exception:
                    pass

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing '{filename}': {str(e)}"))

        self.stdout.write(self.style.SUCCESS("Process completed!"))
