import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.views.generic import TemplateView
from django.db.models import Q

from lessons.models import Word, UserProgress
from .evaluator import evaluate_landmarks
from .gemini_feedback import generate_gemini_feedback
from django.conf import settings

class FrontendIndexView(TemplateView):
    template_name = "index.html"

class HealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({'status': 'ok', 'service': 'HandSign AI Tutor Backend', 'version': '1.0.0'})

class EvaluateSignView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        lesson_identifier = request.data.get('lesson') or request.data.get('word_id')
        user_landmarks = request.data.get('landmarks', [])
        face_metrics = request.data.get('face_metrics', [])
        language = request.data.get('language', 'cs')

        if not lesson_identifier:
            return Response({'error': 'Parameter lesson or word_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Lookup word by ID, name, or slug
        word = None
        if isinstance(lesson_identifier, int) or (isinstance(lesson_identifier, str) and lesson_identifier.isdigit()):
            try:
                word = Word.objects.get(id=int(lesson_identifier))
            except Word.DoesNotExist:
                pass

        if not word and isinstance(lesson_identifier, str):
            word = Word.objects.filter(
                Q(name__iexact=lesson_identifier) | Q(slug__iexact=lesson_identifier)
            ).first()

        if not word:
            return Response(
                {'error': 'Lesson not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check premium access
        if word.is_premium and request.user.is_authenticated and not request.user.is_subscribed:
            return Response(
                {'error': 'This lesson requires a premium family subscription.', 'requires_subscription': True},
                status=status.HTTP_403_FORBIDDEN
            )

        ref_landmarks = word.reference_landmarks
        if not ref_landmarks:
            return Response(
                {'error': 'This lesson does not have reference landmarks yet.'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Perform mathematical evaluation
        eval_result = evaluate_landmarks(
            user_landmarks,
            ref_landmarks,
            face_metrics=face_metrics,
            reference_face_metrics=word.reference_face_metrics if word.requires_face else None,
            language=language,
        )
        score = eval_result['score']
        success = eval_result['success']
        issues = eval_result['issues']

        # Generate natural language feedback via Gemini API in target language
        feedback = generate_gemini_feedback(word.name, score, success, issues, language=language)

        # Update User progress and award XP / Coins if user is authenticated
        xp_gained = 10
        coins_gained = 0
        
        if request.user.is_authenticated:
            user = request.user
            user.xp += 10
            if success:
                user.xp += 50
                user.coins += 5
                xp_gained += 50
                coins_gained += 5
            user.save()
            
            from users.models import XPEntry
            XPEntry.objects.create(user=user, amount=xp_gained)

            progress, _ = UserProgress.objects.get_or_create(user=user, word=word)
            if score > progress.best_score:
                progress.best_score = score
            if success:
                progress.completed = True
            progress.save()

        return Response({
            'word_id': word.id,
            'word_name': word.name,
            'score': score,
            'success': success,
            'feedback': feedback,
            'issues': issues,
            'mean_distance': eval_result.get('mean_distance', 0),
            'xp_gained': xp_gained if request.user.is_authenticated else 0,
            'coins_gained': coins_gained if request.user.is_authenticated else 0,
            'current_xp': request.user.xp if request.user.is_authenticated else 0,
            'current_coins': request.user.coins if request.user.is_authenticated else 0
        })

class TranslateClipView(APIView):
    """
    API Endpoint for Free-Form Sign Translation using Gemini API.
    Translates recorded hand landmarks or video clips into natural text.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        language = request.data.get('language', 'en')
        raw_landmarks = request.data.get('landmarks', '[]')
        
        if isinstance(raw_landmarks, str):
            try:
                landmarks = json.loads(raw_landmarks)
            except Exception:
                landmarks = []
        else:
            landmarks = raw_landmarks

        api_key = settings.GEMINI_API_KEY
        clip = request.FILES.get('clip')
        
        # System prompt for sign translation
        lang_target = "English" if language == 'en' else "Czech" if language == 'cs' else "Ukrainian" if language == 'uk' else "Russian"
        
        if api_key and clip:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=api_key)
                prompt = f"""
Analyze this short American Sign Language (ASL) video and translate only
what is visibly signed into a concise sentence in {lang_target}.
Hand landmark samples captured: {len(landmarks)}.
If the signing is not clear enough to translate, respond with UNCLEAR.
Respond ONLY with the translated text without quotes.
"""
                response = client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=[
                        types.Part.from_bytes(
                            data=clip.read(),
                            mime_type=clip.content_type or 'video/webm',
                        ),
                        prompt,
                    ],
                )
                if response and response.text:
                    text = response.text.strip()
                    if text.upper() != 'UNCLEAR':
                        return Response({'text': text, 'confidence': 0.75})
            except Exception:
                pass

        # Smart fallback translation when Gemini key is offline or processing sample
        translations = {
            'en': "Hello, I would like some water, please.",
            'cs': "Dobrý den, prosím o trochu vody.",
            'uk': "Доброго дня, дайте, будь ласка, трохи води.",
            'ru': "Здравствуйте, дайте, пожалуйста, немного воды."
        }
        return Response({
            'text': translations.get(language, translations['en']),
            'confidence': 0.0,
            'demo': True,
        })
