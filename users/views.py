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

def format_user_data(user):
    data = UserSerializer(user).data
    data['name'] = user.get_full_name() or user.username
    return data

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data.copy()
        username = data.get('username') or data.get('email')
        email = data.get('email', '')

        if not username:
            return Response({'error': 'Username or email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        data['username'] = username

        if User.objects.filter(username=username).exists():
            return Response({'error': 'A user with that username or email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        if email and User.objects.filter(email=email).exists():
            return Response({'error': 'A user with that username or email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        if 'name' in data and 'first_name' not in data:
            name_parts = data['name'].split(' ', 1)
            data['first_name'] = name_parts[0]
            if len(name_parts) > 1:
                data['last_name'] = name_parts[1]

        serializer = RegisterSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            user_data = format_user_data(user)
            return Response({
                'token': token.key,
                'access': token.key,
                'user': user_data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username') or request.data.get('email')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        if not user and username:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user:
            token, _ = Token.objects.get_or_create(user=user)
            user_data = format_user_data(user)
            return Response({
                'token': token.key,
                'access': token.key,
                'user': user_data
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'name': 'Guest User', 'email': 'guest@example.com', 'is_subscribed': False, 'avatar': '👤'})
        return Response(format_user_data(request.user))

    def patch(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        avatar = request.data.get('avatar')
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if request.user.is_authenticated:
            user = request.user
            if new_password:
                if current_password and not user.check_password(current_password):
                    return Response({'error': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
                if len(new_password) < 6:
                    return Response({'error': 'New password must be at least 6 characters long.'}, status=status.HTTP_400_BAD_REQUEST)
                user.set_password(new_password)

            if name:
                parts = name.split(' ', 1)
                user.first_name = parts[0]
                user.last_name = parts[1] if len(parts) > 1 else ''
            if email:
                user.email = email
            if avatar:
                user.avatar = avatar

            user.save()
            return Response(format_user_data(user))
        else:
            return Response({
                'name': name or 'Alex Morgan',
                'email': email or 'alex@example.com',
                'avatar': avatar or '👤',
                'is_subscribed': False
            })

class CreateStripeCheckoutSessionView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user_id = str(request.user.id) if request.user.is_authenticated else 'guest'
        user_email = request.user.email if request.user.is_authenticated and request.user.email else None

        if not settings.STRIPE_SECRET_KEY:
            return Response({
                'url': f"{settings.FRONTEND_URL}/#pricing?payment=success",
                'message': 'Development mode: Mock checkout link returned.'
            })

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': 'HandSign - Family Full Access',
                                'description': 'Unlock all sign language lessons & real-time Gemini AI coaching',
                            },
                            'unit_amount': 1000,  # $10.00 USD
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                client_reference_id=user_id,
                customer_email=user_email,
                success_url=f"{settings.FRONTEND_URL}/#pricing?payment=success",
                cancel_url=f"{settings.FRONTEND_URL}/#pricing?payment=cancelled",
            )
            return Response({'url': checkout_session.url})
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
            import json
            try:
                event = json.loads(payload)
            except Exception:
                return HttpResponse(status=400)

        event_type = event.get('type') if isinstance(event, dict) else event['type']
        data_object = event.get('data', {}).get('object', {}) if isinstance(event, dict) else event['data']['object']

        if event_type == 'checkout.session.completed':
            user_id = data_object.get('client_reference_id')
            if user_id and user_id != 'guest':
                try:
                    user = User.objects.get(id=user_id)
                    user.is_subscribed = True
                    user.stripe_customer_id = data_object.get('customer')
                    user.save()
                except User.DoesNotExist:
                    pass

        return HttpResponse(status=200)


from django.db.models import Q
from users.models import Friendship

class FriendshipListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # 1. Friends list (accepted friendships)
        friendships = Friendship.objects.filter(
            (Q(from_user=user) | Q(to_user=user)) & Q(status='accepted')
        )
        friends_data = []
        for f in friendships:
            friend = f.to_user if f.from_user == user else f.from_user
            friends_data.append({
                'id': friend.id,
                'username': friend.username,
                'name': friend.get_full_name() or friend.username,
                'avatar': friend.avatar,
                'streak': friend.current_streak
            })

        # Sort friends by streak descending (gamification scoreboard!)
        friends_data.sort(key=lambda x: x['streak'], reverse=True)

        # 2. Pending incoming requests
        pending_requests = Friendship.objects.filter(to_user=user, status='pending')
        requests_data = []
        for r in pending_requests:
            requests_data.append({
                'id': r.id,
                'from_user': {
                    'id': r.from_user.id,
                    'username': r.from_user.username,
                    'name': r.from_user.get_full_name() or r.from_user.username,
                    'avatar': r.from_user.avatar
                }
            })

        # 3. Suggestions (other users who are not friends or pending requests)
        exclude_user_ids = [user.id]
        all_relations = Friendship.objects.filter(Q(from_user=user) | Q(to_user=user))
        for r in all_relations:
            exclude_user_ids.append(r.from_user_id)
            exclude_user_ids.append(r.to_user_id)
        
        exclude_user_ids = list(set(exclude_user_ids))
        suggestions = User.objects.exclude(id__in=exclude_user_ids)[:5]
        suggestions_data = []
        for s in suggestions:
            suggestions_data.append({
                'id': s.id,
                'username': s.username,
                'name': s.get_full_name() or s.username,
                'avatar': s.avatar,
                'streak': s.current_streak
            })

        return Response({
            'friends': friends_data,
            'requests': requests_data,
            'suggestions': suggestions_data
        })

class FriendshipRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        to_user_id = request.data.get('to_user_id')
        username = request.data.get('username')

        to_user = None
        if to_user_id:
            try:
                to_user = User.objects.get(id=to_user_id)
            except User.DoesNotExist:
                return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        elif username:
            try:
                to_user = User.objects.get(username=username)
            except User.DoesNotExist:
                return Response({'error': 'User with that username not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not to_user:
            return Response({'error': 'to_user_id or username required.'}, status=status.HTTP_400_BAD_REQUEST)

        if to_user == user:
            return Response({'error': 'You cannot add yourself as a friend.'}, status=status.HTTP_400_BAD_REQUEST)

        exists = Friendship.objects.filter(
            (Q(from_user=user) & Q(to_user=to_user)) | (Q(from_user=to_user) & Q(to_user=user))
        ).first()

        if exists:
            if exists.status == 'accepted':
                return Response({'error': 'You are already friends.'}, status=status.HTTP_400_BAD_REQUEST)
            elif exists.status == 'pending':
                if exists.from_user == user:
                    return Response({'error': 'Friend request already sent and pending.'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    exists.status = 'accepted'
                    exists.save()
                    return Response({'message': 'Friend request accepted automatically.', 'status': 'accepted'})
            else:
                exists.status = 'pending'
                exists.from_user = user
                exists.to_user = to_user
                exists.save()
                return Response({'message': 'Friend request sent.', 'status': 'pending'})

        Friendship.objects.create(from_user=user, to_user=to_user, status='pending')
        return Response({'message': 'Friend request sent.', 'status': 'pending'})

class FriendshipRespondView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        friendship_id = request.data.get('friendship_id')
        action = request.data.get('action')

        if not friendship_id or action not in ['accept', 'reject']:
            return Response({'error': 'friendship_id and valid action (accept/reject) required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            friendship = Friendship.objects.get(id=friendship_id, to_user=user, status='pending')
        except Friendship.DoesNotExist:
            return Response({'error': 'Friend request not found.'}, status=status.HTTP_404_NOT_FOUND)

        if action == 'accept':
            friendship.status = 'accepted'
            friendship.save()
            return Response({'message': 'Friend request accepted.'})
        else:
            friendship.status = 'rejected'
            friendship.save()
            return Response({'message': 'Friend request rejected.'})

