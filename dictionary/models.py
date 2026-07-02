from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class LanguageCode(models.TextChoices):
    ENGLISH = "en", "English"
    UKRAINIAN = "uk", "Ukrainian"


class PartOfSpeech(models.TextChoices):
    NOUN = "noun", "Noun"
    VERB = "verb", "Verb"
    ADJECTIVE = "adjective", "Adjective"
    ADVERB = "adverb", "Adverb"
    PRONOUN = "pronoun", "Pronoun"
    PREPOSITION = "preposition", "Preposition"
    CONJUNCTION = "conjunction", "Conjunction"
    INTERJECTION = "interjection", "Interjection"
    PHRASE = "phrase", "Phrase"
    OTHER = "other", "Other"


class Word(models.Model):
    english_word = models.CharField(max_length=128)
    source_language = models.CharField(
        max_length=2,
        choices=LanguageCode.choices,
        default=LanguageCode.ENGLISH,
    )
    target_language = models.CharField(
        max_length=2,
        choices=LanguageCode.choices,
        default=LanguageCode.UKRAINIAN,
    )
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    transcription = models.CharField(max_length=128)
    ukrainian_translation = models.CharField(max_length=256)
    context_sentence = models.TextField()
    origin = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["english_word"]
        constraints = [
            models.UniqueConstraint(
                fields=["english_word", "source_language", "target_language"],
                name="unique_word_with_direction",
            )
        ]

    def __str__(self) -> str:
        return self.english_word

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.english_word, allow_unicode=True) or "word"

        base_slug = self.slug
        suffix = 1
        while Word.objects.exclude(pk=self.pk).filter(slug=self.slug).exists():
            self.slug = f"{base_slug}-{suffix}"
            suffix += 1

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("dictionary:word_detail", kwargs={"slug": self.slug})


class TranslationOption(models.Model):
    word = models.ForeignKey(
        Word,
        on_delete=models.CASCADE,
        related_name="translation_options",
    )
    text = models.CharField(max_length=256)
    part_of_speech = models.CharField(
        max_length=20,
        choices=PartOfSpeech.choices,
        default=PartOfSpeech.OTHER,
    )
    priority = models.PositiveSmallIntegerField(default=1)
    usage_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["priority", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["word", "text", "part_of_speech"],
                name="unique_translation_option_per_word",
            )
        ]

    def __str__(self) -> str:
        return f"{self.word.english_word} -> {self.text} ({self.part_of_speech})"
