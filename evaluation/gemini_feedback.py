import logging
from django.conf import settings

logger = logging.getLogger(__name__)

LANGUAGE_PROMPTS = {
    'cs': 'v češtině',
    'en': 'in English',
    'uk': 'українською мовою (Ukrainian)',
    'ru': 'на русском языке (Russian)'
}

def generate_gemini_feedback(word_name, score, success, issues, language='cs'):
    """
    Uses Gemini API to generate friendly, constructive feedback in the requested language (cs, en, uk, ru).
    """
    lang_instruction = LANGUAGE_PROMPTS.get(language, 'v češtině')

    if success:
        success_messages = {
            'cs': f"Skvělá práce! Znak pro '{word_name}' jsi provedl(a) správně. Pokračuj v dalším tréninku!",
            'en': f"Great job! You performed the sign for '{word_name}' correctly. Keep up the practice!",
            'uk': f"Чудова робота! Ви правильно виконали жест для '{word_name}'. Продовжуйте тренуватися!",
            'ru': f"Отличная работа! Вы правильно выполнили жест для '{word_name}'. Продолжайте тренироваться!"
        }
        return success_messages.get(language, success_messages['en'])

    issues_str = "\n- ".join(issues) if issues else "Tvar ruky neodpovídal vzoru."
    
    prompt = f"""
You are a friendly AI sign language tutor assisting parents of children with delayed speech or autism.
Your task is to give encouraging, short, and very practical advice based on a sign gesture attempt.

The user attempted the sign for: "{word_name}".
Accuracy score: {score}% (success threshold is 65%).
Detected alignment issues:
- {issues_str}

Write a short advice (max 2 sentences) strictly {lang_instruction} on how to improve the gesture.
Be warm, positive, and specific. Respond ONLY with the advice text without quotes or introductory preamble.
"""

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        if issues:
            return f"Good try for '{word_name}'! Adjust execution: {issues[0]}"
        return f"Good try for '{word_name}'! Bring hand closer to reference pattern and repeat."

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logger.warning(f"Gemini API call failed: {e}")

    return f"Good try for '{word_name}'! Try repeating the gesture closer to the pattern."
