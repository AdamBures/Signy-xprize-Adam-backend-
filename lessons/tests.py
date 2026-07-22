from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from lessons.models import Category, Word

class LessonsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Základní slova", description="Test category")
        self.word1 = Word.objects.create(
            name="Mléko",
            slug="mleko",
            category=self.category,
            description="Znak pro mléko",
            is_premium=False,
            reference_landmarks=[[{"x": 0, "y": 0, "z": 0} for _ in range(21)]]
        )
        self.word2 = Word.objects.create(
            name="Domov",
            slug="domov",
            category=self.category,
            description="Znak pro domov",
            is_premium=True,
            reference_landmarks=[[{"x": 0, "y": 0, "z": 0} for _ in range(21)]]
        )

    def test_list_categories(self):
        url = reverse('category-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_words(self):
        url = reverse('word-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_word_detail(self):
        url = reverse('word-detail', kwargs={'id': self.word1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Mléko')
        self.assertIn('reference_landmarks', response.data)
