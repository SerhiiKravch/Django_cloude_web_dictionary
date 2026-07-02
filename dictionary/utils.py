import json
import os
import time
from dataclasses import dataclass
from typing import Optional

from django.core.exceptions import ImproperlyConfigured

from .models import PartOfSpeech


try:
    from openai import (
        APIConnectionError,
        APIStatusError,
        APITimeoutError,
        OpenAI,
        RateLimitError,
    )
except ImportError:  # pragma: no cover
    OpenAI = None
    APITimeoutError = None
    APIConnectionError = None
    APIStatusError = None
    RateLimitError = None


@dataclass 
class GeneratedTranslationOption:
    text: str
    part_of_speech: str
    confidence: float
    usage_note: str


@dataclass
class GeneratedWord:
    transcription: str
    context_sentence: str
    origin: str
    options: list[GeneratedTranslationOption]


class WordGenerationError(Exception):
    pass


class TemporaryWordGenerationError(WordGenerationError):
    pass


def _is_valid_context_sentence(sentence: str, word: str) -> bool:
    sentence = sentence.strip()
    word = word.strip().lower()
    if not sentence or len(sentence.split()) < 3:
        return False
    return word in sentence.lower()


def _normalize_model_text(value: str) -> str:
    return " ".join(value.strip().split())


def _normalize_part_of_speech(value: str) -> str:
    normalized = _normalize_model_text(value).lower()
    valid_values = {choice[0] for choice in PartOfSpeech.choices}
    if normalized in valid_values:
        return normalized
    return PartOfSpeech.OTHER


def _normalize_confidence(value) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, confidence))


def _deduplicate_options(
    options: list[GeneratedTranslationOption],
) -> list[GeneratedTranslationOption]:
    seen = set()
    unique = []
    for option in options:
        key = (option.text.lower(), option.part_of_speech)
        if key in seen:
            continue
        seen.add(key)
        unique.append(option)
    return unique


def _validate_generated_payload(parsed: dict, requested_word: str) -> Optional[GeneratedWord]:
    if not parsed.get("is_valid_word"):
        return None

    required_fields = [
        "transcription",
        "context_sentence",
        "origin",
        "options",
    ]
    if any(not parsed.get(field) for field in required_fields):
        raise WordGenerationError("Model did not return all required fields.")

    transcription = _normalize_model_text(parsed["transcription"])
    context_sentence = _normalize_model_text(parsed["context_sentence"])
    origin = _normalize_model_text(parsed["origin"])
    raw_options = parsed["options"]

    if not isinstance(raw_options, list):
        raise WordGenerationError("Model returned invalid options format.")

    if not _is_valid_context_sentence(context_sentence, requested_word):
        raise WordGenerationError(
            "Model returned an invalid context sentence. Please try again."
        )

    parsed_options = []
    for item in raw_options:
        if not isinstance(item, dict):
            continue
        text = _normalize_model_text(item.get("text", ""))
        if not text:
            continue
        parsed_options.append(
            GeneratedTranslationOption(
                text=text,
                part_of_speech=_normalize_part_of_speech(item.get("part_of_speech", "")),
                confidence=_normalize_confidence(item.get("confidence")),
                usage_note=_normalize_model_text(item.get("usage_note", "")),
            )
        )

    parsed_options = _deduplicate_options(parsed_options)
    parsed_options.sort(key=lambda option: option.confidence, reverse=True)
    if not parsed_options:
        raise WordGenerationError("Model did not return any translation options.")

    return GeneratedWord(
        transcription=transcription,
        context_sentence=context_sentence,
        origin=origin,
        options=parsed_options,
    )


def generate_word_data(
    word: str,
    source_language: str = "en",
    target_language: str = "uk",
) -> Optional[GeneratedWord]:
    if OpenAI is None:
        raise ImproperlyConfigured(
            "The openai package is not installed. Install dependencies first."
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ImproperlyConfigured("OPENAI_API_KEY is not configured.")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    request_timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
    max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
    client = OpenAI(api_key=api_key)

    language_name = {"en": "English", "uk": "Ukrainian"}
    source_name = language_name.get(source_language, "English")
    target_name = language_name.get(target_language, "Ukrainian")
    pos_values = ", ".join(choice[0] for choice in PartOfSpeech.choices)
    prompt = (
        "You are a bilingual dictionary assistant. "
        f"Source language is {source_name}. Target language is {target_name}. "
        "Return strict JSON with fields: is_valid_word (boolean), transcription (string), "
        "context_sentence (string), origin (string), "
        "options (array of objects with text, part_of_speech, confidence, usage_note). "
        "Use part_of_speech only from this list: "
        f"{pos_values}. "
        "If the input is not a valid word in the source language, return is_valid_word=false "
        "and empty strings/empty options."
    )

    for attempt in range(max_retries + 1):
        try:
            response = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Word: {word}\n"
                            f"Source language code: {source_language}\n"
                            f"Target language code: {target_language}"
                        ),
                    },
                ],
                text={"format": {"type": "json_object"}},
                timeout=request_timeout,
            )
            raw = response.output_text
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:  # pragma: no cover
                raise WordGenerationError("Model returned invalid JSON.") from exc

            return _validate_generated_payload(parsed, requested_word=word)
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            if attempt < max_retries:
                time.sleep(2**attempt)
                continue
            raise TemporaryWordGenerationError(
                "OpenAI is temporarily unavailable. Please retry in a moment."
            ) from exc
        except APIStatusError as exc:
            if exc.status_code and exc.status_code >= 500 and attempt < max_retries:
                time.sleep(2**attempt)
                continue
            raise TemporaryWordGenerationError(
                "OpenAI service returned an error. Please retry later."
            ) from exc
