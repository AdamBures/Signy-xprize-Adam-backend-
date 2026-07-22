from django.urls import path
from .views import CategoryListView, WordListView, WordDetailView, UserProgressListView, UploadVideoWordView

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('words/', WordListView.as_view(), name='word-list'),
    path('words/<int:id>/', WordDetailView.as_view(), name='word-detail'),
    path('progress/', UserProgressListView.as_view(), name='user-progress'),
    path('upload-video-word/', UploadVideoWordView.as_view(), name='upload-video-word'),
]
