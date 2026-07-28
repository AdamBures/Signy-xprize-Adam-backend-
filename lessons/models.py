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
    video_url_en = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='English sign-language guide used for English and Czech UI',
    )
    video_url_ru = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Russian sign-language guide used for Russian UI',
    )
    is_premium = models.BooleanField(default=False)
    requires_face = models.BooleanField(
        default=False,
        help_text="Whether non-manual facial markers are part of this sign",
    )
    required_hands = models.PositiveSmallIntegerField(
        default=1,
        help_text="Number of hands required for the sign (1 or 2)",
    )
    guidance = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional learner guidance: tip, placement and movement",
    )
    reference_face_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Expected normalized facial metrics for non-manual markers",
    )
    # reference_landmarks stores an array of frames, each frame being an array of 21 landmark dicts/lists {"x": ..., "y": ..., "z": ...}
    reference_landmarks = models.JSONField(default=list, help_text="List of landmark frames for reference comparison")
    unlock_requirement = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='unlocks')
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
