from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from lessons.models import Category, Word
from evaluation.evaluator import evaluate_landmarks

class EvaluationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Základní slova")
        
        # Sample 21 landmarks
        self.landmarks_frame = [
            {'x': 0.0, 'y': 0.0, 'z': 0.0}, # wrist
            {'x': -0.1, 'y': 0.2, 'z': 0.0}, {'x': -0.2, 'y': 0.3, 'z': 0.0}, {'x': -0.3, 'y': 0.4, 'z': 0.0}, {'x': -0.4, 'y': 0.5, 'z': 0.0}, # thumb
            {'x': -0.1, 'y': 0.5, 'z': 0.0}, {'x': -0.1, 'y': 0.7, 'z': 0.0}, {'x': -0.1, 'y': 0.9, 'z': 0.0}, {'x': -0.1, 'y': 1.0, 'z': 0.0}, # index
            {'x': 0.0, 'y': 0.5, 'z': 0.0}, {'x': 0.0, 'y': 0.7, 'z': 0.0}, {'x': 0.0, 'y': 0.9, 'z': 0.0}, {'x': 0.0, 'y': 1.1, 'z': 0.0}, # middle
            {'x': 0.1, 'y': 0.5, 'z': 0.0}, {'x': 0.1, 'y': 0.7, 'z': 0.0}, {'x': 0.1, 'y': 0.9, 'z': 0.0}, {'x': 0.1, 'y': 1.0, 'z': 0.0}, # ring
            {'x': 0.2, 'y': 0.4, 'z': 0.0}, {'x': 0.2, 'y': 0.6, 'z': 0.0}, {'x': 0.2, 'y': 0.7, 'z': 0.0}, {'x': 0.2, 'y': 0.8, 'z': 0.0}, # pinky
        ]

        self.word = Word.objects.create(
            name="Mléko",
            slug="mleko",
            category=self.category,
            is_premium=False,
            reference_landmarks=[self.landmarks_frame]
        )

    def test_evaluator_perfect_match(self):
        result = evaluate_landmarks([self.landmarks_frame], [self.landmarks_frame])
        self.assertEqual(result['score'], 100.0)
        self.assertTrue(result['success'])

    def test_evaluate_sign_api_endpoint(self):
        url = reverse('evaluate-sign')
        payload = {
            'word_id': self.word.id,
            'landmarks': [self.landmarks_frame]
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['word_name'], 'Mléko')
        self.assertEqual(response.data['score'], 100.0)
        self.assertTrue(response.data['success'])
        self.assertIn('feedback', response.data)
