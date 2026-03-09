from django.contrib import admin

from .models import Word


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ("english_word", "ukrainian_translation", "transcription", "created_at")
    search_fields = ("english_word", "ukrainian_translation", "context_sentence")
    prepopulated_fields = {"slug": ("english_word",)}
