import json
import os
from dataclasses import dataclass
from typing import Optional

from django.core.exceptions import ImproperlyConfigured


try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


@dataclass
class GeneratedWord:
    transcription: str
    ukrainian_translation: str
    context_sentence: str
    origin: str


class WordGenerationError(Exception):
    pass


def generate_word_data(word: str) -> Optional[GeneratedWord]:
    if OpenAI is None:
        raise ImproperlyConfigured(
            "The openai package is not installed. Install dependencies first."
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ImproperlyConfigured("OPENAI_API_KEY is not configured.")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=api_key)

    prompt = (
        "You are an English dictionary assistant. "
        "Analyze the input and return strict JSON with fields: "
        "is_valid_english_word (boolean), transcription (string), "
        "ukrainian_translation (string), context_sentence (string), origin (string). "
        "If input is not a real English word, return is_valid_english_word=false "
        "and empty strings for the other fields."
    )

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Word: {word}",
            },
        ],
        text={"format": {"type": "json_object"}},
    )

    raw = response.output_text
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover
        raise WordGenerationError("Model returned invalid JSON.") from exc

    if not parsed.get("is_valid_english_word"):
        return None

    required_fields = [
        "transcription",
        "ukrainian_translation",
        "context_sentence",
        "origin",
    ]
    if any(not parsed.get(field) for field in required_fields):
        raise WordGenerationError("Model did not return all required fields.")

    return GeneratedWord(
        transcription=parsed["transcription"].strip(),
        ukrainian_translation=parsed["ukrainian_translation"].strip(),
        context_sentence=parsed["context_sentence"].strip(),
        origin=parsed["origin"].strip(),
    )
