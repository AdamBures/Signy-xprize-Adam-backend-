import os
from django.contrib import admin
from django.urls import path, include
from django.views.static import serve
from django.conf import settings

from evaluation.views import FrontendIndexView, HealthCheckView, EvaluateSignView, TranslateClipView
from users.views import RegisterView, LoginView, UserProfileView, CreateStripeCheckoutSessionView
from lessons.views import WordListView, UserProgressListView

urlpatterns = [
    # Frontend SPA index page at root
    path('', FrontendIndexView.as_view(), name='frontend-index'),

    # Serve root frontend static files directly
    path('styles.css', serve, {'document_root': settings.BASE_DIR, 'path': 'styles.css'}),
    path('app.js', serve, {'document_root': settings.BASE_DIR, 'path': 'app.js'}),
    path('api.js', serve, {'document_root': settings.BASE_DIR, 'path': 'api.js'}),
    path('i18n.js', serve, {'document_root': settings.BASE_DIR, 'path': 'i18n.js'}),
    path('raw_videos/<path:path>', serve, {'document_root': os.path.join(settings.BASE_DIR, 'raw_videos')}),

    # Admin portal
    path('admin/', admin.site.urls),

    # HandSign API v1 Endpoints (expected by app.js / api.js)
    path('api/v1/health/', HealthCheckView.as_view(), name='api-v1-health'),
    path('api/v1/auth/register/', RegisterView.as_view(), name='api-v1-register'),
    path('api/v1/auth/login/', LoginView.as_view(), name='api-v1-login'),
    path('api/v1/lessons/', WordListView.as_view(), name='api-v1-lessons'),
    path('api/v1/me/progress/', UserProgressListView.as_view(), name='api-v1-progress'),
    path('api/v1/me/', UserProfileView.as_view(), name='api-v1-me'),
    path('api/v1/practice/evaluate/', EvaluateSignView.as_view(), name='api-v1-evaluate'),
    path('api/v1/translate/', TranslateClipView.as_view(), name='api-v1-translate'),
    path('api/v1/billing/checkout/', CreateStripeCheckoutSessionView.as_view(), name='api-v1-checkout'),

    # Modular API routes
    path('api/users/', include('users.urls')),
    path('api/lessons/', include('lessons.urls')),
    path('api/evaluation/', include('evaluation.urls')),
]
