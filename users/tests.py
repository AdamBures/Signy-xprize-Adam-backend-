from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class UserAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('user-register')
        self.login_url = reverse('user-login')
        self.profile_url = reverse('user-profile')

    def test_register_user(self):
        data = {
            'username': 'testparent',
            'email': 'parent@example.com',
            'password': 'Password123!',
            'first_name': 'Jan',
            'last_name': 'Novák'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['username'], 'testparent')

    def test_login_user(self):
        User.objects.create_user(username='testparent', password='Password123!')
        data = {
            'username': 'testparent',
            'password': 'Password123!'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_get_user_profile(self):
        user = User.objects.create_user(username='testparent', password='Password123!')
        self.client.force_authenticate(user=user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testparent')
        self.assertFalse(response.data['is_subscribed'])


class FriendshipTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='user1', password='Password123!')
        self.user2 = User.objects.create_user(username='user2', password='Password123!')
        self.user3 = User.objects.create_user(username='user3', password='Password123!')

        self.friends_url = reverse('api-v1-friends')
        self.request_url = reverse('api-v1-friends-request')
        self.respond_url = reverse('api-v1-friends-respond')

    def test_send_friend_request_and_accept(self):
        # Authenticate as user1
        self.client.force_authenticate(user=self.user1)

        # 1. Send request to user2
        response = self.client.post(self.request_url, {'username': 'user2'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'pending')

        # 2. Check pending request is visible to user2
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(self.friends_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['requests']), 1)
        self.assertEqual(response.data['requests'][0]['from_user']['username'], 'user1')

        # 3. Accept the request
        req_id = response.data['requests'][0]['id']
        response = self.client.post(self.respond_url, {'friendship_id': req_id, 'action': 'accept'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 4. Verify user1 and user2 are now friends
        response = self.client.get(self.friends_url)
        self.assertEqual(len(response.data['friends']), 1)
        self.assertEqual(response.data['friends'][0]['username'], 'user1')

