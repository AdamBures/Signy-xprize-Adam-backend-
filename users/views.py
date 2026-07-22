import stripe
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .serializers import UserSerializer, RegisterSerializer

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        if not user:
            # Fallback to email login if username fails
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            })
        return Response({'error': 'Neplatné přihlašovací údaje (Invalid credentials)'}, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

class CreateStripeCheckoutSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not settings.STRIPE_SECRET_KEY:
            # Fallback for dev mode when Stripe API key is not yet set
            return Response({
                'checkout_url': f"{settings.FRONTEND_URL}/payment-success?mock=true",
                'message': 'Development mode: Stripe key not configured. Mock checkout link returned.'
            })

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': 'AI Tutor Znakové řeči - Plný přístup',
                                'description': 'Odemkne všechny lekce a AI zpětnou vazbu v reálném čase',
                            },
                            'unit_amount': 1000,  # $10.00 USD
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                client_reference_id=str(request.user.id),
                customer_email=request.user.email or None,
                success_url=f"{settings.FRONTEND_URL}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/payment-cancel",
            )
            return Response({'checkout_url': checkout_session.url})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        if settings.STRIPE_WEBHOOK_SECRET and sig_header:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
                )
            except (ValueError, stripe.error.SignatureVerificationError):
                return HttpResponse(status=400)
        else:
            # If webhook secret is not set, parse payload directly for testing
            import json
            try:
                event = json.loads(payload)
            except Exception:
                return HttpResponse(status=400)

        event_type = event.get('type') if isinstance(event, dict) else event['type']
        data_object = event.get('data', {}).get('object', {}) if isinstance(event, dict) else event['data']['object']

        if event_type == 'checkout.session.completed':
            user_id = data_object.get('client_reference_id')
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    user.is_subscribed = True
                    user.stripe_customer_id = data_object.get('customer')
                    user.save()
                except User.DoesNotExist:
                    pass

        return HttpResponse(status=200)
