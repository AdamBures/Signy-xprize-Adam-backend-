from django.urls import path
from .views import (
    RegisterView, LoginView, UserProfileView, CreateStripeCheckoutSessionView, StripeWebhookView,
    UserPreferencesView, StoreBuyPremiumView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='user-register'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('create-checkout-session/', CreateStripeCheckoutSessionView.as_view(), name='stripe-checkout'),
    path('stripe-webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('me/preferences/', UserPreferencesView.as_view(), name='user-preferences'),
    path('store/buy-premium/', StoreBuyPremiumView.as_view(), name='store-buy-premium'),
]
