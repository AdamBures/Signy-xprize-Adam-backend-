import math
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from lessons.models import Category, Word

def generate_hand_landmarks(gesture_type='open_palm', frames=6):
    """
    Generates realistic 21-point MediaPipe hand landmark sequence for demo/seed data.
    MediaPipe indices:
    0: Wrist
    1..4: Thumb
    5..8: Index
    9..12: Middle
    13..16: Ring
    17..20: Pinky
    """
    sequence = []

    for t in range(frames):
        alpha = t / max(1, frames - 1)
        frame_lms = []

        # Wrist
        frame_lms.append({'x': 0.0, 'y': 0.0, 'z': 0.0})

        if gesture_type == 'fist':
            curl = 0.2
        elif gesture_type == 'milk':
            squeezing = math.sin(alpha * math.pi)
            curl = 0.8 - (0.6 * squeezing)
        elif gesture_type == 'index_point':
            curl = 0.8
        else:
            curl = 0.8

        # Thumb (1..4)
        for i in range(1, 5):
            factor = i / 4.0
            frame_lms.append({
                'x': round(-0.3 * factor, 4),
                'y': round(0.4 * factor * (0.8 if gesture_type == 'fist' else 1.0), 4),
                'z': round(-0.1 * factor, 4)
            })

        # Index (5..8)
        is_index_extended = gesture_type in ('open_palm', 'index_point', 'milk')
        for i in range(1, 5):
            factor = (4 + i) / 8.0
            curlm = 1.0 if is_index_extended else 0.3
            frame_lms.append({
                'x': round(-0.2 * factor, 4),
                'y': round(0.7 * factor * curlm, 4),
                'z': round(0.0, 4)
            })

        # Middle (9..12)
        is_middle_extended = gesture_type in ('open_palm', 'milk')
        for i in range(1, 5):
            factor = (4 + i) / 8.0
            curlm = 1.0 if is_middle_extended else 0.3
            frame_lms.append({
                'x': round(0.0, 4),
                'y': round(0.8 * factor * curlm, 4),
                'z': round(0.0, 4)
            })

        # Ring (13..16)
        is_ring_extended = gesture_type == 'open_palm'
        for i in range(1, 5):
            factor = (4 + i) / 8.0
            curlm = 1.0 if is_ring_extended else 0.3
            frame_lms.append({
                'x': round(0.2 * factor, 4),
                'y': round(0.7 * factor * curlm, 4),
                'z': round(0.0, 4)
            })

        # Pinky (17..20)
        is_pinky_extended = gesture_type == 'open_palm'
        for i in range(1, 5):
            factor = (4 + i) / 8.0
            curlm = 1.0 if is_pinky_extended else 0.3
            frame_lms.append({
                'x': round(0.3 * factor, 4),
                'y': round(0.6 * factor * curlm, 4),
                'z': round(0.0, 4)
            })

        sequence.append(frame_lms)

    return sequence

