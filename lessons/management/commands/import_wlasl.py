import json
import os
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from lessons.models import Category, Word

class Command(BaseCommand):
    help = 'Imports words and MediaPipe landmark vectors from WLASL (Word-Level American Sign Language) JSON dataset file'

    def add_arguments(self, parser):
        parser.add_argument('--json-path', type=str, help='Path to WLASL JSON file (e.g. WLASL_v0.3.json)')
        parser.add_argument('--limit', type=int, default=100, help='Maximum number of words to import')

    def handle(self, *args, **options):
        json_path = options.get('json_path')
        limit = options.get('limit', 100)

        if not json_path or not os.path.exists(json_path):
            self.stdout.write(self.style.WARNING("No valid WLASL JSON file provided or file does not exist."))
            self.stdout.write(self.style.WARNING("Usage: python manage.py import_wlasl --json-path path/to/WLASL.json --limit 500"))
            self.stdout.write("Information on getting WLASL dataset:")
            self.stdout.write("  1. Download WLASL dataset JSON from: https://github.com/dxli94/WLASL")
            self.stdout.write("  2. Run: python manage.py import_wlasl --json-path WLASL_v0.3.json")
            return

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                wlasl_data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to read WLASL file: {e}"))
            return

        category, _ = Category.objects.get_or_create(
            name="WLASL English Vocabulary",
            defaults={'description': 'Word-Level American Sign Language Benchmark Dataset'}
        )

        imported_count = 0
        for entry in wlasl_data[:limit]:
            gloss_name = entry.get('gloss', '').title()
            if not gloss_name:
                continue

            slug = slugify(gloss_name) or gloss_name.lower().replace(' ', '-')
            
            # Extract landmarks if available in instances or generate reference structure
            instances = entry.get('instances', [])
            ref_lms = []
            for inst in instances:
                if 'landmarks' in inst:
                    ref_lms = inst['landmarks']
                    break

            Word.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': gloss_name,
                    'category': category,
                    'description': f"ASL sign for '{gloss_name}' from WLASL dataset.",
                    'is_premium': False if imported_count < 20 else True,
                    'reference_landmarks': ref_lms
                }
            )
            imported_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully imported {imported_count} English ASL words from WLASL dataset."))
