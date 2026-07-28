import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.views.generic import TemplateView
from django.db.models import Q

from lessons.models import Word, UserProgress
from .evaluator import evaluate_landmarks
from .gemini_feedback import generate_gemini_feedback
from .gemini_client import GeminiUnavailableError, generate_with_fallback
from django.conf import settings

logger = logging.getLogger(__name__)

class FrontendIndexView(TemplateView):
    template_name = "index.html"

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

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
            # Fallback evaluation when reference landmarks are missing
            eval_result = {
                'score': 85,
                'success': True,
                'issues': []
            }
            feedback_note = " (Poznámka: Systém zatím nemá přesná data pro matematické zhodnocení tohoto znaku.)" if language == 'cs' else " (Note: The system does not have precise reference data to mathematically evaluate this sign yet.)"
        else:
            expected_points = len(ref_landmarks[0]) if ref_landmarks else 21
            valid_user_frames = [
                frame for frame in user_landmarks
                if isinstance(frame, list) and len(frame) == expected_points
            ]
            if not valid_user_frames:
                needs_two_hands = expected_points == 42
                return Response(
                    {
                        'code': 'capture_incomplete',
                        'error': (
                            'We could not capture both hands clearly. Keep both hands visible until capture completes.'
                            if needs_two_hands else
                            'We could not capture your hand clearly. Keep it visible until capture completes.'
                        ),
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            # Perform mathematical evaluation
            eval_result = evaluate_landmarks(
                valid_user_frames,
                ref_landmarks,
                face_metrics=face_metrics,
                reference_face_metrics=word.reference_face_metrics if word.requires_face else None,
                language=language,
            )
            feedback_note = ""

        score = eval_result['score']
        success = eval_result['success']
        issues = eval_result['issues']

        # Persist every attempt, but reward only a genuine personal best.
        xp_gained = 0
        coins_gained = 0
        daily_bonus = 0
        previous_best = 0
        personal_best = score
        improved = True
        
        if request.user.is_authenticated:
            user = request.user
            from users.models import XPEntry
            progress, _ = UserProgress.objects.get_or_create(user=user, word=word)
            previous_best = float(progress.best_score)
            improved = score > previous_best
            if improved:
                xp_gained = 60
                coins_gained = 10
                user.xp += xp_gained
                user.coins += coins_gained
                progress.best_score = score
                user.save(update_fields=['xp', 'coins'])
            if success:
                progress.completed = True
            progress.save()
            personal_best = float(progress.best_score)
            # A zero-value entry records practice activity for streaks without
            # granting XP when the personal best was not improved.
            XPEntry.objects.create(user=user, amount=xp_gained)

        # Persist progress before requesting optional AI coaching. Even if an
        # external model is slow or unavailable, a completed attempt is safe.
        try:
            feedback = generate_gemini_feedback(
                word.name,
                score,
                success,
                issues,
                language=language,
            ) + feedback_note
        except Exception as error:
            logger.warning('Optional coaching feedback failed: %s', error)
            fallback_feedback = {
                'ru': 'Попытка сохранена. Повторите жест медленнее и держите руки полностью в кадре.',
                'cs': 'Pokus byl uložen. Zopakujte znak pomaleji a mějte ruce celé v záběru.',
                'uk': 'Спробу збережено. Повторіть жест повільніше й тримайте руки повністю в кадрі.',
                'en': 'Your attempt was saved. Repeat the sign slowly and keep your hands fully visible.',
            }
            feedback = fallback_feedback.get(language, fallback_feedback['en']) + feedback_note

        return Response({
            'authenticated': request.user.is_authenticated,
            'word_id': word.id,
            'word_name': word.name,
            'score': score,
            'success': success,
            'feedback': feedback,
            'issues': issues,
            'mean_distance': eval_result.get('mean_distance', 0),
            'xp_gained': xp_gained if request.user.is_authenticated else 0,
            'coins_gained': coins_gained if request.user.is_authenticated else 0,
            'daily_bonus': daily_bonus if request.user.is_authenticated else 0,
            'improved': improved,
            'previous_best': previous_best,
            'personal_best': personal_best,
            'current_streak': request.user.current_streak if request.user.is_authenticated else 0,
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
        
        if api_key and not clip:
            return Response(
                {'error': 'A recorded video clip is required for AI translation.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if api_key and clip:
            try:
                from google.genai import types
                prompt = f"""
Analyze this short American Sign Language (ASL) video and translate only
what is visibly signed into a concise sentence in {lang_target}.
Hand landmark samples captured: {len(landmarks)}.
If the signing is not clear enough to translate, respond with UNCLEAR.
Respond ONLY with the translated text without quotes.
"""
                contents=[
                    types.Part.from_bytes(
                        data=clip.read(),
                        mime_type=clip.content_type or 'video/webm',
                    ),
                    prompt,
                ]
                response, model = generate_with_fallback(contents)
                if response and response.text:
                    text = response.text.strip()
                    if text.upper() != 'UNCLEAR':
                        return Response({'text': text, 'confidence': 0.75, 'model': model})
                    return Response(
                        {
                            'code': 'unclear_sign',
                            'error': 'We could not read that sign clearly. Keep your hands fully visible and try once more.',
                        },
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    )
                return Response(
                    {
                        'code': 'empty_translation',
                        'error': 'We could not create a translation from that recording. Please try again.',
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            except GeminiUnavailableError as error:
                logger.warning('All Gemini translation models were unavailable: %s', error)
                return Response(
                    {
                        'code': 'ai_unavailable',
                        'error': 'Our AI translator is taking a short break. Please try again in a moment.',
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            except Exception:
                logger.exception('Unexpected video translation failure')
                return Response(
                    {
                        'code': 'translation_failed',
                        'error': 'Something went wrong while translating. Your recording was not saved. Please try again.',
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

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
