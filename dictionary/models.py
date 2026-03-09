from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Word(models.Model):
    english_word = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    transcription = models.CharField(max_length=128)
    ukrainian_translation = models.CharField(max_length=256)
    context_sentence = models.TextField()
    origin = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["english_word"]

    def __str__(self) -> str:
        return self.english_word

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.english_word)

        base_slug = self.slug
        suffix = 1
        while Word.objects.exclude(pk=self.pk).filter(slug=self.slug).exists():
            self.slug = f"{base_slug}-{suffix}"
            suffix += 1

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("dictionary:word_detail", kwargs={"slug": self.slug})
