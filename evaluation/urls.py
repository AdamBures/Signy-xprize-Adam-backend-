from django.urls import path
from .views import EvaluateSignView

urlpatterns = [
    path('evaluate/', EvaluateSignView.as_view(), name='evaluate-sign'),
]
