from django.contrib import admin

from .models import TranslationOption, Word


class TranslationOptionInline(admin.TabularInline):
    model = TranslationOption
    extra = 1
    fields = ("text", "part_of_speech", "priority", "usage_note")
    ordering = ("priority", "id")


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = (
        "english_word",
        "source_language",
        "target_language",
        "ukrainian_translation",
        "transcription",
        "created_at",
    )
    list_filter = ("source_language", "target_language")
    search_fields = (
        "english_word",
        "ukrainian_translation",
        "context_sentence",
        "translation_options__text",
    )
    prepopulated_fields = {"slug": ("english_word",)}
    inlines = [TranslationOptionInline]


@admin.register(TranslationOption)
class TranslationOptionAdmin(admin.ModelAdmin):
    list_display = ("text", "part_of_speech", "priority", "word")
    list_filter = ("part_of_speech",)
    search_fields = ("text", "usage_note", "word__english_word")
