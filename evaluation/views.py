from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from lessons.models import Word, UserProgress
from .evaluator import evaluate_landmarks
from .gemini_feedback import generate_gemini_feedback

class EvaluateSignView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        word_id = request.data.get('word_id')
        user_landmarks = request.data.get('landmarks', [])

        if not word_id:
            return Response({'error': 'Parametr word_id je povinný.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            word = Word.objects.get(id=word_id)
        except Word.DoesNotExist:
            return Response({'error': f'Slovo s ID {word_id} nebylo nalezeno.'}, status=status.HTTP_404_NOT_FOUND)

        # Check premium access
        if word.is_premium:
            if not request.user.is_authenticated or not request.user.is_subscribed:
                return Response(
                    {'error': 'Tato lekce vyžaduje přístup k premiovému balíčku.', 'requires_subscription': True},
                    status=status.HTTP_403_FORBIDDEN
                )

        ref_landmarks = word.reference_landmarks
        if not ref_landmarks:
            # Fallback if reference landmarks are missing for a newly created word
            return Response({
                'score': 100.0,
                'success': True,
                'feedback': f"Pohyb pro znak '{word.name}' byl úspěšně přijat.",
                'issues': []
            })

        language = request.data.get('language', 'cs')

        # Perform mathematical evaluation
        eval_result = evaluate_landmarks(user_landmarks, ref_landmarks)
        score = eval_result['score']
        success = eval_result['success']
        issues = eval_result['issues']

        # Generate natural language feedback via Gemini API in target language (cs, en, uk, ru)
        feedback = generate_gemini_feedback(word.name, score, success, issues, language=language)

        # Update User progress if user is authenticated
        if request.user.is_authenticated:
            progress, _ = UserProgress.objects.get_or_create(user=request.user, word=word)
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
            'mean_distance': eval_result.get('mean_distance', 0)
        })
