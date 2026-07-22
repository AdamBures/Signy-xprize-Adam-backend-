from django.contrib import admin
from .models import Category, Word, UserProgress

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'description']
    search_fields = ['name']
    ordering = ['order', 'name']

@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_premium', 'created_at']
    list_filter = ['category', 'is_premium']
    search_fields = ['name', 'description', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'word', 'best_score', 'completed', 'updated_at']
    list_filter = ['completed', 'word__category']
    search_fields = ['user__username', 'word__name']