class Command(BaseCommand):
    help = 'Seeds initial categories and 40+ English ASL sign words with reference MediaPipe landmarks'

    def handle(self, *args, **options):
        self.stdout.write("Seeding English ASL categories and words...")

        categories_data = [
            {'name': 'Basic Words', 'description': 'Essential first words for daily communication', 'order': 1},
            {'name': 'Family & People', 'description': 'Signs for family members and people', 'order': 2},
            {'name': 'Food & Drinks', 'description': 'Signs for food, beverages, and mealtime', 'order': 3},
            {'name': 'Emotions & Actions', 'description': 'Expressing feelings and common actions', 'order': 4},
            {'name': 'ASL Alphabet', 'description': 'Fingerspelling letters A through Z', 'order': 5},
        ]

        cat_objs = {}
        for c in categories_data:
            cat, _ = Category.objects.get_or_create(
                name=c['name'],
                defaults={'description': c['description'], 'order': c['order']}
            )
            cat_objs[c['name']] = cat

        words_data = [
            # Food & Drinks
            {'name': 'Milk', 'category': 'Food & Drinks', 'gesture': 'milk', 'premium': False, 'desc': 'Squeeze hand open and closed as if milking a cow.'},
            {'name': 'Water', 'category': 'Food & Drinks', 'gesture': 'index_point', 'premium': False, 'desc': 'Form W-shape with index, middle, ring finger at chin.'},
            {'name': 'Eat / Food', 'category': 'Food & Drinks', 'gesture': 'fist', 'premium': False, 'desc': 'Bring flattened O-hand shape to mouth repeatedly.'},
            {'name': 'Drink', 'category': 'Food & Drinks', 'gesture': 'fist', 'premium': False, 'desc': 'Form C-shape with hand as if tipping a cup to mouth.'},
            {'name': 'Apple', 'category': 'Food & Drinks', 'gesture': 'fist', 'premium': True, 'desc': 'Twist knuckle of index finger against cheek.'},
            {'name': 'Cookie', 'category': 'Food & Drinks', 'gesture': 'fist', 'premium': True, 'desc': 'Twist curved hand on palm as if cutting out a cookie.'},

            # Family & People
            {'name': 'Mother', 'category': 'Family & People', 'gesture': 'open_palm', 'premium': False, 'desc': 'Tap thumb of open hand to chin.'},
            {'name': 'Father', 'category': 'Family & People', 'gesture': 'open_palm', 'premium': False, 'desc': 'Tap thumb of open hand to forehead.'},
            {'name': 'Baby / Child', 'category': 'Family & People', 'gesture': 'open_palm', 'premium': False, 'desc': 'Cradle arms side-to-side as if rocking a baby.'},
            {'name': 'Brother', 'category': 'Family & People', 'gesture': 'index_point', 'premium': True, 'desc': 'L-hands moving from forehead down to touch.'},
            {'name': 'Sister', 'category': 'Family & People', 'gesture': 'index_point', 'premium': True, 'desc': 'L-hands moving from chin down to touch.'},

            # Basic Words
            {'name': 'Help', 'category': 'Basic Words', 'gesture': 'fist', 'premium': False, 'desc': 'Place fist on open palm and lift up together.'},
            {'name': 'Please', 'category': 'Basic Words', 'gesture': 'open_palm', 'premium': False, 'desc': 'Rub flat open palm in circular motion on chest.'},
            {'name': 'Thank You', 'category': 'Basic Words', 'gesture': 'open_palm', 'premium': False, 'desc': 'Touch fingers to chin and move hand forward towards person.'},
            {'name': 'Yes', 'category': 'Basic Words', 'gesture': 'fist', 'premium': False, 'desc': 'Nod S-hand shape up and down like a head nodding.'},
            {'name': 'No', 'category': 'Basic Words', 'gesture': 'index_point', 'premium': False, 'desc': 'Snap index and middle finger together with thumb.'},
            {'name': 'More', 'category': 'Basic Words', 'gesture': 'fist', 'premium': False, 'desc': 'Tap fingertips of both hands together repeatedly.'},
            {'name': 'Finished / All Done', 'category': 'Basic Words', 'gesture': 'open_palm', 'premium': False, 'desc': 'Flick open hands outward twice.'},
            {'name': 'Home', 'category': 'Basic Words', 'gesture': 'fist', 'premium': True, 'desc': 'Touch fingertips from mouth to cheek.'},
            {'name': 'Love', 'category': 'Basic Words', 'gesture': 'fist', 'premium': True, 'desc': 'Cross both fists over chest in an X shape.'},

            # Emotions & Actions
            {'name': 'Happy', 'category': 'Emotions & Actions', 'gesture': 'open_palm', 'premium': False, 'desc': 'Pat open palm upward against chest repeatedly.'},
            {'name': 'Sad', 'category': 'Emotions & Actions', 'gesture': 'open_palm', 'premium': False, 'desc': 'Bring open hands down face while tilting head slightly.'},
            {'name': 'Play', 'category': 'Emotions & Actions', 'gesture': 'open_palm', 'premium': False, 'desc': 'Twist Y-hand shapes at wrist back and forth.'},
            {'name': 'Sleep', 'category': 'Emotions & Actions', 'gesture': 'open_palm', 'premium': False, 'desc': 'Draw open hand down face closing into a flattened fist.'},
            {'name': 'Stop', 'category': 'Emotions & Actions', 'gesture': 'open_palm', 'premium': True, 'desc': 'Chop edge of open hand down into flat palm.'},
            {'name': 'Want', 'category': 'Emotions & Actions', 'gesture': 'open_palm', 'premium': True, 'desc': 'Reach out with clawed hands and pull inward.'},

            # ASL Alphabet (A-Z sample)
            {'name': 'Letter A', 'category': 'ASL Alphabet', 'gesture': 'fist', 'premium': False, 'desc': 'Fist with thumb resting against side of index finger.'},
            {'name': 'Letter B', 'category': 'ASL Alphabet', 'gesture': 'open_palm', 'premium': False, 'desc': 'Four fingers straight up with thumb tucked across palm.'},
            {'name': 'Letter C', 'category': 'ASL Alphabet', 'gesture': 'open_palm', 'premium': False, 'desc': 'Curved hand forming C shape.'},
            {'name': 'Letter D', 'category': 'ASL Alphabet', 'gesture': 'index_point', 'premium': False, 'desc': 'Index finger up, other fingers forming O with thumb.'},
            {'name': 'Letter E', 'category': 'ASL Alphabet', 'gesture': 'fist', 'premium': True, 'desc': 'All fingers curled tightly down touching thumb.'},
            {'name': 'Letter F', 'category': 'ASL Alphabet', 'gesture': 'open_palm', 'premium': True, 'desc': 'Index and thumb touching in circle, other 3 fingers up.'},
            {'name': 'Letter G', 'category': 'ASL Alphabet', 'gesture': 'index_point', 'premium': True, 'desc': 'Index and thumb pointing sideways parallel.'},
            {'name': 'Letter H', 'category': 'ASL Alphabet', 'gesture': 'index_point', 'premium': True, 'desc': 'Index and middle finger pointing sideways together.'},
            {'name': 'Letter I', 'category': 'ASL Alphabet', 'gesture': 'open_palm', 'premium': True, 'desc': 'Pinky finger up, other fingers in a fist.'},
            {'name': 'Letter L', 'category': 'ASL Alphabet', 'gesture': 'index_point', 'premium': True, 'desc': 'Thumb and index finger extended at right angle forming L.'},
        ]

        created_count = 0
        for w in words_data:
            slug = slugify(w['name'])
            if not slug:
                slug = w['name'].lower().replace(' ', '-')
            
            lms = generate_hand_landmarks(gesture_type=w['gesture'], frames=6)
            
            word, created = Word.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': w['name'],
                    'category': cat_objs[w['category']],
                    'description': w['desc'],
                    'is_premium': w['premium'],
                    'reference_landmarks': lms
                }
            )
            if created:
                created_count += 1

        # Ensure root superuser exists
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username='root').exists():
            User.objects.create_superuser('root', 'root@example.com', 'root')
            self.stdout.write(self.style.SUCCESS("Superuser 'root' (heslo: 'root') byl vytvoren."))
        else:
            u = User.objects.get(username='root')
            u.set_password('root')
            u.is_superuser = True
            u.is_staff = True
            u.save()
            self.stdout.write(self.style.SUCCESS("Superuser 'root' byl aktualizovan."))

        self.stdout.write(self.style.SUCCESS(f"Uspesne vytvoreno/aktualizovano {len(words_data)} anglickych ASL slovicek ({created_count} novych)."))
