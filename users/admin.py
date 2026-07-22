from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_subscribed', 'is_staff', 'is_superuser']
    list_filter = ['is_subscribed', 'is_staff', 'is_superuser', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Stripe Subscription Info', {'fields': ('is_subscribed', 'stripe_customer_id', 'stripe_subscription_id')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Stripe Subscription Info', {'fields': ('is_subscribed', 'stripe_customer_id', 'stripe_subscription_id')}),
    )
