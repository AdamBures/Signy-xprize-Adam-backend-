from lessons.models import Category, Word

def run():
    print("Starting database cleaning and categorization...")

    # 1. Delete all words that do not have a video_url
    no_video_words = Word.objects.filter(video_url='')
    count_deleted = no_video_words.count()
    no_video_words.delete()
    print(f"Deleted {count_deleted} Word objects that do not have videos.")

    # 2. Create the unified 'Words' category
    cat, _ = Category.objects.get_or_create(
        name="Words",
        defaults={'description': "All vocabulary words for practice.", 'order': 1}
    )

    # 3. Categorize all remaining words under 'Words'
    words = Word.objects.exclude(video_url='')
    for w in words:
        w.category = cat
        w.save()
        print(f"Word '{w.name}' assigned to Category 'Words'")

    # 4. Clean up any other empty categories
    for c in Category.objects.exclude(id=cat.id):
        print(f"Deleting empty Category '{c.name}'")
        c.delete()

    print("Database cleaning and categorization complete!")
