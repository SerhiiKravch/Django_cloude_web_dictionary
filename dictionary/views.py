from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import WordLookupForm
from .models import Word
from .utils import WordGenerationError, generate_word_data


def word_list(request):
    words = Word.objects.all()
    form = WordLookupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        value = form.cleaned_data["word"]
        existing = Word.objects.filter(english_word__iexact=value).first()
        if existing:
            return redirect(existing.get_absolute_url())

        try:
            generated = generate_word_data(value)
        except ImproperlyConfigured as exc:
            messages.error(request, str(exc))
        except WordGenerationError:
            messages.error(request, "Could not generate data for this word. Try again.")
        except Exception:
            messages.error(request, "Unexpected OpenAI error. Please try again later.")
        else:
            if generated is None:
                messages.error(
                    request,
                    "This value is not recognized as a valid English word. Check spelling.",
                )
            else:
                try:
                    created = Word.objects.create(
                        english_word=value.lower(),
                        transcription=generated.transcription,
                        ukrainian_translation=generated.ukrainian_translation,
                        context_sentence=generated.context_sentence,
                        origin=generated.origin,
                    )
                except IntegrityError:
                    existing = Word.objects.filter(english_word__iexact=value).first()
                    if existing:
                        return redirect(existing.get_absolute_url())
                    messages.error(request, "Failed to save word. Please retry.")
                else:
                    return redirect(created.get_absolute_url())

    return render(request, "dictionary/word_list.html", {"words": words, "form": form})


def word_detail(request, slug):
    word = get_object_or_404(Word, slug=slug)
    return render(request, "dictionary/word_detail.html", {"word": word})
