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
