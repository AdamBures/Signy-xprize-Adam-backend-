from lessons.models import Category, Word
from django.utils.text import slugify

def run():
    print("Starting database cleaning and categorization...")

    # 1. Delete all words that do not have a video_url
    no_video_words = Word.objects.filter(video_url='')
    count_deleted = no_video_words.count()
    no_video_words.delete()
    print(f"Deleted {count_deleted} Word objects that do not have videos.")

    # 2. Create the new categories if they don't exist
    cats_data = [
        ("Základy a Komunikace (ASL)", "Základní slova, zdvořilostní obraty a základní porozumění v americké znakové řeči.", 1),
        ("Rodina a Lidé (ASL)", "Členové rodiny, lidé a sociální okruhy v americké znakové řeči.", 2),
        ("Místa a Akce (ASL)", "Znaky pro domov, země, akce a každodenní aktivity.", 3),
        ("Abeceda (ASL)", "Znaková reprezentace jednotlivých písmen abecedy.", 4),
    ]

    categories = {}
    for name, desc, order in cats_data:
        cat, _ = Category.objects.get_or_create(
            name=name,
            defaults={'description': desc, 'order': order}
        )
        categories[name] = cat

    # 3. Categorize remaining words
    words = Word.objects.exclude(video_url='')
    
    people_words = ['mother', 'father', 'sister', 'brother', 'baby', 'aunt', 'actor', 'adopt', 'friend', 'teacher', 'doctor']
    places_actions = ['home', 'australia', 'play', 'stop', 'sleep', 'want', 'go', 'work', 'school', 'eat', 'drink', 'water', 'milk']

    for w in words:
        name_lower = w.name.lower()
        if name_lower.startswith('letter '):
            w.category = categories["Abeceda (ASL)"]
        elif any(p in name_lower for p in people_words):
            w.category = categories["Rodina a Lidé (ASL)"]
        elif any(pa in name_lower for pa in places_actions):
            w.category = categories["Místa a Akce (ASL)"]
        else:
            w.category = categories["Základy a Komunikace (ASL)"]
        w.save()
        print(f"Word '{w.name}' assigned to Category '{w.category.name}'")

    # 4. Clean up any empty categories
    for cat in Category.objects.all():
      if cat.words.count() == 0:
        print(f"Deleting empty Category '{cat.name}'")
        cat.delete()

    print("Database cleaning and categorization complete!")
