from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .models import TranslationOption, Word
from .utils import GeneratedTranslationOption, GeneratedWord


class DictionaryViewsTests(TestCase):
    def setUp(self):
        self.list_url = reverse("dictionary:word_list")

    def test_existing_word_redirects_to_detail(self):
        word = Word.objects.create(
            english_word="apple",
            transcription="[ˈæp.əl]",
            ukrainian_translation="яблуко",
            context_sentence="I ate a red apple for breakfast.",
            origin="From Old English aeppel.",
        )

        response = self.client.post(
            self.list_url,
            {"word": "APPLE", "direction": "en:uk"},
        )

        self.assertRedirects(response, word.get_absolute_url())

    @patch("dictionary.views.generate_word_data")
    def test_unknown_valid_word_is_generated_saved_and_redirected(self, mocked_generate):
        mocked_generate.return_value = GeneratedWord(
            transcription="[ˈriː.dɚ]",
            context_sentence="Every reader finds a favorite book.",
            origin="Derived from read + -er.",
            options=[
                GeneratedTranslationOption(
                    text="читач",
                    part_of_speech="noun",
                    confidence=0.96,
                    usage_note="",
                ),
                GeneratedTranslationOption(
                    text="той, хто читає",
                    part_of_speech="phrase",
                    confidence=0.73,
                    usage_note="",
                ),
            ],
        )

        response = self.client.post(
            self.list_url,
            {"word": "Reader", "direction": "en:uk"},
        )

        created = Word.objects.get(english_word="reader")
        self.assertRedirects(response, created.get_absolute_url())
        mocked_generate.assert_called_once_with(
            "reader",
            source_language="en",
            target_language="uk",
        )
        self.assertEqual(created.ukrainian_translation, "читач")
        self.assertEqual(created.translation_options.count(), 2)

    @patch("dictionary.views.generate_word_data")
    def test_ukrainian_to_english_generation_creates_directional_record(self, mocked_generate):
        mocked_generate.return_value = GeneratedWord(
            transcription="[dɪm]",
            context_sentence="Дім стоїть на пагорбі.",
            origin="Common Slavic root.",
            options=[
                GeneratedTranslationOption(
                    text="house",
                    part_of_speech="noun",
                    confidence=0.94,
                    usage_note="most common",
                ),
                GeneratedTranslationOption(
                    text="home",
                    part_of_speech="noun",
                    confidence=0.88,
                    usage_note="emotional context",
                ),
            ],
        )

        response = self.client.post(
            self.list_url,
            {"word": "Дім", "direction": "uk:en"},
        )

        created = Word.objects.get(english_word="дім", source_language="uk", target_language="en")
        self.assertRedirects(response, created.get_absolute_url())
        self.assertEqual(created.ukrainian_translation, "house")
        options = list(created.translation_options.values_list("text", "part_of_speech", "priority"))
        self.assertEqual(
            options,
            [
                ("house", "noun", 1),
                ("home", "noun", 2),
            ],
        )

    @patch("dictionary.views.generate_word_data")
    def test_invalid_word_shows_notification(self, mocked_generate):
        mocked_generate.return_value = None

        response = self.client.post(
            self.list_url,
            {"word": "asdfghjkl", "direction": "en:uk"},
            follow=True,
        )

        self.assertContains(
            response,
            "This value is not recognized as a valid word for the selected source language.",
        )
        self.assertFalse(Word.objects.filter(english_word="asdfghjkl").exists())

    def test_word_detail_uses_slug_seo_url(self):
        word = Word.objects.create(
            english_word="waterfall",
            transcription="[ˈwɔː.tɚ.fɔːl]",
            ukrainian_translation="водоспад",
            context_sentence="We visited a waterfall in the mountains.",
            origin="Compound of water + fall.",
        )
        TranslationOption.objects.create(
            word=word,
            text="водоспад",
            part_of_speech="noun",
            priority=1,
        )

        response = self.client.get(word.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "waterfall")
        self.assertContains(response, "NOUN")
        self.assertTrue(word.get_absolute_url().endswith("/word/waterfall/"))

    def test_autocomplete_returns_matching_words_for_source_language(self):
        Word.objects.create(
            english_word="apple",
            source_language="en",
            target_language="uk",
            transcription="[ˈæp.əl]",
            ukrainian_translation="яблуко",
            context_sentence="An apple a day keeps the doctor away.",
            origin="Old English aeppel.",
        )
        Word.objects.create(
            english_word="application",
            source_language="en",
            target_language="uk",
            transcription="[ˌæp.lɪˈkeɪ.ʃən]",
            ukrainian_translation="застосунок",
            context_sentence="This application is useful.",
            origin="From Latin applicatio.",
        )
        Word.objects.create(
            english_word="апельсин",
            source_language="uk",
            target_language="en",
            transcription="[apelsɪn]",
            ukrainian_translation="orange",
            context_sentence="Апельсин дуже соковитий.",
            origin="From Dutch appelsien.",
        )

        url = reverse("dictionary:autocomplete_words")
        response = self.client.get(url, {"q": "app", "source_language": "en"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": ["apple", "application"]})
