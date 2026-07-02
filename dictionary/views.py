import re

from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import WordLookupForm
from .models import LanguageCode, TranslationOption, Word
from .utils import (
    TemporaryWordGenerationError,
    WordGenerationError,
    generate_word_data,
)


def normalize_word_input(value: str, source_language: str) -> str:
    cleaned = value.strip().lower().replace("’", "'").replace("`", "'")
    if source_language == LanguageCode.UKRAINIAN:
        cleaned = re.sub(r"[^а-щьюяєіїґ'-]", "", cleaned, flags=re.IGNORECASE)
    else:
        cleaned = re.sub(r"[^a-z'-]", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip("-'")
    return cleaned


def parse_direction(value: str) -> tuple[str, str]:
    try:
        source_language, target_language = value.split(":", 1)
    except ValueError:
        return LanguageCode.ENGLISH, LanguageCode.UKRAINIAN

    allowed = {LanguageCode.ENGLISH, LanguageCode.UKRAINIAN}
    if source_language not in allowed or target_language not in allowed:
        return LanguageCode.ENGLISH, LanguageCode.UKRAINIAN
    if source_language == target_language:
        return LanguageCode.ENGLISH, LanguageCode.UKRAINIAN
    return source_language, target_language


def word_list(request):
    words = Word.objects.all().prefetch_related("translation_options")
    form = WordLookupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        source_language, target_language = parse_direction(form.cleaned_data["direction"])
        value = normalize_word_input(
            form.cleaned_data["word"],
            source_language=source_language,
        )
        if not value:
            messages.error(request, "Enter a valid word for the selected source language.")
            return render(request, "dictionary/word_list.html", {"words": words, "form": form})

        existing = Word.objects.filter(
            english_word__iexact=value,
            source_language=source_language,
            target_language=target_language,
        ).first()
        if existing:
            return redirect(existing.get_absolute_url())

        cache_key = f"generated_word:{source_language}:{target_language}:{value}"
        generated = cache.get(cache_key)
        try:
            if generated is None:
                generated = generate_word_data(
                    value,
                    source_language=source_language,
                    target_language=target_language,
                )
                if generated is not None:
                    cache.set(cache_key, generated, timeout=60 * 60 * 24)
        except ImproperlyConfigured as exc:
            messages.error(request, str(exc))
        except TemporaryWordGenerationError as exc:
            messages.error(request, str(exc))
        except WordGenerationError:
            messages.error(request, "Could not generate data for this word. Try again.")
        except Exception:
            messages.error(request, "Unexpected OpenAI error. Please try again later.")
        else:
            if generated is None:
                messages.error(
                    request,
                    "This value is not recognized as a valid word for the selected source language.",
                )
            else:
                try:
                    with transaction.atomic():
                        created = Word.objects.create(
                            english_word=value,
                            source_language=source_language,
                            target_language=target_language,
                            transcription=generated.transcription,
                            ukrainian_translation=generated.options[0].text,
                            context_sentence=generated.context_sentence,
                            origin=generated.origin,
                        )
                        TranslationOption.objects.bulk_create(
                            [
                                TranslationOption(
                                    word=created,
                                    text=option.text,
                                    part_of_speech=option.part_of_speech,
                                    priority=index,
                                    usage_note=option.usage_note,
                                )
                                for index, option in enumerate(generated.options, start=1)
                            ]
                        )
                except IntegrityError:
                    existing = Word.objects.filter(
                        english_word__iexact=value,
                        source_language=source_language,
                        target_language=target_language,
                    ).first()
                    if existing:
                        return redirect(existing.get_absolute_url())
                    messages.error(request, "Failed to save word. Please retry.")
                else:
                    return redirect(created.get_absolute_url())

    return render(request, "dictionary/word_list.html", {"words": words, "form": form})


def word_detail(request, slug):
    word = get_object_or_404(
        Word.objects.prefetch_related("translation_options"),
        slug=slug,
    )
    return render(request, "dictionary/word_detail.html", {"word": word})


def autocomplete_words(request):
    source_language = request.GET.get("source_language", LanguageCode.ENGLISH)
    if source_language not in {LanguageCode.ENGLISH, LanguageCode.UKRAINIAN}:
        source_language = LanguageCode.ENGLISH
    query = normalize_word_input(request.GET.get("q", ""), source_language=source_language)
    if len(query) < 2:
        return JsonResponse({"results": []})

    matches = (
        Word.objects.filter(
            english_word__istartswith=query,
            source_language=source_language,
        )
        .values_list("english_word", flat=True)[:8]
    )
    return JsonResponse({"results": list(matches)})
