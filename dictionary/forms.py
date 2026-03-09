from django import forms


class WordLookupForm(forms.Form):
    word = forms.CharField(
        label="Unknown word",
        max_length=128,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter an English word",
                "autocomplete": "off",
            }
        ),
    )

    def clean_word(self):
        value = self.cleaned_data["word"].strip()
        return value
