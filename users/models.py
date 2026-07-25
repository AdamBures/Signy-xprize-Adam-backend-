from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_subscribed = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    avatar = models.TextField(blank=True, default='👤')

    @property
    def current_streak(self):
        from lessons.models import UserProgress
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        progress_qs = UserProgress.objects.filter(user=self)
        streak = 0
        current_date = now.date()
        while True:
            has_activity = progress_qs.filter(updated_at__date=current_date).exists()
            if has_activity:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                if streak == 0 and current_date == now.date():
                    current_date -= timedelta(days=1)
                    continue
                break
        return streak

    def __str__(self):
        return self.username or self.email


class Friendship(models.Model):
    from_user = models.ForeignKey(User, related_name='sent_friendships', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_friendships', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"
