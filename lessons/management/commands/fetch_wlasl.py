import json
import urllib.request
import os
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from lessons.models import Category, Word

WLASL_JSON_URL = "https://raw.githubusercontent.com/dxli94/WLASL/master/start_kit/WLASL_v0.3.json"

class Command(BaseCommand):
    help = 'Downloads or parses WLASL dataset and imports words into database automatically'

    def add_arguments(self, parser):
        parser.add_argument('--json-path', type=str, default='', help='Optional local path to WLASL_v0.3.json')
        parser.add_argument('--limit', type=int, default=50, help='Maximum number of words to import')

    def handle(self, *args, **options):
        json_path = options.get('json_path')
        limit = options.get('limit', 50)

        wlasl_data = None

        if json_path and os.path.exists(json_path):
            self.stdout.write(f"Reading local WLASL file: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                wlasl_data = json.load(f)
        else:
            self.stdout.write(f"Fetching WLASL dataset index directly from GitHub ({WLASL_JSON_URL})...")
            try:
                req = urllib.request.Request(WLASL_JSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    wlasl_data = json.loads(resp.read().decode('utf-8'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to download WLASL dataset directly: {e}"))
                self.stdout.write(self.style.WARNING("Tip: Download WLASL_v0.3.json manually and use --json-path WLASL_v0.3.json"))
                return

        if not wlasl_data:
            self.stdout.write(self.style.ERROR("No WLASL data loaded."))
            return

        category, _ = Category.objects.get_or_create(
            name="WLASL English Vocabulary",
            defaults={'description': 'Word-Level American Sign Language Benchmark Dataset', 'order': 10}
        )

        imported_count = 0
        for entry in wlasl_data[:limit]:
            gloss_name = entry.get('gloss', '').title()
            if not gloss_name:
                continue

            slug = slugify(gloss_name) or gloss_name.lower().replace(' ', '-')
            
            instances = entry.get('instances', [])
            ref_lms = []
            video_url = ""
            for inst in instances:
                if 'url' in inst and not video_url:
                    video_url = inst.get('url', '')
                if 'landmarks' in inst:
                    ref_lms = inst['landmarks']
                    break

            Word.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': gloss_name,
                    'category': category,
                    'description': f"ASL sign for '{gloss_name}' from WLASL benchmark dataset.",
                    'video_url': video_url,
                    'is_premium': False if imported_count < 15 else True,
                    'reference_landmarks': ref_lms
                }
            )
            imported_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully imported {imported_count} words from WLASL dataset into database!"))
