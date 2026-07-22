from django.urls import path
from .views import RegisterView, LoginView, UserProfileView, CreateStripeCheckoutSessionView, StripeWebhookView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='user-register'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('create-checkout-session/', CreateStripeCheckoutSessionView.as_view(), name='stripe-checkout'),
    path('stripe-webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
