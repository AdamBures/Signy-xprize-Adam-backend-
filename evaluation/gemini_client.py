import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class GeminiUnavailableError(RuntimeError):
    pass


def model_candidates():
    configured = getattr(settings, 'GEMINI_MODELS', ())
    candidates = [getattr(settings, 'GEMINI_MODEL', ''), *configured]
    return list(dict.fromkeys(model for model in candidates if model))


def generate_with_fallback(contents, *, timeout_ms=10000, max_models=None):
    """Try configured Gemini models in order and return the first valid response."""
    if not settings.GEMINI_API_KEY:
        raise GeminiUnavailableError('Gemini API key is not configured.')

    from google import genai
    from google.genai import types

    errors = []
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=timeout_ms),
    )
    candidates = model_candidates()
    if max_models is not None:
        candidates = candidates[:max_models]
    for model in candidates:
        try:
            response = client.models.generate_content(model=model, contents=contents)
            if response and response.text and response.text.strip():
                return response, model
            errors.append(f'{model}: empty response')
            logger.warning('Gemini model %s returned an empty response', model)
        except Exception as error:
            errors.append(f'{model}: {type(error).__name__}')
            logger.warning('Gemini model %s failed: %s', model, error)

    raise GeminiUnavailableError(
        f'All configured Gemini models failed ({", ".join(errors)}).'
    )
