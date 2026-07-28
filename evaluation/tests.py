from django.test import TestCase
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from types import SimpleNamespace
from unittest.mock import patch
from lessons.models import Category, Word
from evaluation.evaluator import evaluate_face_metrics, evaluate_landmarks

User = get_user_model()

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
        self.assertFalse(response.data['authenticated'])

    def test_authenticated_attempt_rewards_only_a_new_personal_best(self):
        user = User.objects.create_user(username='learner', password='Password123!')
        self.client.force_authenticate(user=user)
        payload = {
            'word_id': self.word.id,
            'landmarks': [self.landmarks_frame],
            'language': 'en',
        }
        first = self.client.post(reverse('evaluate-sign'), payload, format='json')
        second = self.client.post(reverse('evaluate-sign'), payload, format='json')
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertTrue(first.data['authenticated'])
        self.assertTrue(first.data['improved'])
        self.assertEqual(first.data['xp_gained'], 60)
        self.assertEqual(first.data['coins_gained'], 10)
        self.assertFalse(second.data['improved'])
        self.assertEqual(second.data['xp_gained'], 0)
        self.assertEqual(second.data['coins_gained'], 0)
        progress = user.progress.get(word=self.word)
        self.assertTrue(progress.completed)
        self.assertEqual(progress.best_score, 100.0)
        user.refresh_from_db()
        self.assertEqual(user.xp, 60)
        self.assertEqual(user.coins, 10)

    @patch('evaluation.views.generate_gemini_feedback')
    def test_progress_is_saved_before_optional_ai_feedback(self, feedback):
        feedback.side_effect = RuntimeError('external coaching unavailable')
        user = User.objects.create_user(username='durable', password='Password123!')
        self.client.force_authenticate(user=user)
        payload = {
            'word_id': self.word.id,
            'landmarks': [self.landmarks_frame],
            'language': 'en',
        }

        response = self.client.post(reverse('evaluate-sign'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('attempt was saved', response.data['feedback'])

        progress = user.progress.get(word=self.word)
        self.assertTrue(progress.completed)
        self.assertEqual(progress.best_score, 100.0)
        user.refresh_from_db()
        self.assertEqual(user.xp, 60)
        self.assertEqual(user.coins, 10)

    def test_required_smile_changes_combined_score(self):
        result = evaluate_landmarks(
            [self.landmarks_frame],
            [self.landmarks_frame],
            face_metrics=[{'smile': 0.0}],
            reference_face_metrics={'expression': 'smile'},
        )
        self.assertEqual(result['face_score'], 0.0)
        self.assertEqual(result['score'], 80.0)
        self.assertTrue(result['issues'])

    def test_closed_eyes_marker(self):
        result = evaluate_face_metrics(
            [{'eye_open': 0.005}],
            {'expression': 'eyes_closed'},
        )
        self.assertGreaterEqual(result['score'], 60)
        self.assertEqual(result['issues'], [])

    def test_two_hand_sequence_perfect_match(self):
        second_hand = [
            {**point, 'x': point['x'] + 1.5}
            for point in self.landmarks_frame
        ]
        two_hands = self.landmarks_frame + second_hand
        result = evaluate_landmarks([two_hands], [two_hands], language='ru')
        self.assertEqual(result['score'], 100.0)
        self.assertTrue(result['success'])

    def test_two_hand_match_is_stable_when_camera_order_and_scale_change(self):
        second_hand = [
            {**point, 'x': point['x'] + 1.5}
            for point in self.landmarks_frame
        ]
        reference = self.landmarks_frame + second_hand

        def transform(hand, scale, dx, dy):
            return [
                {
                    'x': point['x'] * scale + dx,
                    'y': point['y'] * scale + dy,
                    'z': point['z'] * scale,
                }
                for point in hand
            ]

        # Simulate a mirrored camera returning the right hand first and each
        # hand at a different position/size in the frame.
        user = transform(second_hand, 0.75, -0.4, 0.2) + transform(
            self.landmarks_frame, 1.25, 0.6, -0.1
        )
        result = evaluate_landmarks([user], [reference], language='en')
        self.assertGreater(result['score'], 95.0)
        self.assertTrue(result['success'])

    def test_incomplete_two_hand_capture_is_not_saved_as_zero(self):
        second_hand = [
            {**point, 'x': point['x'] + 1.5}
            for point in self.landmarks_frame
        ]
        two_hand_word = Word.objects.create(
            name='Help',
            slug='help',
            category=self.category,
            required_hands=2,
            reference_landmarks=[self.landmarks_frame + second_hand],
        )
        user = User.objects.create_user(username='twohands', password='Password123!')
        self.client.force_authenticate(user=user)
        response = self.client.post(
            reverse('evaluate-sign'),
            {
                'word_id': two_hand_word.id,
                'landmarks': [self.landmarks_frame],
                'language': 'en',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data['code'], 'capture_incomplete')
        self.assertFalse(user.progress.filter(word=two_hand_word).exists())

    @override_settings(GEMINI_API_KEY='')
    def test_translate_without_key_returns_explicit_demo(self):
        response = self.client.post(
            reverse('api-v1-translate'),
            {'landmarks': '[]', 'language': 'en'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['demo'])
        self.assertEqual(response.data['confidence'], 0.0)

    @override_settings(GEMINI_API_KEY='test-key', GEMINI_MODEL='gemini-3.5-flash-lite')
    @patch('google.genai.Client')
    def test_translate_clip_uses_gemini(self, client_class):
        client_class.return_value.models.generate_content.return_value = SimpleNamespace(
            text='Please give me some water.'
        )
        clip = SimpleUploadedFile('gesture.webm', b'fake-video', content_type='video/webm')
        response = self.client.post(
            reverse('api-v1-translate'),
            {'clip': clip, 'landmarks': '[]', 'language': 'en'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], 'Please give me some water.')
        self.assertNotIn('demo', response.data)
        client_class.return_value.models.generate_content.assert_called_once()

    @override_settings(
        GEMINI_API_KEY='test-key',
        GEMINI_MODEL='unavailable-model',
        GEMINI_MODELS=('working-model',),
    )
    @patch('google.genai.Client')
    def test_translate_tries_next_gemini_model(self, client_class):
        client_class.return_value.models.generate_content.side_effect = [
            RuntimeError('model unavailable'),
            SimpleNamespace(text='Fallback translation works.'),
        ]
        clip = SimpleUploadedFile('gesture.webm', b'fake-video', content_type='video/webm')
        response = self.client.post(
            reverse('api-v1-translate'),
            {'clip': clip, 'landmarks': '[]', 'language': 'en'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], 'Fallback translation works.')
        self.assertEqual(response.data['model'], 'working-model')
        self.assertEqual(
            client_class.return_value.models.generate_content.call_count,
            2,
        )

    @override_settings(
        GEMINI_API_KEY='test-key',
        GEMINI_MODEL='first-model',
        GEMINI_MODELS=('second-model',),
    )
    @patch('google.genai.Client')
    def test_translate_returns_friendly_error_when_all_models_fail(self, client_class):
        client_class.return_value.models.generate_content.side_effect = RuntimeError(
            'service unavailable'
        )
        clip = SimpleUploadedFile('gesture.webm', b'fake-video', content_type='video/webm')
        response = self.client.post(
            reverse('api-v1-translate'),
            {'clip': clip, 'landmarks': '[]', 'language': 'en'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data['code'], 'ai_unavailable')
        self.assertIn('try again', response.data['error'].lower())
        self.assertNotIn('service unavailable', response.data['error'].lower())

    @override_settings(GEMINI_API_KEY='test-key')
    def test_translate_with_key_requires_clip(self):
        response = self.client.post(
            reverse('api-v1-translate'),
            {'landmarks': '[]', 'language': 'en'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
