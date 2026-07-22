from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class Word(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='words', null=True, blank=True)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    video_url = models.URLField(blank=True, default='')
    is_premium = models.BooleanField(default=False)
    # reference_landmarks stores an array of frames, each frame being an array of 21 landmark dicts/lists {"x": ..., "y": ..., "z": ...}
    reference_landmarks = models.JSONField(default=list, help_text="List of landmark frames for reference comparison")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress')
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='user_attempts')
    best_score = models.FloatField(default=0.0)
    completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'word')

    def __str__(self):
        return f"{self.user.username} - {self.word.name}: {self.best_score}%"
