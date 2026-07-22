from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_subscribed = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    avatar = models.TextField(blank=True, default='👤')

    def __str__(self):
        return self.username or self.email
