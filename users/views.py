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
            
            # Send welcome email
            from django.core.mail import send_mail
            try:
                send_mail(
                    subject="Vítej v aplikaci HandSign! 🤟",
                    message=f"Ahoj {user.first_name or user.username},\n\nvítáme tě v aplikaci HandSign – tvém osobním průvodci výukou znakového jazyka! Přihlas se, projdi si onboarding a začni trénovat s kamerou.\n\nHodně štěstí,\nTým HandSign",
                    from_email="noreply@handsign.cz",
                    recipient_list=[user.email or "user@example.com"],
                    fail_silently=True
                )
            except Exception:
                pass

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
        country = request.data.get('country')
        pronouns = request.data.get('pronouns')
        skin_tone = request.data.get('skin_tone')

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
            if country is not None:
                user.country = country
            if pronouns is not None:
                user.pronouns = pronouns
            if skin_tone is not None:
                user.skin_tone = skin_tone
            if 'daily_goal_minutes' in request.data:
                try:
                    user.daily_goal_minutes = int(request.data['daily_goal_minutes'])
                except ValueError:
                    pass
            if request.data.get('onboarding_completed') is True:
                user.onboarding_completed = True

            user.save()
            return Response(format_user_data(user))
        else:
            return Response({
                'name': name or 'Alex Morgan',
                'email': email or 'alex@example.com',
                'avatar': avatar or '👤',
                'is_subscribed': False,
                'country': country or '',
                'pronouns': pronouns or '',
                'skin_tone': skin_tone or 'default'
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

                    # Send payment confirmation email
                    from django.core.mail import send_mail
                    try:
                        send_mail(
                            subject="Potvrzení platby – HandSign 💳",
                            message=f"Ahoj {user.first_name or user.username},\n\nděkujeme za zakoupení rodinného předplatného HandSign Family Full Access ($10.00 USD)!\n\nTvoje platba proběhla úspěšně a všechny prémiové lekce a Gemini AI koučování byly pro tvůj účet plně odemčeny.\n\nPřejeme spoustu zábavy při výuce,\nTým HandSign",
                            from_email="billing@handsign.cz",
                            recipient_list=[user.email or "user@example.com"],
                            fail_silently=True
                        )
                    except Exception:
                        pass
                except User.DoesNotExist:
                    pass

        return HttpResponse(status=200)


from django.db.models import Q
from users.models import Friendship

class FriendshipListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        friends_page = int(request.query_params.get('friends_page', 1))
        requests_page = int(request.query_params.get('requests_page', 1))
        page_size = 20

        # 1. Friends list (accepted friendships)
        friendships_qs = Friendship.objects.filter(
            (Q(from_user=user) | Q(to_user=user)) & Q(status='accepted')
        )
        total_friends = friendships_qs.count()
        friendships = friendships_qs[(friends_page-1)*page_size : friends_page*page_size]
        friends_next = f"?friends_page={friends_page+1}" if total_friends > friends_page*page_size else None
        
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
        pending_qs = Friendship.objects.filter(to_user=user, status='pending')
        total_requests = pending_qs.count()
        pending_requests = pending_qs[(requests_page-1)*page_size : requests_page*page_size]
        requests_next = f"?requests_page={requests_page+1}" if total_requests > requests_page*page_size else None
        
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
            'friends_next': friends_next,
            'requests': requests_data,
            'requests_next': requests_next,
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


from django.utils import timezone

class UserPreferencesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        language_level = request.data.get('language_level')
        daily_goal_minutes = request.data.get('daily_goal_minutes')

        if language_level:
            user.language_level = language_level
        if daily_goal_minutes:
            try:
                user.daily_goal_minutes = int(daily_goal_minutes)
            except ValueError:
                pass

        user.onboarding_completed = True
        user.save()
        return Response(format_user_data(user))

class StoreBuyPremiumView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        cost = 500  # 500 coins for 24 hours of premium
        if user.coins < cost:
            return Response({'error': f'Nedostatek mincí. Potřebuješ {cost} mincí.'}, status=status.HTTP_400_BAD_REQUEST)

        user.coins -= cost
        # Add 24 hours to premium_expires_at
        now = timezone.now()
        if user.premium_expires_at and user.premium_expires_at > now:
            user.premium_expires_at = user.premium_expires_at + timezone.timedelta(hours=24)
        else:
            user.premium_expires_at = now + timezone.timedelta(hours=24)
        user.save()
        return Response({
            'message': 'Premium aktivováno na 24 hodin!',
            'user': format_user_data(user)
        })

class LeaderboardView(APIView):
    def get(self, request):
        timeframe = request.query_params.get('timeframe', 'all_time')
        country = request.query_params.get('country', 'global')

        from users.models import User, XPEntry
        from django.db.models import Sum

        users_qs = User.objects.filter(is_active=True, is_staff=False)
        if country and country != 'global':
            users_qs = users_qs.filter(country=country)

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 50

        if timeframe == 'all_time':
            users = users_qs.order_by('-xp')
            page = paginator.paginate_queryset(users, request, view=self)
            
            data = []
            for u in (page if page is not None else users):
                if u.xp > 0:
                    data.append({
                        'username': u.username,
                        'avatar': u.avatar or '👤',
                        'xp': u.xp,
                        'country': u.country
                    })
        else:
            now = timezone.now()
            if timeframe == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif timeframe == 'week':
                start_date = now - timezone.timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif timeframe == 'month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = now

            # Filter XPEntries
            entries = XPEntry.objects.filter(created_at__gte=start_date)
            # Group by user and sum amount
            user_xps = entries.values('user').annotate(total_xp=Sum('amount')).order_by('-total_xp')
            
            page = paginator.paginate_queryset(user_xps, request, view=self)
            
            data = []
            for entry in (page if page is not None else user_xps):
                try:
                    u = users_qs.get(id=entry['user'])
                    data.append({
                        'username': u.username,
                        'avatar': u.avatar or '👤',
                        'xp': entry['total_xp'],
                        'country': u.country
                    })
                except User.DoesNotExist:
                    pass
                    
        if page is not None:
            return paginator.get_paginated_response(data)

        return Response({'leaderboard': data})

class ActiveCountriesView(APIView):
    def get(self, request):
        from users.models import User
        countries = User.objects.exclude(country='').values_list('country', flat=True).distinct()[:50]
        return Response({'countries': list(countries)})

