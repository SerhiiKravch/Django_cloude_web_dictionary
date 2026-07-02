from django import forms

from .models import LanguageCode


LANGUAGE_DIRECTION_CHOICES = (
    (f"{LanguageCode.ENGLISH}:{LanguageCode.UKRAINIAN}", "English -> Ukrainian"),
    (f"{LanguageCode.UKRAINIAN}:{LanguageCode.ENGLISH}", "Ukrainian -> English"),
)


class WordLookupForm(forms.Form):
    direction = forms.ChoiceField(
        label="Translation direction",
        choices=LANGUAGE_DIRECTION_CHOICES,
        initial=f"{LanguageCode.ENGLISH}:{LanguageCode.UKRAINIAN}",
    )
    word = forms.CharField(
        label="Unknown word",
        max_length=128,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter a word",
                "autocomplete": "off",
            }
        ),
    )

    def clean_word(self):
        value = self.cleaned_data["word"].strip()
        return value
